"""
test_retrieval_fallback.py
==========================
对原始语料关键词兜底检索的单元测试。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.retrieval_fallback import (
    get_chroma_sqlite_stats,
    search_chroma_sqlite,
    search_raw_corpus,
)


def _create_chroma_sqlite_fixture(db_path: Path) -> None:
    """创建一个最小 Chroma SQLite 结构，用于验证兜底检索。"""
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE VIRTUAL TABLE embedding_fulltext_search USING fts5(string_value)")
    conn.execute(
        """
        CREATE TABLE embedding_metadata (
            id INTEGER,
            key TEXT,
            string_value TEXT,
            int_value INTEGER,
            float_value REAL,
            bool_value INTEGER,
            PRIMARY KEY (id, key)
        )
        """
    )
    conn.commit()
    conn.close()


def _insert_chroma_doc(db_path: Path, item_id: int, source: str, text: str) -> None:
    """写入一条 Chroma 文档正文和常用元数据。"""
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO embeddings(id) VALUES (?)", (item_id,))
    conn.execute(
        "INSERT INTO embedding_fulltext_search(rowid, string_value) VALUES (?, ?)",
        (item_id, text),
    )
    rows = [
        (item_id, "chroma:document", text, None, None, None),
        (item_id, "source", source, None, None, None),
        (item_id, "path", "/root/final-exam2/data/rag_documents_raw.jsonl", None, None, None),
        (item_id, "chunk_id", None, 0, None, None),
        (item_id, "language", "zh", None, None, None),
    ]
    conn.executemany(
        """
        INSERT INTO embedding_metadata(
            id, key, string_value, int_value, float_value, bool_value
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def test_get_chroma_sqlite_stats(tmp_path):
    db_path = tmp_path / "chroma.sqlite3"
    _create_chroma_sqlite_fixture(db_path)
    _insert_chroma_doc(db_path, 1, "source_a.md", "第一条文档")
    _insert_chroma_doc(db_path, 2, "source_b.md", "第二条文档")

    count, sources, source_count = get_chroma_sqlite_stats(db_path=db_path)

    assert count == 2
    assert sources == ["source_a.md", "source_b.md"]
    assert source_count == 2


class TestSearchRawCorpus:
    def test_returns_matching_chunks(self, tmp_path):
        source = tmp_path / "term_rag.md"
        source.write_text(
            "检索增强生成 RAG 会先检索外部知识，再把相关片段交给大语言模型生成回答。",
            encoding="utf-8",
        )

        results = search_raw_corpus(
            "检索增强生成 RAG",
            top_k=1,
            data_dir=tmp_path,
        )

        assert len(results) == 1
        assert results[0]["source"] == "term_rag.md"
        assert results[0]["metadata"]["retrieval"] == "raw_keyword_fallback"

    def test_returns_empty_when_no_terms_match(self, tmp_path):
        source = tmp_path / "term_batch.md"
        source.write_text("批处理适合离线处理大规模数据。", encoding="utf-8")

        results = search_raw_corpus(
            "量子通信",
            top_k=3,
            data_dir=tmp_path,
        )

        assert results == []

    def test_returns_token_quota_guidance(self, tmp_path):
        source = tmp_path / "faq_api_token_limits.md"
        source.write_text(
            "API 配额耗尽或余额不足时，先检查供应商控制台，再充值或更换可用 API Key。",
            encoding="utf-8",
        )

        results = search_raw_corpus(
            "大模型 Token 额度耗尽后怎么处理？",
            top_k=1,
            data_dir=tmp_path,
        )

        assert len(results) == 1
        assert results[0]["source"] == "faq_api_token_limits.md"


class TestSearchChromaSqlite:
    def test_returns_matching_fts_document(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "rag_documents_raw_doc_000001",
            "token 过期时需要 refresh token，然后检查 scope 是否仍然 Active。",
        )

        results = search_chroma_sqlite("token用完怎么办", top_k=1, db_path=db_path)

        assert len(results) == 1
        assert results[0]["source"] == "rag_documents_raw_doc_000001"
        assert results[0]["metadata"]["retrieval"] == "chroma_sqlite_keyword_fallback"

    def test_expands_token_exhaustion_to_workaround_terms(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "token_scope_note",
            "FAQ: E1001 表示认证失败，通常与 token scope 不匹配。",
        )
        _insert_chroma_doc(
            db_path,
            2,
            "token_refresh_workaround",
            "用户反馈 token 过期，Support 建议 Temporary workaround: refresh token and retry。",
        )

        results = search_chroma_sqlite("token用完怎么办", top_k=1, db_path=db_path)

        assert len(results) == 1
        assert results[0]["source"] == "token_refresh_workaround"

    def test_token_quota_query_rejects_expired_token_workaround(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "token_refresh_workaround",
            "用户反馈 token 过期，Temporary workaround: refresh token and retry。",
        )
        _insert_chroma_doc(
            db_path,
            2,
            "token_scope_note",
            "E1001 表示认证失败，通常与 token scope 不匹配。",
        )

        results = search_chroma_sqlite(
            "大模型 Token 额度耗尽后怎么处理？",
            top_k=1,
            db_path=db_path,
        )

        assert results == []

    def test_token_quota_query_prefers_quota_guidance(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "token_refresh_workaround",
            "用户反馈 token 过期，Temporary workaround: refresh token and retry。",
        )
        _insert_chroma_doc(
            db_path,
            2,
            "api_quota_workaround",
            "API 配额耗尽或余额不足时，先检查控制台，再充值或更换 API Key。",
        )

        results = search_chroma_sqlite(
            "大模型 Token 额度耗尽后怎么处理？",
            top_k=1,
            db_path=db_path,
        )

        assert len(results) == 1
        assert results[0]["source"] == "api_quota_workaround"

    def test_guidance_query_prefers_actionable_workaround(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "http_429_log",
            "HTTP 429 too many requests HTTP 429 too many requests HTTP 429 too many requests",
        )
        _insert_chroma_doc(
            db_path,
            2,
            "http_429_workaround",
            "用户反馈 HTTP 429，Support 建议 Temporary workaround: refresh token and retry。",
        )

        results = search_chroma_sqlite("HTTP 429 怎么处理", top_k=1, db_path=db_path)

        assert len(results) == 1
        assert results[0]["source"] == "http_429_workaround"

    def test_prefers_complete_domain_topic_over_generic_database_terms(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            1,
            "hive_notes.md",
            "传统数据库与 Hive 数据库在数据仓库场景中存在多项区别。",
        )
        _insert_chroma_doc(
            db_path,
            2,
            "vector_db_notes.md",
            "向量数据库存储向量并按相似度检索，适合语义搜索。",
        )

        results = search_chroma_sqlite(
            "向量数据库和传统数据库有什么区别？",
            top_k=1,
            db_path=db_path,
        )

        assert len(results) == 1
        assert results[0]["source"] == "vector_db_notes.md"

    def test_returns_matching_chinese_like_document(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            2,
            "queue_notes",
            "缓存用完后应先清理临时目录，再检查队列积压和重试策略。",
        )

        results = search_chroma_sqlite("缓存用完怎么办", top_k=1, db_path=db_path)

        assert len(results) == 1
        assert results[0]["source"] == "queue_notes"
        assert "缓存用完" in results[0]["text"]

    def test_ignores_source_only_matches(self, tmp_path):
        db_path = tmp_path / "chroma.sqlite3"
        _create_chroma_sqlite_fixture(db_path)
        _insert_chroma_doc(
            db_path,
            3,
            "rag_documents_raw_doc_000003",
            "HTTP 429 too many requests binary-fragment timeout after 30000ms",
        )

        results = search_chroma_sqlite("RAG", top_k=1, db_path=db_path)

        assert results == []
