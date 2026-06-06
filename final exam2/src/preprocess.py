"""
preprocess.py
=============
文本清洗、语义分块与 LLM 元数据提取模块。

功能：
  - clean_text   : 移除 HTML 标签、修复常见编码乱码
  - chunk_text   : 语义分块（先按段落边界切分，再合并到目标大小）
  - extract_metadata : 调用 LLM 从文档文本中提取作者/日期/分类
  - process_documents: 整合以上步骤
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from openai import OpenAI, RateLimitError

from src.utils import get_logger, get_model_name, get_openai_client

logger = get_logger("preprocess")

DEFAULT_MAX_WORKERS = 32
SUPPORTED_METADATA_STRATEGIES = {"merge", "llm_only", "jsonl_only"}


# ── 清洗 ──────────────────────────────────────────────────────────

_HTML_ENTITIES = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&apos;": "'", "&nbsp;": " ",
    "&#160;": " ", "&#39;": "'",
}


def clean_text(text: str) -> str:
    """
    清洗文本：
      1. 移除 HTML 标签
      2. 解码常见 HTML 实体
      3. 去除控制字符（保留换行与制表符）
      4. 合并多余空白行与行内空格
    """
    text = re.sub(r"<[^>]+>", " ", text)

    for entity, char in _HTML_ENTITIES.items():
        text = text.replace(entity, char)

    text = re.sub(r"\r", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[^\S\n\t ]+", " ", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ── 语义分块 ──────────────────────────────────────────────────────

def _split_into_sentences(text: str) -> list[str]:
    """将文本按句子边界切分（支持中英文标点，避免切碎缩写与版本号）。"""
    # 在中文字符、问号、感叹号、换行，或后跟空格+大写字母/数字的句点处切分
    parts = re.split(r"(?<=[。！？\n])\s*|(?<=[!?])\s*|(?<=\.)\s+(?=[A-Z\d])", text)
    return [s.strip() for s in parts if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 700,
    overlap: int = 120,
    min_chunk_chars: int = 40,
) -> list[dict]:
    """
    语义分块策略：
      1. 首先按双换行（段落边界）切分为自然段落
      2. 对每个段落，按句子边界细分
      3. 将句子合并到接近 chunk_size 的块（贪心合并）
      4. 若单句超长，按字符滑窗再切分
      overlap 保证上下文连续性。
    """
    if not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0。")
    if overlap < 0:
        raise ValueError("overlap 必须大于等于 0。")
    if chunk_size <= overlap:
        raise ValueError("chunk_size 必须大于 overlap。")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # 将段落拆为句子
    all_sentences: list[str] = []
    for para in paragraphs:
        sentences = _split_into_sentences(para)
        if sentences:
            all_sentences.extend(sentences)
        else:
            all_sentences.append(para)

    # 贪心合并句子到 chunk_size
    merged: list[str] = []
    current = ""
    for sent in all_sentences:
        candidate = (current + " " + sent).strip() if current else sent
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                merged.append(current)
            # 单句超长时直接加入（后续滑窗处理）
            current = sent
    if current:
        merged.append(current)

    # 对超长块做字符滑窗细分
    chunks: list[dict] = []
    char_offset = 0
    for block in merged:
        if len(block) <= chunk_size:
            if len(block) >= min_chunk_chars:
                chunks.append({
                    "text": block,
                    "char_start": char_offset,
                    "char_end": char_offset + len(block),
                })
            char_offset += len(block) + 1
        else:
            start = 0
            while start < len(block):
                end = start + chunk_size
                piece = block[start:end].strip()
                if len(piece) >= min_chunk_chars:
                    chunks.append({
                        "text": piece,
                        "char_start": char_offset + start,
                        "char_end": char_offset + min(end, len(block)),
                    })
                start += chunk_size - overlap
            char_offset += len(block) + 1

    if not chunks and text.strip():
        chunks.append({
            "text": text.strip(),
            "char_start": 0,
            "char_end": len(text.strip()),
        })

    return chunks


# ── LLM 元数据提取 ───────────────────────────────────────────────

def _safe_json_parse(raw: str, default: Any = None) -> Any:
    """安全解析 JSON，对常见 LLM 输出格式错误做自动修复。"""
    if not raw or not raw.strip():
        return default if default is not None else {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 尝试修复：截断到最后一个完整对象
        fixed = raw.strip()
        # 移除首尾非 JSON 内容（如解释性文字）
        brace_start = fixed.find("{")
        brace_end = fixed.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            fixed = fixed[brace_start : brace_end + 1]
        # 移除注释行
        fixed = re.sub(r"^\s*//.*$", "", fixed, flags=re.MULTILINE)
        # 移除尾随逗号
        fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        # 最后尝试：用正则逐字段提取
        fallback: dict = {}
        for key in ("author", "year", "category", "language", "summary"):
            pattern = rf'"{key}"\s*:\s*("(?:[^"\\]|\\.)*"|\d+|null|true|false)'
            match = re.search(pattern, fixed)
            if match:
                val = match.group(1)
                if val == "null":
                    fallback[key] = None
                elif val == "true":
                    fallback[key] = True
                elif val == "false":
                    fallback[key] = False
                elif val.startswith('"'):
                    fallback[key] = val[1:-1]
                else:
                    fallback[key] = int(float(val))
        return fallback if fallback else (default if default is not None else {})


_METADATA_SUPPORTED_KEYS = ("author", "year", "category", "language", "summary")

_METADATA_SYSTEM = (
    "你是一个文档分析助手。请从给定的文档文本中提取结构化元数据，"
    "以纯 JSON 格式返回，不要有任何额外文字或代码块标记。\n"
    "JSON 字段说明（如信息缺失则填 null）：\n"
    '  "author"   : 作者姓名（字符串或 null）\n'
    '  "year"     : 发布/创作年份（整数或 null）\n'
    '  "category" : 文档分类，如 notice/faq/notes/report/wiki 等（字符串）\n'
    '  "language" : 主要语言，zh 或 en（字符串）\n'
    '  "summary"  : 一句话摘要，不超过 50 字（字符串）'
)


_METADATA_MAX_RETRIES = 3
_METADATA_RETRY_BASE_DELAY = 2


def extract_metadata(
    text: str,
    filename: str = "",
    client: OpenAI | None = None,
) -> dict:
    """
    使用 LLM 提取文档元数据。
    遇到 429 限流时自动指数退避重试，其他失败返回默认值（保证流水线不中断）。
    """
    default_category = _guess_category(filename)

    if client is None:
        client = get_openai_client()
    model = get_model_name()
    snippet = text[:1200]
    user_msg = f"文件名：{filename}\n\n文档内容（节选）：\n{snippet}"

    for attempt in range(1, _METADATA_MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _METADATA_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0,
                max_tokens=256,
            )
            raw = resp.choices[0].message.content or "{}"
            raw = re.sub(r"```[a-z]*", "", raw).strip().strip("`").strip()
            meta = _safe_json_parse(raw, default={})

            meta.setdefault("author", None)
            meta.setdefault("year", None)
            meta.setdefault("category", default_category)
            meta.setdefault("language", "zh")
            meta.setdefault("summary", "")

            if meta["year"] is not None:
                try:
                    meta["year"] = int(float(meta["year"]))
                except (ValueError, TypeError):
                    meta["year"] = None

            return meta

        except RateLimitError:
            if attempt < _METADATA_MAX_RETRIES:
                delay = _METADATA_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "429 限流 [%s] 第%d次，%ds 后重试…", filename, attempt, delay,
                )
                time.sleep(delay)
            else:
                logger.warning("429 限流 [%s] 重试耗尽，使用默认值。", filename)

        except Exception as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            logger.warning("元数据提取失败 [%s]: %s", filename, exc)
            break

    return {
        "author": None,
        "year": None,
        "category": default_category,
        "language": "zh",
        "summary": "",
    }


def _guess_category(filename: str) -> str:
    """根据文件名前缀推断分类（兜底）。"""
    name = filename.lower()
    if name.startswith("wiki_"):       return "wiki"
    if name.startswith("notice"):      return "notice"
    if name.startswith("faq"):         return "faq"
    if name.startswith("case_study"):  return "case_study"
    if name.startswith("report"):      return "report"
    if name.startswith("term_"):       return "term"
    return "general"


def _extract_metadata_batch(
    tasks: list[tuple[str, str]],
    client: OpenAI,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict]:
    """
    并发批量提取元数据。

    参数：
      tasks       : [(text, filename), ...] 待提取的文档列表
      client      : 共享的 OpenAI 客户端（线程安全）
      max_workers : 并发线程数

    返回：
      与 tasks 等长的元数据字典列表，顺序与输入对应。
    """
    results: dict[int, dict] = {}
    total = len(tasks)

    def _do_one(idx: int, text: str, filename: str) -> tuple[int, dict]:
        meta = extract_metadata(text, filename=filename, client=client)
        return idx, meta

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_do_one, idx, text, fname): idx
            for idx, (text, fname) in enumerate(tasks)
        }
        done_count = 0
        for future in as_completed(futures):
            idx, meta = future.result()
            results[idx] = meta
            done_count += 1
            if done_count % 10 == 0 or done_count == total:
                logger.info("元数据提取进度: %d/%d", done_count, total)

    return [results[i] for i in range(total)]


def _merge_fm_meta(fm_meta: dict, llm_meta: dict) -> dict:
    """将 Front-Matter 元数据与 LLM 提取的元数据合并，Front-Matter 优先。"""
    merged = dict(llm_meta)
    if fm_meta.get("author"):
        merged["author"] = fm_meta["author"]
    if fm_meta.get("year"):
        try:
            merged["year"] = int(float(fm_meta["year"]))
        except (ValueError, TypeError):
            logger.warning("Front-Matter year 字段转换失败: %s", fm_meta["year"])
    if fm_meta.get("category"):
        merged["category"] = fm_meta["category"]
    if fm_meta.get("language"):
        merged["language"] = fm_meta["language"]
    return merged


def _merge_jsonl_meta(jsonl_meta: dict, llm_meta: dict) -> dict:
    """
    将 JSONL 元数据与 LLM 提取的元数据合并，JSONL 优先。

    JSONL 字段映射：
      - author → author
      - category → category
      - year (从 created_at 解析) → year
      - doc_type → 用于推断 category（若 category 为空）
    """
    merged = dict(llm_meta)

    # 作者：JSONL 优先
    if jsonl_meta.get("author"):
        merged["author"] = jsonl_meta["author"]

    # 年份：从 created_at 解析
    if jsonl_meta.get("year"):
        merged["year"] = jsonl_meta["year"]

    # 分类：JSONL 优先，若为空则用 doc_type 推断
    if jsonl_meta.get("category"):
        merged["category"] = jsonl_meta["category"]
    elif jsonl_meta.get("doc_type"):
        # 根据 doc_type 推断 category
        doc_type = jsonl_meta["doc_type"].lower()
        type_mapping = {
            "ticket": "ticket",
            "error_log": "error_log",
            "slack": "slack",
            "manual": "manual",
        }
        merged["category"] = type_mapping.get(doc_type, "general")

    # 语言：根据内容推断（中文字符占比）
    # 这里简单处理，后续可在 preprocess 中进一步优化
    if not merged.get("language"):
        merged["language"] = "zh"

    return merged


# ── 主处理流程 ───────────────────────────────────────────────────

def process_documents(
    documents: list[dict],
    chunk_size: int = 700,
    overlap: int = 120,
    is_extract_meta: bool = True,
    max_workers: int = DEFAULT_MAX_WORKERS,
    metadata_strategy: str = "merge",
) -> list[dict]:
    """
    完整的文档处理流程：
      清洗 → (可选) 并发LLM元数据提取 → 语义分块 → 组装

    参数：
      max_workers : LLM 元数据提取的并发线程数（仅在 is_extract_meta=True 时生效）
      metadata_strategy : 元数据合并策略
        - "merge": 优先使用 JSONL/Front-Matter 元数据，缺失时用 LLM 补充
        - "llm_only": 忽略 JSONL/Front-Matter 元数据，使用 LLM 提取
        - "jsonl_only": 仅使用 JSONL/Front-Matter 元数据，跳过 LLM 提取
    """
    processed: list[dict] = []
    if metadata_strategy not in SUPPORTED_METADATA_STRATEGIES:
        raise ValueError(
            "metadata_strategy 必须是 merge、llm_only 或 jsonl_only。"
        )

    # ── 阶段 1：清洗所有文档 ──
    cleaned_docs: list[tuple[dict, str]] = []
    for doc in documents:
        cleaned = clean_text(doc["text"])
        cleaned_docs.append((doc, cleaned))
    logger.info("文档清洗完成，共 %d 篇。", len(cleaned_docs))

    # ── 阶段 2：并发提取元数据（或使用默认值） ──
    if metadata_strategy == "jsonl_only":
        # 仅使用 JSONL/Front-Matter 元数据，跳过 LLM 提取
        llm_metas = [
            {
                "author": None, "year": None,
                "category": _guess_category(doc.get("source", "unknown")),
                "language": "zh", "summary": "",
            }
            for doc, _ in cleaned_docs
        ]
        logger.info("使用 jsonl_only 策略，跳过 LLM 元数据提取。")
    elif is_extract_meta and metadata_strategy != "jsonl_only":
        client = get_openai_client()
        tasks = [
            (cleaned, doc.get("source", "unknown"))
            for doc, cleaned in cleaned_docs
        ]
        logger.info("开始并发提取元数据（并发数: %d）…", max_workers)
        llm_metas = _extract_metadata_batch(tasks, client, max_workers=max_workers)
    else:
        llm_metas = [
            {
                "author": None, "year": None,
                "category": _guess_category(doc.get("source", "unknown")),
                "language": "zh", "summary": "",
            }
            for doc, _ in cleaned_docs
        ]

    # ── 阶段 3：分块组装 ──
    for doc_idx, ((doc, cleaned), llm_meta) in enumerate(zip(cleaned_docs, llm_metas)):
        filename = doc.get("source", "unknown")

        # 合并元数据（根据策略）
        fm_meta = doc.get("fm_meta", {})
        if metadata_strategy == "merge" and fm_meta:
            # 判断是 JSONL 还是 Front-Matter
            if fm_meta.get("doc_type") or fm_meta.get("created_at"):
                # JSONL 元数据
                llm_meta = _merge_jsonl_meta(fm_meta, llm_meta)
            else:
                # Front-Matter 元数据
                llm_meta = _merge_fm_meta(fm_meta, llm_meta)
        elif metadata_strategy == "jsonl_only" and fm_meta:
            # 仅使用 JSONL/Front-Matter 元数据
            if fm_meta.get("doc_type") or fm_meta.get("created_at"):
                llm_meta = {
                    "author": fm_meta.get("author"),
                    "year": fm_meta.get("year"),
                    "category": fm_meta.get("category", "general"),
                    "language": fm_meta.get("language", "zh"),
                    "summary": fm_meta.get("summary", ""),
                }
            else:
                llm_meta = {
                    "author": fm_meta.get("author"),
                    "year": fm_meta.get("year") if fm_meta.get("year") else None,
                    "category": fm_meta.get("category", "general"),
                    "language": fm_meta.get("language", "zh"),
                    "summary": "",
                }

        chunks = chunk_text(cleaned, chunk_size=chunk_size, overlap=overlap)

        for idx, chunk in enumerate(chunks):
            processed.append({
                "id": f"{filename}_{doc_idx}_{idx}",
                "text": chunk["text"],
                "metadata": {
                    "source":     filename,
                    "path":       doc.get("path", ""),
                    "chunk_id":   idx,
                    "char_start": chunk["char_start"],
                    "char_end":   chunk["char_end"],
                    "author":     llm_meta.get("author") if llm_meta.get("author") != "" else None,
                    "year":       llm_meta.get("year") if llm_meta.get("year") != 0 else None,
                    "category":   llm_meta.get("category", "general"),
                    "language":   llm_meta.get("language", "zh"),
                    "summary":    llm_meta.get("summary", ""),
                },
            })

    return processed
