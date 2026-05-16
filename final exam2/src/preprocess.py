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
from typing import Any

from openai import OpenAI

from src.utils import get_logger, get_model_name, get_openai_client

logger = get_logger("preprocess")


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
    """将文本按句子边界切分（支持中英文标点）。"""
    # 在中英文句末标点后切分，保留标点
    parts = re.split(r"(?<=[。！？.!?\n])\s*", text)
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
                    fallback[key] = int(val)
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


def extract_metadata(
    text: str,
    filename: str = "",
    client: OpenAI | None = None,
) -> dict:
    """
    使用 LLM 提取文档元数据。
    失败时返回默认值（保证流水线不中断）。
    """
    default_category = _guess_category(filename)

    try:
        if client is None:
            client = get_openai_client()
        model = get_model_name()
        snippet = text[:1200]
        user_msg = f"文件名：{filename}\n\n文档内容（节选）：\n{snippet}"

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
                meta["year"] = int(meta["year"])
            except (ValueError, TypeError):
                meta["year"] = None

        return meta

    except Exception as exc:
        # 不吞掉 KeyboardInterrupt / SystemExit 等系统信号
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.warning("元数据提取失败 [%s]: %s", filename, exc)
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


def _merge_fm_meta(fm_meta: dict, llm_meta: dict) -> dict:
    """将 Front-Matter 元数据与 LLM 提取的元数据合并，Front-Matter 优先。"""
    merged = dict(llm_meta)
    if fm_meta.get("author"):
        merged["author"] = fm_meta["author"]
    if fm_meta.get("year"):
        try:
            merged["year"] = int(fm_meta["year"])
        except (ValueError, TypeError):
            logger.warning("Front-Matter year 字段转换失败: %s", fm_meta["year"])
            pass
    if fm_meta.get("category"):
        merged["category"] = fm_meta["category"]
    if fm_meta.get("language"):
        merged["language"] = fm_meta["language"]
    return merged


# ── 主处理流程 ───────────────────────────────────────────────────

def process_documents(
    documents: list[dict],
    chunk_size: int = 700,
    overlap: int = 120,
    is_extract_meta: bool = True,
) -> list[dict]:
    """
    完整的文档处理流程：
      清洗 → (可选) LLM元数据提取 → 语义分块 → 组装
    """
    processed: list[dict] = []

    # 复用同一个 OpenAI 客户端
    client = get_openai_client() if is_extract_meta else None

    for doc_idx, doc in enumerate(documents):
        filename = doc.get("source", "unknown")
        logger.info("[%d/%d] 处理: %s", doc_idx + 1, len(documents), filename)

        cleaned = clean_text(doc["text"])

        if is_extract_meta:
            llm_meta = extract_metadata(cleaned, filename=filename, client=client)
        else:
            llm_meta = {
                "author": None, "year": None,
                "category": _guess_category(filename),
                "language": "zh", "summary": "",
            }

        # 合并 Front-Matter 元数据
        fm_meta = doc.get("fm_meta", {})
        if fm_meta:
            llm_meta = _merge_fm_meta(fm_meta, llm_meta)

        chunks = chunk_text(cleaned, chunk_size=chunk_size, overlap=overlap)

        for idx, chunk in enumerate(chunks):
            processed.append({
                "id": f"{filename}_{idx}",
                "text": chunk["text"],
                "metadata": {
                    "source":     filename,
                    "path":       doc.get("path", ""),
                    "chunk_id":   idx,
                    "char_start": chunk["char_start"],
                    "char_end":   chunk["char_end"],
                    "author":     llm_meta.get("author") or "",
                    "year":       llm_meta.get("year") or 0,
                    "category":   llm_meta.get("category", "general"),
                    "language":   llm_meta.get("language", "zh"),
                    "summary":    llm_meta.get("summary", ""),
                },
            })

    return processed
