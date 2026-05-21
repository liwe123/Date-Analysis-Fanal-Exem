"""
test_preprocess.py
==================
对 preprocess 模块的单元测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.preprocess import (
    _guess_category,
    _merge_fm_meta,
    _safe_json_parse,
    chunk_text,
    clean_text,
    extract_metadata,
    process_documents,
)


class TestCleanText:
    def test_removes_html_tags(self):
        assert clean_text("<p>Hello</p> <b>World</b>") == "Hello World"

    def test_decodes_html_entities(self):
        assert clean_text("a &amp; b &lt; c") == "a & b < c"

    def test_merges_blank_lines(self):
        text = "line1\n\n\n\nline2"
        assert clean_text(text) == "line1\n\nline2"

    def test_strips_control_chars(self):
        text = "hello\x00\x01world"
        assert clean_text(text) == "helloworld"

    def test_preserves_newlines_and_tabs(self):
        text = "line1\nline2\ttab"
        result = clean_text(text)
        assert "\n" in result


class TestChunkText:
    def test_basic_chunking(self):
        text = "段落一。\n\n段落二。\n\n段落三。"
        chunks = chunk_text(text, chunk_size=100, overlap=20, min_chunk_chars=0)
        assert len(chunks) >= 1
        assert all("text" in c for c in chunks)

    def test_chunk_size_respected(self):
        text = "a" * 500 + "\n\n" + "b" * 500
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        for c in chunks:
            assert len(c["text"]) <= 200 + 50  # some tolerance for sentence boundary

    def test_empty_text(self):
        assert chunk_text("", chunk_size=100) == []

    def test_single_short_paragraph(self):
        chunks = chunk_text("短文本。", chunk_size=100, overlap=20, min_chunk_chars=0)
        assert len(chunks) == 1

    def test_invalid_overlap(self):
        with pytest.raises(ValueError):
            chunk_text("test", chunk_size=10, overlap=20)

    def test_has_char_offsets(self):
        chunks = chunk_text("第一段。\n\n第二段。", chunk_size=100, overlap=20)
        for c in chunks:
            assert "char_start" in c
            assert "char_end" in c
            assert c["char_end"] > c["char_start"]

    def test_sentence_boundary_splitting(self):
        """验证分块尊重句子边界。"""
        text = "这是第一句话。这是第二句话。这是环境配置 1.0.0 测试。这是第四句话。"
        chunks = chunk_text(text, chunk_size=30, overlap=5)
        for c in chunks:
            t = c["text"]
            assert len(t) <= 30 or t.endswith("。") or "1.0.0" in t


class TestGuessCategory:
    def test_wiki_prefix(self):
        assert _guess_category("wiki_test.md") == "wiki"

    def test_notice_prefix(self):
        assert _guess_category("notice_01.md") == "notice"

    def test_faq_prefix(self):
        assert _guess_category("faq_exam.md") == "faq"

    def test_case_study_prefix(self):
        assert _guess_category("case_study_01.md") == "case_study"

    def test_unknown_prefix(self):
        assert _guess_category("random.md") == "general"


class TestMergeFmMeta:
    def test_fm_overrides_llm(self):
        fm = {"author": "张三", "year": "2024"}
        llm = {"author": "李四", "year": 2023, "category": "wiki", "language": "zh", "summary": "test"}
        result = _merge_fm_meta(fm, llm)
        assert result["author"] == "张三"
        assert result["year"] == 2024
        assert result["category"] == "wiki"  # not overridden

    def test_empty_fm(self):
        llm = {"author": "A", "year": 2023, "category": "wiki"}
        result = _merge_fm_meta({}, llm)
        assert result == llm


class TestSafeJsonParse:
    def test_valid_json(self):
        assert _safe_json_parse('{"author": "Bob"}') == {"author": "Bob"}

    def test_empty_json(self):
        assert _safe_json_parse("") == {}
        assert _safe_json_parse("   ") == {}

    def test_json_with_codeblock_and_comments(self):
        raw = """
        // 这是一个注释
        {
            "author": "Alice", // 另一个注释
            "year": 2026
        }
        """
        parsed = _safe_json_parse(raw)
        assert parsed["author"] == "Alice"
        assert parsed["year"] == 2026

    def test_invalid_json_fallback(self):
        raw = "这不是JSON"
        assert _safe_json_parse(raw, default={"fallback": True}) == {"fallback": True}


class TestExtractMetadata:
    @patch("src.preprocess.get_model_name", return_value="gpt-4o-mini")
    def test_extract_success(self, mock_model, mock_openai_client):
        mock_choices = MagicMock()
        mock_choices.message.content = '{"author": "Eve", "year": "2026", "category": "notice"}'
        mock_openai_client.chat.completions.create.return_value.choices = [mock_choices]

        meta = extract_metadata("一些测试文档正文内容", filename="notice_test.md", client=mock_openai_client)
        assert meta["author"] == "Eve"
        assert meta["year"] == 2026
        assert meta["category"] == "notice"

    @patch("src.preprocess.get_model_name", return_value="gpt-4o-mini")
    def test_extract_exception_fallback(self, mock_model, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        meta = extract_metadata("正文", filename="wiki_test.md", client=mock_openai_client)
        assert meta["author"] is None
        assert meta["year"] is None
        assert meta["category"] == "wiki"


class TestProcessDocuments:
    def test_is_extract_meta_false(self):
        docs = [{"source": "wiki_01.md", "path": "p.md", "text": "Hadoop tutorial"}]
        processed = process_documents(docs, is_extract_meta=False)
        assert len(processed) >= 1
        meta = processed[0]["metadata"]
        assert meta["source"] == "wiki_01.md"
        assert meta["category"] == "wiki"
        assert meta["author"] is None
        assert meta["year"] is None

    @patch("src.preprocess.get_openai_client")
    def test_is_extract_meta_true(self, mock_get_client):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"author": "Carl", "year": 2024, "category": "wiki"}'
        mock_client.chat.completions.create.return_value.choices = [mock_choice]
        mock_get_client.return_value = mock_client

        docs = [{"source": "wiki_01.md", "path": "p.md", "text": "Hadoop tutorial"}]
        processed = process_documents(docs, is_extract_meta=True, max_workers=2)
        assert len(processed) >= 1
        meta = processed[0]["metadata"]
        assert meta["author"] == "Carl"
        assert meta["year"] == 2024
