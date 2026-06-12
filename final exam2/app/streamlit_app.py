"""
streamlit_app.py
================
Streamlit Web 界面入口。
"""

from __future__ import annotations

import html
import sys
import time
from pathlib import Path

import streamlit as st
from openai import OpenAI

# 动态添加路径以防导入失败
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rendering import safe_text_to_html
from app.retrieval_fallback import (
    load_raw_corpus_chunks,
    search_chroma_sqlite,
    search_raw_corpus,
)
from src.embed_store import VectorStore
from src.preprocess import process_documents
from src.qa import generate_answer
from src.query_parser import parse_query
from src.utils import get_embedding_model_name, get_logger, get_openai_client, init_env

EXAMPLE_QUESTIONS = (
    "课程项目的最终提交要求是什么？",
    "什么是检索增强生成（RAG）？",
    "向量数据库和传统数据库有什么区别？",
)
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff")
STYLE_PATH = Path(__file__).parent / "style.css"

# 防止在每次 Streamlit 重载时重复加载环境变量
if "env_initialized" not in st.session_state:
    init_env()
    st.session_state.env_initialized = True

logger = get_logger("streamlit_app")

st.set_page_config(
    page_title="课程知识库 RAG 助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── Load CSS ─────────────────────────────────────────────────────────────────

@st.cache_data
def load_css(style_mtime: float) -> str:
    """读取并缓存 CSS 样式文件，避免重复磁盘 I/O。"""
    with STYLE_PATH.open(encoding="utf-8") as f:
        return f.read()


st.markdown(f"<style>{load_css(STYLE_PATH.stat().st_mtime)}</style>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "store_stats" not in st.session_state:
    st.session_state.store_stats = None

# ── Top actions ───────────────────────────────────────────────────────────────

if st.session_state.messages:
    st.markdown('<div class="clear-btn-wrapper">', unsafe_allow_html=True)
    if st.button("清空对话"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def get_cached_client() -> OpenAI:
    """缓存 OpenAI 客户端单例。"""
    if "openai_client" not in st.session_state:
        st.session_state.openai_client = get_openai_client()
    return st.session_state.openai_client


def get_cached_store() -> VectorStore:
    """缓存向量数据库单例。"""
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = VectorStore()
    return st.session_state.vector_store


@st.cache_data(ttl=3600, show_spinner=False)
def get_store_stats() -> tuple[int, list[str]]:
    """缓存知识库统计数据以提升响应性能，在更新数据时会主动清除。"""
    store = get_cached_store()
    return store.count(), store.list_sources()


@st.cache_data(ttl=3600, show_spinner=False)
def get_raw_fallback_chunks() -> list[dict]:
    """缓存原始语料兜底检索片段。"""
    return load_raw_corpus_chunks()


def _validate_question(raw_question: str) -> tuple[str | None, str | None]:
    """校验用户输入，返回规范化问题与错误提示。"""
    candidate_question = raw_question.strip()
    lower_question = candidate_question.lower()

    if not candidate_question:
        return None, "请输入文字问题。"
    if any(lower_question.endswith(ext) for ext in IMAGE_SUFFIXES):
        return None, "不支持图片输入。请输入文字问题，或描述你想了解的图像内容。"
    if candidate_question.startswith("data:image") or "![image]" in lower_question:
        return None, "检测到图片内容。本助手仅支持文字提问，请用文字描述你的问题。"
    if (
        "image.png" in lower_question
        or "image.jpg" in lower_question
        or "clipboard" in lower_question
    ):
        return None, "检测到粘贴的图片。本助手仅支持文字提问，请用文字描述你的问题。"
    return candidate_question, None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-icon">RAG</div>'
        '<div class="sidebar-brand-title">课程 RAG</div>'
        '<div class="sidebar-brand-sub">证据面板</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">系统状态</div>', unsafe_allow_html=True)

    try:
        if st.button("加载 / 刷新知识库状态", key="refresh_store_stats", use_container_width=True):
            st.session_state.store_stats = get_store_stats()

        if st.session_state.store_stats is None:
            st.caption("百万级向量库统计按需加载，避免打开页面或输入问题时卡顿闪烁。")
        else:
            count, sources = st.session_state.store_stats

            # 处理超大数量时的显示逻辑
            real_sources = [s for s in sources if not s.startswith("...")]
            display_sources_count = len(real_sources)
            sources_metric_val = f"{display_sources_count}+" if count > 10000 else str(display_sources_count)
            expander_title = f"文档来源列表（{sources_metric_val}）"

            col1, col2 = st.columns(2)
            with col1:
                st.metric("文档块数", count)
            with col2:
                st.metric("来源数", sources_metric_val)

            if sources:
                with st.expander(expander_title):
                    search_src = st.text_input(
                        "来源过滤",
                        key="src_filter",
                        placeholder="输入关键词过滤...",
                        label_visibility="collapsed",
                    )
                    filtered = (
                        [s for s in sources if search_src.lower() in s.lower()]
                        if search_src
                        else sources
                    )
                    for src in filtered:
                        st.markdown(f"· {html.escape(src)}")

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        st.error("向量索引暂不可用")
        st.caption("仍可直接提问，系统会先切换到 Chroma SQLite 关键词检索，再使用原始语料兜底。")
        st.caption(html.escape(str(exc)))
        logger.warning("向量库初始化失败: %s", exc)

    st.markdown('<div class="sidebar-section-title">数据写入</div>', unsafe_allow_html=True)
    
    custom_data_title = st.text_input("数据标题", placeholder="例如：最新课程通知", key="custom_title")
    custom_data_text = st.text_area("数据内容", height=150, placeholder="粘贴文本内容...", key="custom_text")
    if st.button("添加到知识库", use_container_width=True):
        if not custom_data_text.strip():
            st.error("内容不能为空")
        else:
            with st.spinner("正在处理并加入向量库..."):
                source_name = f"custom_{int(time.time())}.txt"
                if custom_data_title.strip():
                    # 过滤非法文件名字符
                    safe_title = "".join(
                        c for c in custom_data_title.strip()
                        if c.isalnum() or c in (" ", "_", "-")
                    ).replace(" ", "_")
                    source_name = f"{safe_title}_{int(time.time())}.txt"
                    
                doc = {
                    "source": source_name,
                    "path": "custom_input",
                    "text": custom_data_text,
                    "fm_meta": {},
                }
                processed = process_documents([doc])
                store = get_cached_store()
                store.add_documents(processed)
                st.success("添加成功！")
                get_store_stats.clear()  # 清除缓存以便侧边栏立即更新状态
                st.session_state.store_stats = None
                time.sleep(1)
                st.rerun()

    st.markdown('<div class="sidebar-section-title">检索设置</div>', unsafe_allow_html=True)

    top_k = st.slider("返回条数（Top-K）", 1, 10, 3, help="从知识库中检索最相关的前 K 条文档片段")
    show_debug = st.checkbox("显示调试信息", value=False, help="显示搜索关键词和过滤条件")

    with st.expander("高级设置"):
        st.caption("向量搜索距离上限（0=最相似，2=相反）")
        max_dist = st.slider("max_distance", 0.1, 2.0, 2.0, 0.05, help="只返回余弦距离不超过此值的结果。值越小结果越精准。")
        max_dist = None if max_dist >= 2.0 else max_dist

    st.divider()
    st.caption("输入问题后，系统会先解析意图，再检索片段并生成回答。")

# ── Chat input ────────────────────────────────────────────────────────────────

pending_question = None
input_error = None
submitted_question = st.chat_input("在这里输入你的问题...", accept_file=False)

if submitted_question:
    pending_question, input_error = _validate_question(submitted_question)
    if pending_question:
        st.session_state.messages.append({"role": "user", "content": pending_question})

if input_error:
    st.error(input_error)

# ── Welcome ───────────────────────────────────────────────────────────────────

if not st.session_state.messages:
    st.markdown(
        '<div class="welcome-container">'
        '<div class="welcome-kicker">COURSE RAG</div>'
        '<div class="welcome-title">课程知识库 RAG 助手</div>'
        '<div class="welcome-desc">'
        "从课程资料里找答案。选择一个常见问题，或直接输入你想查证的课程、项目、知识点问题。"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    example_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for idx, example_question in enumerate(EXAMPLE_QUESTIONS):
        with example_cols[idx]:
            if st.button(example_question, key=f"example_question_{idx}", use_container_width=True):
                pending_question = example_question
                st.session_state.messages.append({"role": "user", "content": pending_question})

# ── Chat history ──────────────────────────────────────────────────────────────

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="message-user"><div class="bubble">{html.escape(msg["content"])}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        safe_content = safe_text_to_html(msg["content"])
        st.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">AI</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{safe_content}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

if pending_question:
    question = pending_question

    # ── 使用 st.status 展示实时思考过程（原生组件，即刻渲染，不白屏） ──
    answer = None
    results = None
    error_msg = None

    try:
        with st.status("正在思考...", expanded=True) as thinking:
            client = get_cached_client()
            embedding_mode = get_embedding_model_name().lower()
            active_retrieval_mode = "sqlite_primary"

            # ── 步骤 1：意图解析 ──
            st.write("01 / 正在分析问题意图并提取关键词...")
            parsed = parse_query(question, client=client)
            search_query = parsed.get("search_query", question)
            filters = parsed.get("filters")

            st.write(f"核心搜索词：`{search_query}`")
            if filters:
                st.write(f"元数据过滤：`{filters}`")
            if show_debug:
                st.write(f"原始解析结果：`{parsed}`")

            # ── 步骤 2：文档检索 ──
            thinking.update(label="正在检索相关文档...", expanded=True)
            st.write("02 / 正在从知识库中检索最匹配的文档片段...")

            if embedding_mode == "remote":
                try:
                    store = get_cached_store()
                    results = store.search(
                        search_query,
                        top_k=top_k,
                        where=filters,
                        max_distance=max_dist,
                    )
                    active_retrieval_mode = "vector"
                    st.write("检索路径：百万行 ChromaDB HNSW 向量索引。")
                except Exception as search_exc:
                    if isinstance(search_exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    logger.warning("向量检索失败，切换 Chroma SQLite 检索: %s", search_exc)
                    st.write("向量索引暂不可用，已切换到百万行 Chroma SQLite 正文索引。")
                    results = search_chroma_sqlite(search_query, top_k=top_k)
                    active_retrieval_mode = "sqlite_primary"
            else:
                st.write(
                    "当前为 local embedding，云显卡不可用时不加载本地大模型，"
                    "直接使用百万行 Chroma SQLite 正文索引。"
                )
                results = search_chroma_sqlite(search_query, top_k=top_k)

            if not results:
                st.write("Chroma SQLite 未召回内容，继续使用原始语料关键词检索。")
                fallback_chunks = get_raw_fallback_chunks()
                results = search_raw_corpus(
                    search_query,
                    top_k=top_k,
                    chunks=fallback_chunks,
                )
                active_retrieval_mode = "raw_fallback"

            if not results:
                raise RuntimeError(
                    "Chroma SQLite 与原始语料兜底均未召回内容。"
                    "请检查 vector_store/chroma.sqlite3 或 data/raw。"
                )

            if not results:
                thinking.update(label="未检索到相关内容", state="error", expanded=True)
                st.write("未召回任何匹配片段，请尝试换个问法或放宽 max_distance。")
                warning_msg = (
                    "**未检索到相关内容**\n\n"
                    "**可能的原因：**\n"
                    "- 知识库中暂无相关文档资料\n"
                    "- 搜索关键词与文档内容不匹配\n"
                    "- 距离过滤条件过严（可在侧边栏放宽 `max_distance`）\n\n"
                    "请尝试换个问法，或使用更通用的关键词。"
                )
                st.session_state.messages.append({"role": "assistant", "content": warning_msg})
                st.stop()

            st.write(f"成功召回 **{len(results)}** 个相关文档片段")
            if show_debug:
                mode_label = {
                    "vector": "百万行 ChromaDB HNSW 向量索引",
                    "sqlite_primary": "百万行 Chroma SQLite 正文索引",
                    "raw_fallback": "原始语料关键词兜底",
                }.get(active_retrieval_mode, active_retrieval_mode)
                st.write(f"实际检索模式：`{mode_label}`")
            for i, r in enumerate(results, 1):
                score = r.get("score")
                sim = max(0, (1 - score / 2)) * 100 if score is not None else 0
                st.write(f"　{i}. `{r['source']}` — 相似度 ≈{sim:.0f}%")

            # ── 步骤 3：答案生成 ──
            thinking.update(label="正在生成回答...", expanded=True)
            st.write("03 / 正在基于检索到的资料生成精准回答...")
            answer = generate_answer(question, results, client=client)
            st.write("回答生成完毕")

            thinking.update(label="思考完成", state="complete", expanded=False)

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        err_str = str(exc)
        if "image" in err_str.lower() or "image_url" in err_str.lower():
            error_msg = "**图片不被支持**\n\n当前模型仅接受文字输入，请勿在问题中包含图片或文件路径。"
        elif "api" in err_str.lower() or "key" in err_str.lower():
            error_msg = "**API 配置问题**\n\n请检查 `.env` 文件中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否正确。"
        elif "rate" in err_str.lower() or "limit" in err_str.lower():
            error_msg = "**请求频率过高**\n\nAPI 达到速率限制，请稍后再试。"
        else:
            error_msg = f"**出错了**\n\n```\n{html.escape(err_str[:500])}\n```"

    # ── 渲染最终回答气泡（或错误信息） ──
    if answer and results:
        source_items = ""
        retrieval_types = {
            item.get("metadata", {}).get("retrieval")
            for item in results
            if item.get("metadata", {}).get("retrieval")
        }
        if retrieval_types == {"chroma_sqlite_keyword_fallback"}:
            retrieval_summary = "百万行 SQLite 正文索引"
        elif retrieval_types == {"raw_keyword_fallback"}:
            retrieval_summary = "原始语料关键词兜底"
        else:
            retrieval_summary = "百万行 ChromaDB HNSW 向量索引"

        for idx, item in enumerate(results, 1):
            score = item.get("score")
            retrieval_mode = item.get("metadata", {}).get("retrieval")
            if retrieval_mode == "raw_keyword_fallback":
                similarity = max(0, (1 - (score or 0))) * 100
                badge = f"关键词兜底  |  相关度≈{similarity:.0f}%"
            elif retrieval_mode == "chroma_sqlite_keyword_fallback":
                similarity = max(0, (1 - (score or 0))) * 100
                badge = f"百万行SQLite正文索引  |  相关度≈{similarity:.0f}%"
            elif score is not None:
                distance = f"{score:.4f}"
                similarity = max(0, (1 - score / 2)) * 100
                badge = f"distance={distance}  |  相似度≈{similarity:.0f}%"
            else:
                badge = "distance=N/A"

            escaped_snippet = html.escape(item["text"].replace("\n", " ")[:400])
            if len(item["text"]) > 400:
                escaped_snippet += "..."

            path_html = ""
            if item.get("metadata", {}).get("path"):
                escaped_path = html.escape(item["metadata"]["path"])
                path_html = (
                    '<span class="path-text">'
                    + escaped_path
                    + "</span>"
                )

            escaped_source = html.escape(item["source"])
            source_items += (
                '<div class="source-card">'
                '<div class="source-card-header">'
                f'<span class="source-card-num">{idx}</span>'
                f'<span class="source-card-title">{escaped_source}</span>'
                "</div>"
                '<div class="source-card-meta">'
                f'<span class="meta-badge">{badge}</span>'
                f"{path_html}</div>"
                f'<div class="source-card-snippet">{escaped_snippet}</div>'
                "</div>"
            )

        safe_answer = safe_text_to_html(answer)
        full_answer = (
            safe_answer
            + '<div class="source-section">'
            + f'<div class="retrieval-path">检索路径：{retrieval_summary}</div>'
            + "<details>"
            + f"<summary>检索来源（{len(results)} 条）</summary>"
            + source_items
            + "</details></div>"
        )

        st.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">AI</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{full_answer}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": answer})

    elif error_msg:
        safe_error = safe_text_to_html(error_msg)
        st.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">AI</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{safe_error}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": error_msg})

