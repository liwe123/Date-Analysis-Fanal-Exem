import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.embed_store import VectorStore
from src.qa import generate_answer
from src.query_parser import parse_query
from src.utils import get_logger, get_openai_client, init_env

init_env()
logger = get_logger("streamlit_app")

# ── 页面配置 ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="课程知识库 RAG 助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自定义样式 ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stMetric { background: #f0f2f6; padding: 0.5rem 1rem; border-radius: 8px; }
    .source-box {
        background: #f8f9fa; border-left: 3px solid #1f77b4;
        padding: 0.5rem 1rem; margin: 0.5rem 0; border-radius: 4px;
        font-size: 0.85rem; color: #333 !important;
    }
    [data-theme="dark"] .source-box {
        background: #2b2b2b; color: #e0e0e0 !important;
    }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── 标题区 ────────────────────────────────────────────────────────────────────

col_title, col_btn = st.columns([6, 1])
with col_title:
    st.title("📚 课程知识库 RAG 助手")
    st.caption("基于检索增强生成（RAG）的智能问答系统 · 计划二")
with col_btn:
    if st.button("🗑 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── 初始化会话状态 ────────────────────────────────────────────────────────────

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


# ── 侧边栏 ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙ 系统状态")

    try:
        store = get_cached_store()
        count = store.count()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 文档块数", count)
        with col2:
            sources = store.list_sources()
            st.metric("📄 来源数", len(sources))

        if sources:
            with st.expander(f"📋 文档来源列表 ({len(sources)})"):
                search_src = st.text_input("过滤来源", key="src_filter", placeholder="输入关键词...")
                filtered = [s for s in sources if search_src.lower() in s.lower()] if search_src else sources
                for src in filtered:
                    st.write(f"▪ {src}")

    except Exception as exc:
        st.error(f"⚠ 向量库初始化失败")
        st.caption(str(exc))

    st.divider()
    st.header("🔍 检索设置")

    top_k = st.slider("返回条数 (Top-K)", 1, 10, 3)
    show_debug = st.checkbox("🐛 调试模式", value=False)

    with st.expander("⚙ 高级设置"):
        st.caption("向量搜索距离上限（0=最相似，2=相反）")
        max_dist = st.slider(
            "max_distance", 0.1, 2.0, 2.0, 0.05,
            help="只返回余弦距离不超过此值的结果。值越小结果越精准。",
        )
        max_dist = None if max_dist >= 2.0 else max_dist

    st.divider()
    st.caption("💡 提示：可直接在对话框中输入问题，或拖动上方滑块调整检索参数。")

# ── 欢迎区域 ──────────────────────────────────────────────────────────────────

if not st.session_state.messages:
    st.info(
        "👋 **欢迎使用课程知识库 RAG 助手！**\n\n"
        "你可以问我关于课程文档、知识点、考试要求等任何问题。\n\n"
        "**示例问题：**\n"
        "- 课程项目的最终提交要求是什么？\n"
        "- 什么是检索增强生成（RAG）？\n"
        "- 向量数据库和传统数据库有什么区别？",
    )

# ── 显示历史消息 ──────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 输入处理 ──────────────────────────────────────────────────────────────────

question = st.chat_input("在这里输入你的问题...", accept_file=False)

if question:
    # ── 输入校验 ──────────────────────────────────────────────────────────────
    question = question.strip()
    if not question:
        st.stop()

    # 检测并拦截非文本内容（图片路径、Base64 等）
    if any(question.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff")):
        st.error("❌ 不支持图片输入。请输入文字问题，或描述你想了解的图像内容。")
        st.stop()

    if question.startswith("data:image") or "![image]" in question.lower():
        st.error("❌ 检测到图片内容。本助手仅支持文字提问，请用文字描述你的问题。")
        st.stop()

    if "image.png" in question or "image.jpg" in question or "clipboard" in question.lower():
        st.error("❌ 检测到粘贴的图片。本助手仅支持文字提问，请用文字描述你的问题。")
        st.stop()

    # ── 显示用户消息 ──────────────────────────────────────────────────────────
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # ── 生成回答 ──────────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        try:
            client = get_cached_client()
            store = get_cached_store()

            with st.spinner("🧠 正在分析问题意图..."):
                parsed = parse_query(question, client=client)

            search_query = parsed.get("search_query", question)
            filters = parsed.get("filters")

            if show_debug:
                st.info(f"**核心搜索词**: `{search_query}`")
                if filters:
                    st.info(f"**元数据过滤**: `{filters}`")

            with st.spinner("📖 正在检索相关文档..."):
                results = store.search(search_query, top_k=top_k, where=filters, max_distance=max_dist)

            if not results:
                warning_msg = (
                    "😕 未检索到相关内容。\n\n"
                    "**可能的原因：**\n"
                    "- 知识库中暂无相关文档资料\n"
                    "- 搜索关键词与文档内容不匹配\n"
                    "- 距离过滤条件过严（可在侧边栏放宽 `max_distance`）\n\n"
                    "请尝试换个问法，或使用更通用的关键词。"
                )
                st.warning(warning_msg)
                st.session_state.messages.append({"role": "assistant", "content": warning_msg})
                st.stop()

            with st.spinner("✍ 正在生成回答..."):
                answer = generate_answer(question, results, client=client)

            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

            # ── 检索来源 ──────────────────────────────────────────────────────
            with st.expander(f"📎 检索来源 ({len(results)} 条)"):
                for idx, item in enumerate(results, 1):
                    score = item.get("score")
                    if score is not None:
                        distance = f"{score:.4f}"
                        # 余弦距离转为相似度百分比显示
                        similarity = max(0, (1 - score / 2)) * 100
                        badge = f"distance={distance}  |  相似度≈{similarity:.0f}%"
                    else:
                        badge = "distance=N/A"

                    st.markdown(f"**{idx}. {item['source']}**")
                    st.caption(badge)
                    if item.get("metadata", {}).get("path"):
                        st.caption(f"📁 `{item['metadata']['path']}`")

                    snippet = item["text"].replace("\n", " ")[:400]
                    if len(item["text"]) > 400:
                        snippet += "..."
                    st.markdown(f'<div class="source-box">{snippet}</div>', unsafe_allow_html=True)

        except Exception as exc:
            err_str = str(exc)

            # 区分不同类型的错误
            if "image" in err_str.lower() or "image_url" in err_str.lower():
                error_msg = (
                    "❌ **图片不被支持**\n\n"
                    "当前模型仅接受文字输入，请勿在问题中包含图片或文件路径。"
                )
            elif "api" in err_str.lower() or "key" in err_str.lower():
                error_msg = (
                    "⚠ **API 配置问题**\n\n"
                    "请检查 `.env` 文件中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否正确。"
                )
            elif "rate" in err_str.lower() or "limit" in err_str.lower():
                error_msg = (
                    "⏳ **请求频率过高**\n\n"
                    "API 达到速率限制，请稍后再试。"
                )
            else:
                error_msg = f"⚠ **出错了**\n\n```\n{err_str[:500]}\n```"

            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
