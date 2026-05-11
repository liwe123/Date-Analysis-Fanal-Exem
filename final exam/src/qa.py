# -*- coding: utf-8 -*-
"""
qa.py
=====
问答生成模块。
"""

from __future__ import annotations

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


def generate_answer(question: str, retrieved_docs: list[dict], client=None) -> str:
    if not retrieved_docs:
        return "No relevant documents found. Unable to answer."

    context_blocks = []
    for doc in retrieved_docs:
        meta = doc.get("metadata", {})
        source = meta.get("source", doc.get("source", "unknown"))
        year = meta.get("year")
        year_str = f" ({year})" if year else ""
        block = f"[Source: {source}{year_str}]\n{doc['text']}"
        context_blocks.append(block)

    context_text = "\n\n".join(context_blocks)

    system_prompt = (
        "You are a professional Q&A assistant.\n"
        "Answer based only on the provided reference materials.\n"
        "Cite sources inline as [Source: name]."
    )

    user_prompt = f"References:\n{context_text}\n\nQuestion:\n{question}"

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

        if "[Source:" not in answer:
            answer += f"\n\nSources:\n{_format_sources_list(retrieved_docs)}"

        return answer

    except Exception as exc:
        logger.error("LLM answer generation failed: %s", repr(exc))
        raise RuntimeError(f"Answer generation failed: {exc}") from exc
