"""
test_embed_store.py
===================
对 embed_store 模块的单元测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.embed_store import VectorStore


class TestVectorStoreInit:
    def test_default_collection_name(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.get_embedding_model_name", return_value="test-emb"):
            store = VectorStore()
            assert store.embedding_model == "test-emb"

    def test_custom_collection_name(self):
        with patch("src.embed_store.chromadb.PersistentClient") as mock_client, \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            VectorStore(collection_name="my_collection")
            mock_instance.get_or_create_collection.assert_called_once_with(
                name="my_collection",
                metadata={"hnsw:space": "cosine"},
            )


class TestDeleteCollection:
    def test_requires_confirm(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            with pytest.raises(RuntimeError, match="confirm=True"):
                store.delete_collection()

    def test_delete_with_confirm(self):
        with patch("src.embed_store.chromadb.PersistentClient") as mock_client, \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            store = VectorStore()
            store.delete_collection(confirm=True)
            mock_instance.delete_collection.assert_called_once()


class TestSearch:
    def test_search_returns_results(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.get_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])

            mock_results = {
                "documents": [["文档内容"]],
                "metadatas": [[{"source": "test.md", "year": 2024}]],
                "distances": [[0.15]],
            }
            store.collection.query = MagicMock(return_value=mock_results)

            results = store.search("测试查询", top_k=1)
            assert len(results) == 1
            assert results[0]["text"] == "文档内容"
            assert results[0]["source"] == "test.md"
            assert results[0]["score"] == 0.15

    def test_max_distance_filter(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.get_embedding = MagicMock(return_value=[0.1, 0.2])

            mock_results = {
                "documents": [["远距离文档", "近距离文档"]],
                "metadatas": [[{"source": "far.md"}, {"source": "near.md"}]],
                "distances": [[1.8, 0.2]],
            }
            store.collection.query = MagicMock(return_value=mock_results)

            results = store.search("测试", top_k=5, max_distance=0.5)
            assert len(results) == 1
            assert results[0]["source"] == "near.md"

    def test_where_clause_fallback(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.get_embedding = MagicMock(return_value=[0.1, 0.2])

            call_count = 0
            def side_effect(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ValueError("Invalid where filter")
                return {"documents": [["fallback"]], "metadatas": [[{"source": "fb.md"}]], "distances": [[0.0]]}
            store.collection.query = MagicMock(side_effect=side_effect)

            results = store.search("测试", top_k=1, where={"invalid": "field"})
            assert len(results) == 1
            assert results[0]["source"] == "fb.md"
            assert call_count == 2


class TestCountAndListSources:
    def test_count(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.collection.count = MagicMock(return_value=42)
            assert store.count() == 42

    def test_list_sources_empty(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.collection.count = MagicMock(return_value=0)
            assert store.list_sources() == []

    def test_list_sources(self):
        with patch("src.embed_store.chromadb.PersistentClient"), \
             patch("src.embed_store.get_openai_client"), \
             patch("src.embed_store.use_local_embedding", return_value=False), \
             patch("src.embed_store.clean_env", return_value=""):
            store = VectorStore()
            store.collection.count = MagicMock(return_value=2)
            store.collection.get = MagicMock(return_value={
                "metadatas": [
                    {"source": "a.md"},
                    {"source": "b.md"},
                    {"source": "a.md"},
                ]
            })
            sources = store.list_sources()
            assert sources == ["a.md", "b.md"]
