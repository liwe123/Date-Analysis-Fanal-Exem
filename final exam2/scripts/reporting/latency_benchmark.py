"""
latency_benchmark.py
=====================
测量 RAG 系统各组件延迟分解。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.utils import get_logger, init_env

logger = get_logger("latency")


def benchmark_latency() -> None:
    """测量各组件延迟并输出分解结果。"""
    from src.embed_store import VectorStore
    from src.qa import generate_answer
    from src.query_parser import parse_query

    store = VectorStore()

    test_queries = [
        "课程项目提交要求是什么？",
        "什么是 RAG？",
        "Hadoop 和 Spark 有什么区别？",
        "2025年的通知有哪些？",
        "向量数据库的工作原理是什么？",
    ]

    results = []

    for q in test_queries:
        # 1. 查询解析延迟
        t0 = time.time()
        parsed = parse_query(q)
        t_parse = time.time() - t0

        search_query = parsed["search_query"]
        filters = parsed["filters"]

        # 2. 嵌入 + 检索延迟
        t1 = time.time()
        retrieved = store.search(search_query, top_k=3, where=filters)
        t_search = time.time() - t1

        # 3. 答案生成延迟
        t2 = time.time()
        if retrieved:
            answer = generate_answer(q, retrieved)
        else:
            answer = "未找到相关文档。"
        t_generate = time.time() - t2

        t_total = t_parse + t_search + t_generate

        r = {
            "query": q,
            "parse_s": round(t_parse, 3),
            "search_s": round(t_search, 3),
            "generate_s": round(t_generate, 3),
            "total_s": round(t_total, 3),
        }
        results.append(r)
        logger.info("%.2fs total (parse=%.2f, search=%.2f, gen=%.2f) — %s",
                    t_total, t_parse, t_search, t_generate, q[:30])

    # 汇总
    avg = lambda key: sum(r[key] for r in results) / len(results)
    summary = {
        "avg_parse_s": round(avg("parse_s"), 3),
        "avg_search_s": round(avg("search_s"), 3),
        "avg_generate_s": round(avg("generate_s"), 3),
        "avg_total_s": round(avg("total_s"), 3),
        "bottleneck": "generate" if avg("generate_s") > avg("search_s") else "search",
    }

    output = {"summary": summary, "results": results}
    out_path = BASE_DIR / "report" / "latency_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("=== 延迟分析完成 ===")
    logger.info("平均查询解析: %.3fs", avg("parse_s"))
    logger.info("平均检索: %.3fs", avg("search_s"))
    logger.info("平均生成: %.3fs", avg("generate_s"))
    logger.info("平均总延迟: %.3fs", avg("total_s"))
    logger.info("瓶颈组件: %s", summary["bottleneck"])


if __name__ == "__main__":
    init_env()
    benchmark_latency()
