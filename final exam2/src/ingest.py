"""
ingest.py
=========
文档摄取模块：读取原始文件，支持 .md / .txt / .pdf 与 .jsonl 格式。

返回的文档字典中包含从文件名/YAML 前置元数据/JSONL 字段推断的基础信息。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from src.utils import get_logger

logger = get_logger("ingest")

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from dateutil import parser as dateutil_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """
    解析 Markdown YAML Front-Matter（--- ... --- 块）。
    返回 (metadata_dict, body_text)。若无 Front-Matter 则返回 ({}, text)。
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    m = pattern.match(text)
    if not m:
        return {}, text

    fm_raw = m.group(1)
    body = text[m.end():]

    try:
        meta = yaml.safe_load(fm_raw)
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError as e:
        logger.warning("Front-Matter 解析 YAML 失败: %s", e)
        meta = {}

    return meta, body


def load_text_files(data_dir: str | Path, recursive: bool = True) -> list[dict]:
    """
    遍历目录，读取 .md / .txt / .pdf 文件。

    返回的每个文档字典包含：
      source   : 文件名（不含路径）
      path     : 完整路径字符串
      text     : 文件正文（已剥离 Front-Matter）
      fm_meta  : Front-Matter 元数据（可能为空 {}）
    """
    data_path = Path(data_dir)
    documents: list[dict] = []

    if not data_path.exists():
        logger.warning("目录不存在: %s", data_path)
        return documents

    iterator = data_path.rglob("*") if recursive else data_path.glob("*")

    for file_path in sorted(iterator):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        if file_path.suffix.lower() == ".pdf":
            if not HAS_PYMUPDF:
                logger.warning("跳过 %s，未安装 PyMuPDF。请运行 pip install PyMuPDF。", file_path.name)
                continue
            try:
                with fitz.open(str(file_path)) as doc:
                    raw = "\n".join(page.get_text() for page in doc)
                raw = raw.strip()
            except Exception as e:
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                logger.error("解析 PDF 失败 %s: %s", file_path.name, e)
                continue
        else:
            raw = file_path.read_text(encoding="utf-8", errors="ignore").strip()

        if not raw:
            continue

        fm_meta, body = _parse_front_matter(raw)

        documents.append({
            "source":  file_path.name,
            "path":    str(file_path),
            "text":    body,
            "fm_meta": fm_meta,
        })

    logger.info("读取到 %d 个文件。", len(documents))
    return documents


# ── JSONL 支持 ──────────────────────────────────────────────────────

def _parse_date(date_str: str | None) -> int | None:
    """
    从日期字符串中提取年份。

    支持多种日期格式：
      - "18-12-2024" (DD-MM-YYYY)
      - "2026-04-09 09:26:01" (YYYY-MM-DD HH:MM:SS)
      - "2024/06/10" (YYYY/MM/DD)
      - "Dec 25, 2025" (Month DD, YYYY)
      - ISO 8601 格式

    参数：
      date_str: 日期字符串

    返回值：
      年份整数，解析失败返回 None
    """
    if not date_str or not isinstance(date_str, str):
        return None

    # 跳过无效值
    date_str = date_str.strip().lower()
    if date_str in ("tomorrow", "yesterday", "today", "now", ""):
        return None

    # 尝试使用 dateutil 解析
    if HAS_DATEUTIL:
        try:
            dt = dateutil_parser.parse(date_str, dayfirst=False)
            return dt.year
        except (ValueError, TypeError, OverflowError):
            pass

    # 回退：尝试正则提取年份
    year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
    if year_match:
        return int(year_match.group())

    return None


def load_jsonl_file(file_path: Path) -> list[dict]:
    """
    读取单个 JSONL 文件，返回文档字典列表。

    返回的每个文档字典包含：
      source   : "{文件名}_{doc_id}"
      path     : 完整路径字符串
      text     : content 字段内容
      fm_meta  : 从 JSONL 字段映射的元数据

    参数：
      file_path: JSONL 文件路径

    返回值：
      文档字典列表
    """
    documents: list[dict] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("JSONL 第 %d 行解析失败: %s", line_num, e)
                continue

            doc_id = record.get("doc_id", "")
            content = record.get("content", "").strip()
            if not content:
                continue

            # 构建 source 标识（确保唯一性）
            source = f"{file_path.stem}_{doc_id}" if doc_id else f"{file_path.stem}_line_{line_num}"

            # 映射元数据
            created_at = record.get("created_at")
            fm_meta = {
                "doc_type": record.get("doc_type", ""),
                "title": record.get("title", ""),
                "author": record.get("author"),
                "category": record.get("category", ""),
                "created_at": created_at,
                "is_resolved": record.get("is_resolved"),
                "year": _parse_date(created_at),
            }

            documents.append({
                "source": source,
                "path": str(file_path),
                "text": content,
                "fm_meta": fm_meta,
            })

    logger.info("从 %s 读取到 %d 个文档。", file_path.name, len(documents))
    return documents


def load_jsonl_files(data_dir: str | Path, recursive: bool = True) -> list[dict]:
    """
    遍历目录，读取所有 .jsonl 文件。

    参数：
      data_dir: 数据目录路径
      recursive: 是否递归遍历子目录

    返回值：
      文档字典列表
    """
    data_path = Path(data_dir)
    documents: list[dict] = []

    if not data_path.exists():
        logger.warning("目录不存在: %s", data_path)
        return documents

    iterator = data_path.rglob("*.jsonl") if recursive else data_path.glob("*.jsonl")

    for file_path in sorted(iterator):
        if not file_path.is_file():
            continue
        docs = load_jsonl_file(file_path)
        documents.extend(docs)

    logger.info("JSONL 文件共读取到 %d 个文档。", len(documents))
    return documents
