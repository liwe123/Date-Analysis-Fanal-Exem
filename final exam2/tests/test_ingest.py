"""
test_ingest.py
==============
对 ingest 模块的单元测试。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingest import _parse_front_matter, load_text_files, load_jsonl_file, load_jsonl_files, _parse_date


class TestParseFrontMatter:
    def test_with_front_matter(self):
        text = "---\nauthor: Alice\nyear: 2024\n---\nbody text"
        meta, body = _parse_front_matter(text)
        assert meta["author"] == "Alice"
        assert meta["year"] == 2024
        assert body == "body text"

    def test_without_front_matter(self):
        text = "普通文本内容"
        meta, body = _parse_front_matter(text)
        assert meta == {}
        assert body == text

    def test_empty_front_matter(self):
        text = "---\n---\n正文"
        meta, body = _parse_front_matter(text)
        assert meta == {}
        assert body == text


class TestLoadTextFiles:
    def test_loads_md_and_txt(self, tmp_path):
        (tmp_path / "test.md").write_text("# 标题\n内容", encoding="utf-8")
        (tmp_path / "test.txt").write_text("纯文本", encoding="utf-8")
        (tmp_path / "test.csv").write_text("a,b,c", encoding="utf-8")  # 不支持

        docs = load_text_files(tmp_path, recursive=False)
        assert len(docs) == 2
        names = {d["source"] for d in docs}
        assert "test.md" in names
        assert "test.txt" in names
        assert "test.csv" not in names

    def test_text_loader_skips_jsonl(self, tmp_path):
        (tmp_path / "dataset.jsonl").write_text(
            '{"doc_id": "1", "content": "jsonl content"}\n',
            encoding="utf-8",
        )

        docs = load_text_files(tmp_path, recursive=False)

        assert docs == []

    def test_empty_directory(self, tmp_path):
        docs = load_text_files(tmp_path)
        assert docs == []

    def test_nonexistent_directory(self):
        docs = load_text_files(Path("/nonexistent/path"))
        assert docs == []

    def test_front_matter_parsed(self, tmp_path):
        content = "---\nauthor: Test\n---\nBody text"
        (tmp_path / "fm.md").write_text(content, encoding="utf-8")
        docs = load_text_files(tmp_path, recursive=False)
        assert len(docs) == 1
        assert docs[0]["fm_meta"]["author"] == "Test"
        assert "Body text" in docs[0]["text"]

    def test_recursive_false(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.md").write_text("root", encoding="utf-8")
        (sub / "b.md").write_text("nested", encoding="utf-8")

        docs = load_text_files(tmp_path, recursive=False)
        assert len(docs) == 1

    def test_recursive_true(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.md").write_text("root", encoding="utf-8")
        (sub / "b.md").write_text("nested", encoding="utf-8")

        docs = load_text_files(tmp_path, recursive=True)
        assert len(docs) == 2

    @patch("src.ingest.HAS_PYMUPDF", True)
    @patch("src.ingest.fitz.open")
    def test_pdf_loading(self, mock_fitz_open, tmp_path):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "PDF 正文"
        mock_doc.__enter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content", encoding="utf-8")

        docs = load_text_files(tmp_path, recursive=False)
        assert len(docs) == 1
        assert docs[0]["text"] == "PDF 正文"

    def test_empty_file(self, tmp_path):
        (tmp_path / "empty.txt").write_text("", encoding="utf-8")
        docs = load_text_files(tmp_path, recursive=False)
        assert docs == []

    def test_bad_yaml_front_matter(self, tmp_path):
        content = "---\nauthor: [Alice\n---\nBody text"
        (tmp_path / "bad.md").write_text(content, encoding="utf-8")
        docs = load_text_files(tmp_path, recursive=False)
        assert len(docs) == 1
        assert docs[0]["fm_meta"] == {}
        assert docs[0]["text"] == "Body text"


class TestParseDate:
    def test_valid_date_formats(self):
        assert _parse_date("18-12-2024") == 2024
        assert _parse_date("2026-04-09 09:26:01") == 2026
        assert _parse_date("2024/06/10") == 2024
        assert _parse_date("Dec 25, 2025") == 2025
        assert _parse_date("2024-08-02T16:02:16.471382Z") == 2024

    def test_invalid_date_values(self):
        assert _parse_date(None) is None
        assert _parse_date("") is None
        assert _parse_date("tomorrow") is None
        assert _parse_date("yesterday") is None
        assert _parse_date("invalid") is None

    def test_year_extraction_fallback(self):
        assert _parse_date("some year 2023 here") == 2023
        assert _parse_date("no year here") is None


class TestLoadJsonlFile:
    def test_loads_jsonl(self, tmp_path):
        jsonl_content = (
            '{"doc_id": "doc_001", "doc_type": "ticket", "title": "Test", '
            '"content": "Hello World", "author": "Alice", "category": "api"}\n'
        )
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")

        assert len(docs) == 1
        assert docs[0]["source"] == "test_doc_001"
        assert docs[0]["text"] == "Hello World"
        assert docs[0]["fm_meta"]["author"] == "Alice"
        assert docs[0]["fm_meta"]["category"] == "api"
        assert docs[0]["fm_meta"]["doc_type"] == "ticket"

    def test_empty_content_skipped(self, tmp_path):
        jsonl_content = '{"doc_id": "doc_001", "content": ""}\n'
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 0

    def test_invalid_json_skipped(self, tmp_path):
        jsonl_content = 'invalid json\n{"doc_id": "doc_001", "content": "valid"}\n'
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 1
        assert docs[0]["text"] == "valid"

    def test_multiple_records(self, tmp_path):
        jsonl_content = (
            '{"doc_id": "doc_001", "content": "first"}\n'
            '{"doc_id": "doc_002", "content": "second"}\n'
            '{"doc_id": "doc_003", "content": "third"}\n'
        )
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 3
        assert docs[0]["source"] == "test_doc_001"
        assert docs[1]["source"] == "test_doc_002"
        assert docs[2]["source"] == "test_doc_003"

    def test_date_parsing(self, tmp_path):
        jsonl_content = (
            '{"doc_id": "doc_001", "content": "test", "created_at": "18-12-2024"}\n'
        )
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 1
        assert docs[0]["fm_meta"]["year"] == 2024

    def test_null_fields(self, tmp_path):
        jsonl_content = (
            '{"doc_id": "doc_001", "content": "test", "author": null, '
            '"created_at": null, "category": ""}\n'
        )
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 1
        assert docs[0]["fm_meta"]["author"] is None
        assert docs[0]["fm_meta"]["year"] is None

    def test_empty_doc_id_generates_unique_source(self, tmp_path):
        jsonl_content = (
            '{"doc_id": "", "content": "first empty"}\n'
            '{"doc_id": "", "content": "second empty"}\n'
            '{"doc_id": "doc_003", "content": "has id"}\n'
        )
        (tmp_path / "test.jsonl").write_text(jsonl_content, encoding="utf-8")

        docs = load_jsonl_file(tmp_path / "test.jsonl")
        assert len(docs) == 3
        sources = [d["source"] for d in docs]
        # 确保所有source唯一
        assert len(sources) == len(set(sources))
        # 空doc_id应使用行号生成source
        assert "test_line_1" in sources
        assert "test_line_2" in sources
        assert "test_doc_003" in sources


class TestLoadJsonlFiles:
    def test_loads_multiple_jsonl_files(self, tmp_path):
        (tmp_path / "a.jsonl").write_text(
            '{"doc_id": "doc_001", "content": "file a"}\n', encoding="utf-8"
        )
        (tmp_path / "b.jsonl").write_text(
            '{"doc_id": "doc_002", "content": "file b"}\n', encoding="utf-8"
        )

        docs = load_jsonl_files(tmp_path, recursive=False)
        assert len(docs) == 2

    def test_recursive_false(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.jsonl").write_text(
            '{"doc_id": "doc_001", "content": "root"}\n', encoding="utf-8"
        )
        (sub / "b.jsonl").write_text(
            '{"doc_id": "doc_002", "content": "nested"}\n', encoding="utf-8"
        )

        docs = load_jsonl_files(tmp_path, recursive=False)
        assert len(docs) == 1

    def test_recursive_true(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.jsonl").write_text(
            '{"doc_id": "doc_001", "content": "root"}\n', encoding="utf-8"
        )
        (sub / "b.jsonl").write_text(
            '{"doc_id": "doc_002", "content": "nested"}\n', encoding="utf-8"
        )

        docs = load_jsonl_files(tmp_path, recursive=True)
        assert len(docs) == 2

    def test_empty_directory(self, tmp_path):
        docs = load_jsonl_files(tmp_path)
        assert docs == []
