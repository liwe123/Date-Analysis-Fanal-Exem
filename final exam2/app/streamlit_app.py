"""
streamlit_app.py
================
Streamlit Web 界面入口。
"""

from __future__ import annotations

import html
import os
import sys
import time
from pathlib import Path

import streamlit as st
from openai import OpenAI

# 动态添加路径以防导入失败
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.embed_store import VectorStore
from src.preprocess import process_documents
from src.qa import generate_answer
from src.query_parser import parse_query
from src.utils import get_logger, get_openai_client, init_env

# 防止在每次 Streamlit 重载时重复加载环境变量
if "env_initialized" not in st.session_state:
    init_env()
    st.session_state.env_initialized = True

logger = get_logger("streamlit_app")

st.set_page_config(
    page_title="课程知识库 RAG 助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ─────────────────────────────────────────────────────────────────

@st.cache_data
def load_css() -> str:
    """读取并缓存 CSS 样式文件，避免重复磁盘 I/O。"""
    with open(Path(__file__).parent / "style.css", encoding="utf-8") as f:
        return f.read()


st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)

# ── Title ────────────────────────────────────────────────────────────────────

col_title, col_btn = st.columns([5, 1])
with col_title:
    st.markdown(
        '<div class="header-container">'
        '<div class="header-inner">'
        '<div class="header-icon">📚</div>'
        '<div class="header-text-group">'
        '<div class="header-title">'
        '<span class="header-title-gradient">课程知识库 RAG 助手</span>'
        '</div>'
        '<div class="header-subtitle">基于检索增强生成（RAG）的智能问答系统 · 计划二</div>'
        '</div></div></div>',
        unsafe_allow_html=True,
    )
with col_btn:
    st.markdown('<div class="clear-btn-wrapper">', unsafe_allow_html=True)
    if st.button("🗑 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []


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


@st.cache_data(ttl=30)
def get_store_stats() -> tuple[int, list[str]]:
    """缓存知识库统计数据以提升响应性能，在更新数据时会主动清除。"""
    store = get_cached_store()
    return store.count(), store.list_sources()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-icon">📚</div>'
        '<div class="sidebar-brand-title">RAG 知识库</div>'
        '<div class="sidebar-brand-sub">智能问答系统</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">📊 系统状态</div>', unsafe_allow_html=True)

    try:
        count, sources = get_store_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("文档块数", count)
        with col2:
            st.metric("来源数", len(sources))

        if sources:
            with st.expander(f"📋 文档来源列表（{len(sources)}）"):
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
                    st.markdown(f"▪ {html.escape(src)}")

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        st.error("⚠ 向量库初始化失败")
        st.caption(html.escape(str(exc)))
        logger.warning("向量库初始化失败: %s", exc)

    st.markdown('<div class="sidebar-section-title">➕ 数据管理</div>', unsafe_allow_html=True)
    
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
                time.sleep(1)
                st.rerun()

    st.markdown('<div class="sidebar-section-title">🔍 检索设置</div>', unsafe_allow_html=True)

    top_k = st.slider("返回条数（Top-K）", 1, 10, 3, help="从知识库中检索最相关的前 K 条文档片段")
    show_debug = st.checkbox("🐛 调试模式", value=False, help="显示搜索关键词和过滤条件")

    with st.expander("⚙ 高级设置"):
        st.caption("向量搜索距离上限（0=最相似，2=相反）")
        max_dist = st.slider("max_distance", 0.1, 2.0, 2.0, 0.05, help="只返回余弦距离不超过此值的结果。值越小结果越精准。")
        max_dist = None if max_dist >= 2.0 else max_dist

    st.divider()
    st.caption("💡 可直接在下方输入问题，或调整左侧检索参数优化结果。")

# ── Welcome ───────────────────────────────────────────────────────────────────

if not st.session_state.messages:
    st.markdown(
        '<div class="welcome-container">'
        '<div class="welcome-icon">📚</div>'
        '<div class="welcome-title">欢迎使用课程知识库 RAG 助手</div>'
        '<div class="welcome-desc">'
        "我可以帮你解答关于课程文档、知识点、考试要求等任何问题。"
        "基于先进的检索增强生成技术，为你提供准确、有据可查的回答。"
        "</div>"
        '<div class="welcome-examples">'
        '<span class="welcome-example-item">课程项目的最终提交要求是什么？</span>'
        '<span class="welcome-example-item">什么是检索增强生成（RAG）？</span>'
        '<span class="welcome-example-item">向量数据库和传统数据库有什么区别？</span>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Chat history ──────────────────────────────────────────────────────────────

st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="message-user"><div class="bubble">{html.escape(msg["content"])}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f'{msg["content"]}'
            "</div></div></div>",
            unsafe_allow_html=True,
        )

