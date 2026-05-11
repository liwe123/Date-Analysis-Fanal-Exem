"""
test_ingest.py
==============
对 ingest 模块的单元测试。
"""

import tempfile
from pathlib import Path

from src.ingest import _parse_front_matter, load_text_files


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
