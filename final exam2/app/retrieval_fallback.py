"""
retrieval_fallback.py
=====================
原始语料关键词兜底检索辅助函数。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from src.ingest import load_text_files
from src.preprocess import chunk_text, clean_text
from src.utils import get_logger

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CHROMA_SQLITE_PATH = BASE_DIR / "vector_store" / "chroma.sqlite3"
CHROMA_DOCUMENT_KEY = "chroma:document"
QUERY_TOKEN_RE = re.compile(r"[a-zA-Z0-9_+-]{2,}|[\u4e00-\u9fff]{2,}")
FTS_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")
ASCII_TOKEN_RE = re.compile(r"[a-zA-Z0-9_+-]+")
ASCII_TERM_RE = re.compile(r"^[a-zA-Z0-9_+-]+$")
GUIDANCE_QUERY_MARKERS = ("怎么办", "怎么", "如何", "处理", "解决", "失败", "错误", "异常")
GUIDANCE_DOC_MARKERS = ("faq", "workaround", "解决", "处理", "步骤", "检查", "验证", "refresh", "retry", "active")
GUIDANCE_CANDIDATE_TERMS = (
    "workaround",
    "refresh token",
    "retry",
    "support",
    "解决",
    "处理",
    "步骤",
    "检查",
    "验证",
)
GENERIC_GUIDANCE_TERMS = (
    "怎么",
    "么办",
    "么处",
    "完怎",
    "处理",
    "怎么处",
    "么处理",
    "怎么处理",
    "如何",
    "办法",
    "解决",
    "失败",
    "错误",
    "异常",
)
TOKEN_EXHAUSTION_MARKERS = (
    "token用完",
    "token用尽",
    "token耗尽",
    "token过期",
    "token失效",
    "tokenexpired",
    "expiredtoken",
)
TOKEN_EXHAUSTION_TERMS = (
    "token过期",
    "token失效",
    "过期",
    "失效",
    "认证失败",
    "鉴权失败",
    "refresh token",
    "refresh",
    "retry",
    "scope",
    "expired",
    "session expired",
    "workaround",
)
TOKEN_EXHAUSTION_BODY_MARKERS = (
    "token过期",
    "token失效",
    "sessionexpired",
    "refreshtoken",
)
TOKEN_QUOTA_MARKERS = (
    "token额度耗尽",
    "token额度用完",
    "token配额耗尽",
    "token配额用完",
    "api额度耗尽",
    "api额度用完",
    "api配额耗尽",
    "api配额用完",
    "额度耗尽",
    "额度用完",
    "配额耗尽",
    "配额用完",
    "余额不足",
    "insufficientquota",
    "quotaexceeded",
    "creditsexhausted",
)
TOKEN_QUOTA_TERMS = (
    "API 配额耗尽",
    "API 额度耗尽",
    "余额不足",
    "insufficient quota",
    "quota exceeded",
    "充值",
    "更换 API Key",
    "备用模型",
    "限流",
    "上下文超限",
    "缩短提示词",
)
TOKEN_QUOTA_BODY_MARKERS = (
    "api配额耗尽",
    "api额度耗尽",
    "余额不足",
    "insufficientquota",
    "quotaexceeded",
    "充值",
    "备用模型",
    "上下文超限",
)
DOMAIN_TOPIC_EXPANSIONS = {
    "向量数据库": ("向量数据库", "vector database", "vector_db"),
}

logger = get_logger(__name__)


def get_chroma_sqlite_stats(
    db_path: Path | str = CHROMA_SQLITE_PATH,
    source_scan_limit: int = 10000,
    source_return_limit: int = 500,
) -> tuple[int, list[str], int]:
    """通过只读 SQLite 主键上界快速返回文档块数、来源列表和抽样来源数。"""
    sqlite_path = Path(db_path)
    if not sqlite_path.exists() or source_scan_limit <= 0 or source_return_limit <= 0:
        return 0, [], 0

    conn = _connect_readonly_sqlite(sqlite_path)
    try:
        total_row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM embeddings").fetchone()
        total = int(total_row[0]) if total_row else 0
        source_count_row = conn.execute(
            """
            SELECT COUNT(DISTINCT string_value)
            FROM (
                SELECT string_value
                FROM embedding_metadata
                WHERE key = 'source' AND string_value IS NOT NULL
                LIMIT ?
            )
            """,
            (source_scan_limit,),
        ).fetchone()
        source_count = int(source_count_row[0]) if source_count_row else 0
        source_rows = conn.execute(
            """
            SELECT DISTINCT string_value
            FROM (
                SELECT string_value
                FROM embedding_metadata
                WHERE key = 'source' AND string_value IS NOT NULL
                LIMIT ?
            )
            ORDER BY string_value
            LIMIT ?
            """,
            (source_scan_limit, source_return_limit),
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("读取 Chroma SQLite 统计失败: %s", exc)
        return 0, [], 0
    finally:
        conn.close()

    sources = [str(row[0]) for row in source_rows if row[0]]
    return total, sources, source_count


def _is_guidance_query(query: str) -> bool:
    """判断查询是否在询问处理方法或故障解决步骤。"""
    compact_query = _compact_text(query)
    return any(marker in compact_query for marker in GUIDANCE_QUERY_MARKERS)


def _is_token_exhaustion_query(query: str) -> bool:
    """判断查询是否在询问 token 用完、过期或失效。"""
    compact_query = _compact_text(query)
    if _is_token_quota_query(query):
        return False
    return "token" in compact_query and any(
        marker in compact_query for marker in TOKEN_EXHAUSTION_MARKERS
    )


def _is_token_quota_query(query: str) -> bool:
    """判断查询是否在询问 API Token 配额、额度或余额耗尽。"""
    compact_query = _compact_text(query)
    return any(marker in compact_query for marker in TOKEN_QUOTA_MARKERS)


def _extract_query_terms(query: str) -> list[str]:
    """从查询中提取中英文关键词，并为长中文词补充短语片段。"""
    terms: set[str] = set()

    for token in QUERY_TOKEN_RE.findall(query.lower()):
        token = token.strip()
        if not token:
            continue
        terms.add(token)

        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", token):
            for size in (2, 3, 4):
                for idx in range(0, len(token) - size + 1):
                    terms.add(token[idx : idx + size])

    compact_query = _compact_text(query)
    if _is_token_exhaustion_query(query):
        terms.update(TOKEN_EXHAUSTION_TERMS)
    if _is_token_quota_query(query):
        terms.update(TOKEN_QUOTA_TERMS)
    for marker, expanded_terms in DOMAIN_TOPIC_EXPANSIONS.items():
        if marker in compact_query:
            terms.update(expanded_terms)

    return sorted(terms, key=lambda item: (-len(item), item))


def _compact_text(text: str) -> str:
    """压缩空白并统一小写，便于中英文混合关键词匹配。"""
    return re.sub(r"\s+", "", text.lower())


def _score_chunk(query: str, terms: list[str], text: str, source: str) -> float:
    """计算查询与文档片段之间的轻量关键词相关度。"""
    compact_query = _compact_text(query)
    compact_body = _compact_text(text)
    body_ascii_tokens = ASCII_TOKEN_RE.findall(text.lower())
    source_ascii_tokens = set(ASCII_TOKEN_RE.findall(source.lower()))
    source_text = _compact_text(source)
    body_score = 0.0
    source_score = 0.0

    is_token_quota_query = _is_token_quota_query(query)
    has_token_quota_guidance = any(
        marker in compact_body for marker in TOKEN_QUOTA_BODY_MARKERS
    )
    if is_token_quota_query and not has_token_quota_guidance:
        return 0.0

    if compact_query and len(compact_query) >= 2 and compact_query in compact_body:
        body_score += len(compact_query) * 4

    for term in terms:
        compact_term = _compact_text(term)
        if compact_term in GENERIC_GUIDANCE_TERMS:
            continue
        if any(marker in compact_term for marker in GUIDANCE_QUERY_MARKERS):
            continue

        term_score = max(len(term), 2)
        if ASCII_TERM_RE.fullmatch(term):
            body_count = body_ascii_tokens.count(term)
            has_source_match = term in source_ascii_tokens
        else:
            body_count = compact_body.count(term)
            has_source_match = term in source_text

        if body_count:
            body_score += min(body_count, 4) * term_score
        if has_source_match:
            source_score += term_score * 0.5

    has_topic_match = body_score > 0
    if _is_guidance_query(query) and has_topic_match:
        for marker in GUIDANCE_DOC_MARKERS:
            if marker in compact_body:
                body_score += 30

    if _is_token_exhaustion_query(query) and has_topic_match:
        for marker in TOKEN_EXHAUSTION_BODY_MARKERS:
            if marker in compact_body:
                body_score += 80

    if is_token_quota_query and has_topic_match:
        for marker in TOKEN_QUOTA_BODY_MARKERS:
            if marker in compact_body:
                body_score += 100

    for marker in DOMAIN_TOPIC_EXPANSIONS:
        if marker in compact_query and (marker in compact_body or marker in source_text):
            body_score += len(marker) * 40

    has_guidance_marker = any(marker in compact_body for marker in GUIDANCE_DOC_MARKERS)
    if "http429" in compact_query and "http429" in compact_body:
        body_score += 180 if has_guidance_marker else 20
    if "toomanyrequests" in compact_query and "toomanyrequests" in compact_body:
        body_score += 120 if has_guidance_marker else 10

    if body_score <= 0:
        return 0.0

    return body_score + source_score


def _connect_readonly_sqlite(db_path: Path) -> sqlite3.Connection:
    """以只读模式连接 Chroma SQLite 持久化文件。"""
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _build_fts_query(terms: list[str]) -> str:
    """把查询词转换为 FTS5 安全表达式，仅使用英文/数字 token。"""
    fts_terms: list[str] = []
    seen: set[str] = set()

    for term in terms:
        for token in FTS_TOKEN_RE.findall(term.lower()):
            if token in seen:
                continue
            seen.add(token)
            fts_terms.append(token)

    return " OR ".join(f'"{term}"' for term in fts_terms[:8])


def _select_like_terms(terms: list[str], include_english: bool) -> list[str]:
    """挑选少量 LIKE 查询词，避免对百万行文档做过多全表扫描。"""
    selected: list[str] = []
    seen: set[str] = set()
    chinese_terms = [term for term in terms if re.search(r"[\u4e00-\u9fff]", term)]
    english_terms = [term for term in terms if term not in chinese_terms]
    term_groups = [
        chinese_terms[:2],
        [term for term in chinese_terms if len(term) == 3][:3],
        [term for term in chinese_terms if len(term) == 2][:4],
    ]

    if include_english:
        term_groups.append(english_terms[:4])

    for group in term_groups:
        for term in group:
            if term in seen:
                continue
            seen.add(term)
            selected.append(term)

    return selected[:10]


def _escape_like_term(term: str) -> str:
    """转义 SQLite LIKE 通配符。"""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _append_candidate_ids(target: list[int], seen: set[int], ids: list[int]) -> None:
    """按查询顺序合并候选 id，并去重。"""
    for item_id in ids:
        if item_id in seen:
            continue
        seen.add(item_id)
        target.append(item_id)


def _query_fts_candidate_ids(conn: sqlite3.Connection, fts_query: str, limit: int) -> list[int]:
    """从 Chroma FTS5 表里召回候选文档 id。"""
    if not fts_query:
        return []

    try:
        ranked_rows = conn.execute(
            """
            SELECT rowid
            FROM embedding_fulltext_search
            WHERE embedding_fulltext_search MATCH ?
            ORDER BY bm25(embedding_fulltext_search)
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        natural_rows = conn.execute(
            """
            SELECT rowid
            FROM embedding_fulltext_search
            WHERE embedding_fulltext_search MATCH ?
            LIMIT ?
            """,
            (fts_query, min(limit, 80)),
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("Chroma FTS 兜底检索失败: %s", exc)
        return []

    candidate_ids: list[int] = []
    seen_ids: set[int] = set()
    _append_candidate_ids(candidate_ids, seen_ids, [int(row["rowid"]) for row in ranked_rows])
    _append_candidate_ids(candidate_ids, seen_ids, [int(row["rowid"]) for row in natural_rows])
    return candidate_ids


def _query_like_candidate_ids(
    conn: sqlite3.Connection,
    terms: list[str],
    limit: int,
    include_english: bool,
) -> list[int]:
    """从 Chroma 文档元数据里用 LIKE 召回候选文档 id。"""
    like_terms = _select_like_terms(terms, include_english=include_english)
    if not like_terms:
        return []

    conditions = " OR ".join(["string_value LIKE ? ESCAPE '\\'"] * len(like_terms))
    params = [f"%{_escape_like_term(term)}%" for term in like_terms]

    try:
        rows = conn.execute(
            f"""
            SELECT id
            FROM embedding_metadata
            WHERE key = ?
              AND string_value IS NOT NULL
              AND ({conditions})
            LIMIT ?
            """,
            [CHROMA_DOCUMENT_KEY, *params, limit],
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("Chroma LIKE 兜底检索失败: %s", exc)
        return []

    return [int(row["id"]) for row in rows]


def _select_guidance_topic_terms(terms: list[str]) -> list[str]:
    """为处理类问题挑选主题词，过滤掉“怎么/处理”等泛化问法词。"""
    topic_terms: list[str] = []
    for term in terms:
        compact_term = _compact_text(term)
        if compact_term in GENERIC_GUIDANCE_TERMS:
            continue
        if any(marker in compact_term for marker in GUIDANCE_QUERY_MARKERS):
            continue
        topic_terms.append(term)
    return _select_like_terms(topic_terms, include_english=True)[:6]


def _query_guidance_candidate_ids(
    conn: sqlite3.Connection,
    terms: list[str],
    limit: int,
) -> list[int]:
    """召回同时包含主题词和处理建议标记的候选文档。"""
    topic_terms = _select_guidance_topic_terms(terms)
    if not topic_terms:
        return []

    topic_conditions = " OR ".join(["string_value LIKE ? ESCAPE '\\'"] * len(topic_terms))
    guidance_conditions = " OR ".join(
        ["string_value LIKE ? ESCAPE '\\'"] * len(GUIDANCE_CANDIDATE_TERMS)
    )
    topic_params = [f"%{_escape_like_term(term)}%" for term in topic_terms]
    guidance_params = [f"%{_escape_like_term(term)}%" for term in GUIDANCE_CANDIDATE_TERMS]

    try:
        rows = conn.execute(
            f"""
            SELECT id
            FROM embedding_metadata
            WHERE key = ?
              AND string_value IS NOT NULL
              AND ({topic_conditions})
              AND ({guidance_conditions})
            LIMIT ?
            """,
            [CHROMA_DOCUMENT_KEY, *topic_params, *guidance_params, limit],
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("Chroma 处理建议兜底检索失败: %s", exc)
        return []

    return [int(row["id"]) for row in rows]


def _metadata_value(row: sqlite3.Row) -> str | int | float | bool | None:
    """按 Chroma 元数据列类型取出实际值。"""
    if row["string_value"] is not None:
        return row["string_value"]
    if row["int_value"] is not None:
        return int(row["int_value"])
    if row["float_value"] is not None:
        return float(row["float_value"])
    if row["bool_value"] is not None:
        return bool(row["bool_value"])
    return None


def _load_chroma_records(conn: sqlite3.Connection, candidate_ids: list[int]) -> list[dict]:
    """按候选 id 加载 Chroma 文档正文和元数据。"""
    if not candidate_ids:
        return []

    placeholders = ", ".join(["?"] * len(candidate_ids))
    rows = conn.execute(
        f"""
        SELECT id, key, string_value, int_value, float_value, bool_value
        FROM embedding_metadata
        WHERE id IN ({placeholders})
        """,
        candidate_ids,
    ).fetchall()

    metadata_by_id: dict[int, dict] = {}
    for row in rows:
        item_id = int(row["id"])
        metadata_by_id.setdefault(item_id, {})[row["key"]] = _metadata_value(row)

    records: list[dict] = []
    for item_id in candidate_ids:
        raw_metadata = metadata_by_id.get(item_id, {})
        text = str(raw_metadata.get(CHROMA_DOCUMENT_KEY) or "")
        if not text.strip():
            continue

        source = str(raw_metadata.get("source") or f"chroma_row_{item_id}")
        metadata = {
            key: value
            for key, value in raw_metadata.items()
            if key != CHROMA_DOCUMENT_KEY
        }
        metadata.setdefault("source", source)
        metadata.setdefault("path", "")
        metadata.setdefault("chunk_id", 0)
        metadata.setdefault("category", "chroma_sqlite_fallback")
        metadata.setdefault("language", "zh")
        metadata.setdefault("summary", "")
        metadata["retrieval"] = "chroma_sqlite_keyword_fallback"
        metadata["sqlite_rowid"] = item_id

        records.append({
            "text": text,
            "source": source,
            "metadata": metadata,
        })

    return records


def search_chroma_sqlite(
    query: str,
    top_k: int = 5,
    db_path: Path | str = CHROMA_SQLITE_PATH,
) -> list[dict]:
    """
    直接查询 Chroma SQLite 持久化文件，作为 HNSW 向量段损坏时的百万行语料兜底。

    参数：
      query: 查询字符串。
      top_k: 返回片段数量。
      db_path: Chroma SQLite 文件路径。

    返回值：
      与 VectorStore.search 输出结构兼容的片段列表。
    """
    terms = _extract_query_terms(query)
    if not terms or top_k <= 0:
        return []

    sqlite_path = Path(db_path)
    if not sqlite_path.exists():
        return []

    candidate_limit = max(top_k * 80, 80)
    candidate_ids: list[int] = []
    seen_ids: set[int] = set()
    conn = _connect_readonly_sqlite(sqlite_path)

    try:
        fts_query = _build_fts_query(terms)
        fts_ids = _query_fts_candidate_ids(conn, fts_query, candidate_limit)
        _append_candidate_ids(candidate_ids, seen_ids, fts_ids)

        if len(candidate_ids) < max(top_k * 8, 24):
            like_ids = _query_like_candidate_ids(
                conn,
                terms=terms,
                limit=candidate_limit,
                include_english=not bool(fts_query),
            )
            _append_candidate_ids(candidate_ids, seen_ids, like_ids)

        if _is_guidance_query(query):
            guidance_ids = _query_guidance_candidate_ids(
                conn,
                terms=terms,
                limit=candidate_limit,
            )
            _append_candidate_ids(candidate_ids, seen_ids, guidance_ids)

        records = _load_chroma_records(conn, candidate_ids)
    except sqlite3.Error as exc:
        logger.warning("Chroma SQLite 兜底检索失败: %s", exc)
        return []
    finally:
        conn.close()

    scored: list[tuple[float, dict]] = []
    for item in records:
        raw_score = _score_chunk(
            query=query,
            terms=terms,
            text=item.get("text", ""),
            source=item.get("source", ""),
        )
        if raw_score <= 0:
            continue

        result = {
            "text": item.get("text", ""),
            "source": item.get("source", "unknown"),
            "metadata": dict(item.get("metadata", {})),
            "score": round(1 / (1 + raw_score), 4),
        }
        scored.append((raw_score, result))

    scored.sort(
        key=lambda pair: (
            -pair[0],
            pair[1]["source"],
            pair[1]["metadata"].get("chunk_id", 0),
        )
    )
    return [item for _, item in scored[:top_k]]


def load_raw_corpus_chunks(
    data_dir: Path | str = RAW_DIR,
    recursive: bool = True,
    chunk_size: int = 700,
    overlap: int = 120,
) -> list[dict]:
    """
    读取原始语料并切分为可检索片段。

    参数：
      data_dir: 原始语料目录。
      recursive: 是否递归读取子目录。
      chunk_size: 分块字符数。
      overlap: 分块重叠字符数。

    返回值：
      与 VectorStore.search 兼容的候选片段列表。
    """
    documents = load_text_files(data_dir, recursive=recursive)
    candidates: list[dict] = []

    for doc in documents:
        cleaned = clean_text(doc["text"])
        chunks = chunk_text(cleaned, chunk_size=chunk_size, overlap=overlap)
        fm_meta = doc.get("fm_meta", {})

        for idx, chunk in enumerate(chunks):
            candidates.append({
                "text": chunk["text"],
                "source": doc.get("source", "unknown"),
                "metadata": {
                    "source": doc.get("source", "unknown"),
                    "path": doc.get("path", ""),
                    "chunk_id": idx,
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "author": fm_meta.get("author"),
                    "year": fm_meta.get("year"),
                    "category": fm_meta.get("category", "raw_fallback"),
                    "language": fm_meta.get("language", "zh"),
                    "summary": fm_meta.get("summary", ""),
                    "retrieval": "raw_keyword_fallback",
                },
            })

    return candidates


def search_raw_corpus(
    query: str,
    top_k: int = 5,
    chunks: list[dict] | None = None,
    data_dir: Path | str = RAW_DIR,
) -> list[dict]:
    """
    使用关键词相关度检索原始语料片段，作为 Chroma 索引不可用时的兜底。

    参数：
      query: 查询字符串。
      top_k: 返回片段数量。
      chunks: 预加载片段列表；未传入时现场读取 data_dir。
      data_dir: 原始语料目录。

    返回值：
      与 VectorStore.search 输出结构兼容的片段列表。
    """
    terms = _extract_query_terms(query)
    if not terms:
        return []

    candidate_chunks = chunks if chunks is not None else load_raw_corpus_chunks(data_dir)
    scored: list[tuple[float, dict]] = []

    for item in candidate_chunks:
        raw_score = _score_chunk(
            query=query,
            terms=terms,
            text=item.get("text", ""),
            source=item.get("source", ""),
        )
        if raw_score <= 0:
            continue

        result = {
            "text": item.get("text", ""),
            "source": item.get("source", "unknown"),
            "metadata": dict(item.get("metadata", {})),
            "score": round(1 / (1 + raw_score), 4),
        }
        scored.append((raw_score, result))

    scored.sort(
        key=lambda pair: (
            -pair[0],
            pair[1]["source"],
            pair[1]["metadata"].get("chunk_id", 0),
        )
    )
    return [item for _, item in scored[:top_k]]