st.markdown("</div>", unsafe_allow_html=True)

# ── Chat input ────────────────────────────────────────────────────────────────

question = st.chat_input("在这里输入你的问题...", accept_file=False)

if question:
    question = question.strip()
    if not question:
        st.stop()

    if any(question.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff")):
        st.error("❌ 不支持图片输入。请输入文字问题，或描述你想了解的图像内容。")
        st.stop()

    if question.startswith("data:image") or "![image]" in question.lower():
        st.error("❌ 检测到图片内容。本助手仅支持文字提问，请用文字描述你的问题。")
        st.stop()

    if "image.png" in question or "image.jpg" in question or "clipboard" in question.lower():
        st.error("❌ 检测到粘贴的图片。本助手仅支持文字提问，请用文字描述你的问题。")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": question})
    st.markdown(
        f'<div class="message-user"><div class="bubble">{html.escape(question)}</div></div>',
        unsafe_allow_html=True,
    )

    msg_placeholder = st.empty()

    with msg_placeholder.container():
        st.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
            '<div class="bubble-wrapper">'
            '<div class="bubble">'
            '<div class="typing-indicator">'
            '<span class="dot"></span><span class="dot"></span><span class="dot"></span>'
            "</div></div></div></div>",
            unsafe_allow_html=True,
        )

    try:
        client = get_cached_client()
        store = get_cached_store()

        with st.spinner("🧠 正在分析问题意图..."):
            parsed = parse_query(question, client=client)

        search_query = parsed.get("search_query", question)
        filters = parsed.get("filters")

        if show_debug:
            escaped_query = html.escape(search_query)
            escaped_filters = html.escape(str(filters))
            debug_html = f"<div class=\"debug-box\"><strong>🔍 核心搜索词：</strong><code>{escaped_query}</code>"
            if filters:
                debug_html += f"<br><strong>🏷 元数据过滤：</strong><code>{escaped_filters}</code>"
            debug_html += "</div>"
            msg_placeholder.markdown(
                '<div class="message-assistant">'
                '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
                '<div class="bubble-wrapper"><div class="bubble">'
                f"{debug_html}"
                "</div></div></div>",
                unsafe_allow_html=True,
            )

        with st.spinner("📖 正在检索相关文档..."):
            results = store.search(search_query, top_k=top_k, where=filters, max_distance=max_dist)

        if not results:
            warning_msg = (
                "😕 **未检索到相关内容**\n\n"
                "**可能的原因：**\n"
                "- 知识库中暂无相关文档资料\n"
                "- 搜索关键词与文档内容不匹配\n"
                "- 距离过滤条件过严（可在侧边栏放宽 `max_distance`）\n\n"
                "请尝试换个问法，或使用更通用的关键词。"
            )
            msg_placeholder.markdown(
                '<div class="message-assistant">'
                '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
                '<div class="bubble-wrapper"><div class="bubble">'
                f"{warning_msg}"
                "</div></div></div>",
                unsafe_allow_html=True,
            )
            st.session_state.messages.append({"role": "assistant", "content": warning_msg})
            st.stop()

        with st.spinner("✍ 正在生成回答..."):
            answer = generate_answer(question, results, client=client)

        source_items = ""
        for idx, item in enumerate(results, 1):
            score = item.get("score")
            if score is not None:
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
                    '<span class="path-text">📁 '
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

        full_answer = (
            answer
            + '<div class="source-section"><details>'
            + f"<summary>📎 检索来源（{len(results)} 条）</summary>"
            + source_items
            + "</details></div>"
        )

        msg_placeholder.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{full_answer}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )

        st.session_state.messages.append({"role": "assistant", "content": answer})

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        err_str = str(exc)

        if "image" in err_str.lower() or "image_url" in err_str.lower():
            error_msg = "❌ **图片不被支持**\n\n当前模型仅接受文字输入，请勿在问题中包含图片或文件路径。"
        elif "api" in err_str.lower() or "key" in err_str.lower():
            error_msg = "⚠ **API 配置问题**\n\n请检查 `.env` 文件中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否正确。"
        elif "rate" in err_str.lower() or "limit" in err_str.lower():
            error_msg = "⏳ **请求频率过高**\n\nAPI 达到速率限制，请稍后再试。"
        else:
            error_msg = f"⚠ **出错了**\n\n```\n{html.escape(err_str[:500])}\n```"

        msg_placeholder.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{error_msg}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": error_msg})

