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
    sources_set = set()
    for doc in retrieved_docs:
        source = doc.get("source", "unknown")
        sources_set.add(source)
    if sources_set:
        return "\n".join(f"- {src}" for src in sorted(sources_set))
    return "- N/A"


def generate_answer(question: str, retrieved_docs: list[dict], client: OpenAI | None = None) -> str:
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

    system_prompt = (
        "你是一个专业的问答助手。\n"
        "仅基于提供的参考资料回答问题。\n"
        "在回答中引用来源，格式为 [来源: 名称]。"
    )

    user_prompt = f"参考资料:\n{context_text}\n\n问题:\n{question}"

    if client is None:
        client = get_openai_client()
    model = get_model_name()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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
