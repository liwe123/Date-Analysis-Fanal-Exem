"""
query_parser.py
===============
混合搜索查询解析模块。

功能：
  - 使用 LLM 将用户的自然语言问题解析为：
      1. 纯语义搜索查询（语义向量搜索用）
      2. 元数据过滤条件（SQL 风格，例如 year=2026, category=notice）
  - 支持中英文问题
  - 解析失败时安全降级为纯向量搜索
"""

from __future__ import annotations

import json
import re

from openai import OpenAI

from src.utils import get_logger, get_model_name, get_openai_client

logger = get_logger("query_parser")


_PARSER_SYSTEM = """\
你是一个智能搜索查询解析器。
用户会提出自然语言问题，你需要将其解析为结构化 JSON，供下游混合搜索引擎使用。

输出格式（纯 JSON，不要有代码块标记）：
{
  "search_query": "用于向量语义搜索的核心关键词或短语",
  "filters": {
    "year": <整数 或 null>,
    "category": "<字符串 或 null>",
    "author": "<字符串 或 null>",
    "language": "<zh 或 en 或 null>"
  }
}

规则：
1. search_query 必须是能代表语义的短语，去掉"仅限xxx年"等过滤条件
2. filters 中只填写用户明确提及的约束，其余填 null
3. category 可选值：notice / faq / wiki / case_study / report / term / general
4. 若用户问题不含任何过滤条件，filters 所有字段填 null
5. 只输出 JSON，不要任何解释文字
"""


def parse_query(question: str, client: OpenAI | None = None) -> dict:
    """
    将自然语言问题解析为混合搜索参数。

    参数：
      client : 可选的 OpenAI 客户端实例，不传则自动创建。

    返回值结构：
    {
      "search_query": str,
      "filters": dict | None,
      "raw_filters": dict,
    }
    """
    fallback = {
        "search_query": question,
        "filters": None,
        "raw_filters": {"year": None, "category": None, "author": None, "language": None},
    }

    try:
        if client is None:
            client = get_openai_client()
        model = get_model_name()

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _PARSER_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=256,
        )
        raw = resp.choices[0].message.content or "{}"
        raw = re.sub(r"```[a-z]*", "", raw).strip().strip("`").strip()
        parsed = json.loads(raw)

        search_query = parsed.get("search_query", question).strip() or question
        raw_filters: dict = parsed.get("filters", {})

        where: dict = {}
        if raw_filters.get("year"):
            try:
                where["year"] = int(raw_filters["year"])
            except (ValueError, TypeError):
                pass
        if raw_filters.get("category"):
            where["category"] = str(raw_filters["category"])
        if raw_filters.get("author"):
            where["author"] = str(raw_filters["author"])
        if raw_filters.get("language"):
            where["language"] = str(raw_filters["language"])

        return {
            "search_query": search_query,
            "filters": where if where else None,
            "raw_filters": raw_filters,
        }

    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.warning("查询解析失败，降级为纯向量搜索: %s", exc)
        return fallback
