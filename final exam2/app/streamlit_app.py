import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 必须在导入 src 模块前初始化环境变量（尤其是 HF_ENDPOINT）
from src.utils import init_env
init_env()
# 兜底：如果 utils 未设置 HF_ENDPOINT，则使用镜像
if not os.environ.get("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import streamlit as st
from src.embed_store import VectorStore
from src.qa import generate_answer
from src.query_parser import parse_query
from src.utils import get_logger, get_openai_client
logger = get_logger("streamlit_app")

st.set_page_config(
    page_title="课程知识库 RAG 助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ─────────────────────────────────────────────────────────────────
with open(Path(__file__).parent / "style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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


def get_cached_client():
    if "openai_client" not in st.session_state:
        st.session_state.openai_client = get_openai_client()
    return st.session_state.openai_client


def get_cached_store():
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = VectorStore()
    return st.session_state.vector_store


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
        store = get_cached_store()
        count = store.count()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("文档块数", count)
        with col2:
            sources = store.list_sources()
            st.metric("来源数", len(sources))

        if sources:
            with st.expander(f"📋 文档来源列表（{len(sources)}）"):
                search_src = st.text_input("", key="src_filter", placeholder="输入关键词过滤...", label_visibility="collapsed")
                filtered = [s for s in sources if search_src.lower() in s.lower()] if search_src else sources
                for src in filtered:
                    st.markdown(f"▪ {src}")

    except Exception as exc:
        st.error("⚠ 向量库初始化失败")
        st.caption(str(exc))

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
            f'<div class="message-user"><div class="bubble">{msg["content"]}</div></div>',
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
        f'<div class="message-user"><div class="bubble">{question}</div></div>',
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
            debug_html = f"<div class=\"debug-box\"><strong>🔍 核心搜索词：</strong><code>{search_query}</code>"
            if filters:
                debug_html += f"<br><strong>🏷 元数据过滤：</strong><code>{filters}</code>"
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

            snippet = item["text"].replace("\n", " ")[:400]
            if len(item["text"]) > 400:
                snippet += "..."

            path_html = ""
            if item.get("metadata", {}).get("path"):
                path_html = (
                    '<span class="path-text">📁 '
                    + item["metadata"]["path"]
                    + "</span>"
                )

            source_items += (
                '<div class="source-card">'
                '<div class="source-card-header">'
                f'<span class="source-card-num">{idx}</span>'
                f'<span class="source-card-title">{item["source"]}</span>'
                "</div>"
                '<div class="source-card-meta">'
                f'<span class="meta-badge">{badge}</span>'
                f"{path_html}</div>"
                f'<div class="source-card-snippet">{snippet}</div>'
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
        err_str = str(exc)

        if "image" in err_str.lower() or "image_url" in err_str.lower():
            error_msg = "❌ **图片不被支持**\n\n当前模型仅接受文字输入，请勿在问题中包含图片或文件路径。"
        elif "api" in err_str.lower() or "key" in err_str.lower():
            error_msg = "⚠ **API 配置问题**\n\n请检查 `.env` 文件中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否正确。"
        elif "rate" in err_str.lower() or "limit" in err_str.lower():
            error_msg = "⏳ **请求频率过高**\n\nAPI 达到速率限制，请稍后再试。"
        else:
            error_msg = f"⚠ **出错了**\n\n```\n{err_str[:500]}\n```"

        msg_placeholder.markdown(
            '<div class="message-assistant">'
            '<div class="avatar-wrapper"><div class="avatar">🤖</div></div>'
            '<div class="bubble-wrapper"><div class="bubble">'
            f"{error_msg}"
            "</div></div></div>",
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
