"""
ingest.py
=========
文档摄取模块：读取原始文件，支持 .md / .txt / .pdf 格式。

返回的文档字典中包含从文件名/YAML 前置元数据推断的基础信息。
"""

from __future__ import annotations

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
    except yaml.YAMLError:
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
