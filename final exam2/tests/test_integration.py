"""
test_integration.py
===================
集成测试：验证从文档加载到向量搜索的完整流水线。
（使用 mock 避免真实 API 和 ChromaDB 依赖）
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestIngestToPreprocessPipeline:
    """验证 ingest → preprocess 流水线。"""

    def test_load_and_process(self, tmp_path):
        (tmp_path / "doc.md").write_text(
            "---\nauthor: Alice\nyear: 2024\ncategory: wiki\n---\n"
            "# Title\n\nThis is the main content. This is the second sentence.",
            encoding="utf-8",
        )

        with patch("src.preprocess.get_openai_client"), \
             patch("src.preprocess.get_model_name", return_value="test-model"):
            from src.ingest import load_text_files
            from src.preprocess import process_documents

            docs = load_text_files(tmp_path, recursive=False)
            assert len(docs) == 1

            processed = process_documents(docs, chunk_size=700, overlap=120, is_extract_meta=False)
            assert len(processed) >= 1
            for p in processed:
                assert "id" in p
                assert "text" in p
                assert "metadata" in p
                assert p["metadata"]["author"] == "Alice"
                assert p["metadata"]["year"] == 2024
                assert p["metadata"]["category"] == "wiki"

    def test_empty_directory_pipeline(self, tmp_path):
        with patch("src.preprocess.get_openai_client"), \
             patch("src.preprocess.get_model_name", return_value="test-model"):
            from src.ingest import load_text_files
            from src.preprocess import process_documents

            docs = load_text_files(tmp_path)
            assert docs == []
            processed = process_documents(docs, is_extract_meta=False)
            assert processed == []


class TestSearchAndAnswerPipeline:
    """验证搜索 → 回答流水线。"""

    def test_full_qa_flow(self):
        mock_client = MagicMock()
        mock_parser_resp = MagicMock()
        mock_parser_resp.choices = [MagicMock()]
        mock_parser_resp.choices[0].message.content = (
            '{"search_query": "What is RAG", "filters": {"year": null, "category": "wiki"}}'
        )

        mock_answer_resp = MagicMock()
        mock_answer_resp.choices = [MagicMock()]
        mock_answer_resp.choices[0].message.content = "RAG is retrieval augmented generation [Source: wiki.md]"

        mock_client.chat.completions.create.side_effect = [
            mock_parser_resp,
            mock_answer_resp,
        ]

        with patch("src.query_parser.get_openai_client", return_value=mock_client), \
             patch("src.query_parser.get_model_name", return_value="test-model"), \
             patch("src.qa.get_model_name", return_value="test-model"), \
             patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client", return_value=mock_client), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value="test-emb"):

            from src.query_parser import parse_query
            from src.qa import generate_answer

            parsed = parse_query("What is RAG", client=mock_client)
            assert parsed["search_query"] == "What is RAG"
            assert parsed["filters"] == {"category": "wiki"}

            docs = [{
                "text": "RAG结合检索和生成",
                "source": "wiki.md",
                "metadata": {"source": "wiki.md", "category": "wiki"},
                "score": 0.1,
            }]

            answer = generate_answer("What is RAG", docs, client=mock_client)
            assert "RAG" in answer
            assert "wiki.md" in answer


class TestNestedYamlFrontMatter:
    """验证 pyyaml 能解析嵌套 YAML。"""

    def test_nested_yaml(self):
        from src.ingest import _parse_front_matter

        text = (
            "---\n"
            "author: Alice\n"
            "tags:\n"
            "  - rag\n"
            "  - llm\n"
            "year: 2024\n"
            "---\n"
            "body text"
        )
        meta, body = _parse_front_matter(text)
        assert meta["author"] == "Alice"
        assert meta["year"] == 2024
        assert meta["tags"] == ["rag", "llm"]
        assert body == "body text"
