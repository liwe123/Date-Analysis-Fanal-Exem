"""
qa.py
=====
问答生成模块。
"""

from __future__ import annotations

from openai import OpenAI

from src.utils import get_logger, get_model_name, get_openai_client

logger = get_logger("qa")


def _format_sources_list(retrieved_docs: list[dict]) -> str:
    """格式化并去重返回检索来源列表。"""
    sources_set = set()
    for doc in retrieved_docs:
        source = doc.get("source", "unknown")
        sources_set.add(source)
    if sources_set:
        return "\n".join(f"- {src}" for src in sorted(sources_set))
    return "- N/A"


def generate_answer(
    question: str,
    retrieved_docs: list[dict],
    client: OpenAI | None = None,
    chat_history: list[dict] | None = None,
) -> str:
    """
    基于检索到的文档片段以及可选的历史会话生成问题的回答。

    参数：
      question: 自然语言问题。
      retrieved_docs: 检索到的相关文档片段列表。
      client: 可选的 OpenAI 客户端实例。
      chat_history: 可选的历史会话列表（按时间正序排列）。

    返回值：
      生成的回答文本。
    """
    if not retrieved_docs:
        return "未找到相关文档，无法回答。"

    context_blocks = []
    for doc in retrieved_docs:
        meta = doc.get("metadata", {})
        source = meta.get("source", doc.get("source", "unknown"))
        year = meta.get("year")
        year_str = f" ({year})" if year else ""
        block = f"[来源: {source}{year_str}]\n{doc['text']}"
        context_blocks.append(block)

    context_text = "\n\n".join(context_blocks)
    
    # 🔴 性能/安全：硬性截断长上下文，防御超大 Token 消费或 API 报错
    if len(context_text) > 8000:
        logger.warning("参考资料内容过长（%d 字符），已进行自动截断处理。", len(context_text))
        context_text = context_text[:8000] + "\n...[参考资料过长，已被系统截断]..."

    system_prompt = (
        "你是一个专业的问答助手。\n"
        "仅基于提供的参考资料回答问题。\n"
        "在回答中引用来源，格式为 [来源: 名称]。"
    )

    user_prompt = f"参考资料:\n{context_text}\n\n问题:\n{question}"

    # 组装消息列表
    messages = [{"role": "system", "content": system_prompt}]
    
    # 🔴 关键：安全截断，至多保留最近 10 条历史会话消息
    if chat_history:
        trimmed_history = chat_history[-10:]
        for msg in trimmed_history:
            if msg.get("role") and msg.get("content"):
                # 排除当前提问避免重复
                if msg["role"] == "user" and msg["content"] == question:
                    continue
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_prompt})

    if client is None:
        client = get_openai_client()
    model = get_model_name()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content or ""

        if "[来源:" not in answer:
            answer += f"\n\n来源:\n{_format_sources_list(retrieved_docs)}"

        return answer

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.error("LLM 答案生成失败: %s", repr(exc))
        raise RuntimeError(f"答案生成失败: {exc}") from exc

