"""
evaluation.py
==============
RAG 系统评估脚本：运行 50 个测试查询，记录延迟、检索命中率、幻觉频率。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# 动态插入项目根路径
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.utils import get_logger, init_env

logger = get_logger("evaluation")


# ── 50 个测试查询 ─────────────────────────────────────────────────

TEST_QUERIES: list[dict] = [
    # === A 类：课程信息查询（10 题） ===
    {"id": 1, "category": "课程信息", "question": "课程项目最后提交截止日期是什么？", "expected_source_hint": ["project_requirements", "submission_rules", "notice"]},
    {"id": 2, "category": "课程信息", "question": "期末考试的形式是什么？", "expected_source_hint": ["notice", "faq"]},
    {"id": 3, "category": "课程信息", "question": "这门课的评分标准是什么？", "expected_source_hint": ["grading_policy", "course_intro", "faq"]},
    {"id": 4, "category": "课程信息", "question": "实验报告需要包含哪些内容？", "expected_source_hint": ["lab_manual", "faq"]},
    {"id": 5, "category": "课程信息", "question": "课程项目有哪些可选方向？", "expected_source_hint": ["project_requirements", "course_intro"]},
    {"id": 6, "category": "课程信息", "question": "团队项目最少需要几个人？", "expected_source_hint": ["project_requirements", "faq", "notice"]},
    {"id": 7, "category": "课程信息", "question": "什么时候可以找老师答疑？", "expected_source_hint": ["notice", "course_schedule"]},
    {"id": 8, "category": "课程信息", "question": "课程涵盖哪些大数据技术？", "expected_source_hint": ["course_intro", "course_schedule"]},
    {"id": 9, "category": "课程信息", "question": "如何提交作业？", "expected_source_hint": ["submission_rules", "faq"]},
    {"id": 10, "category": "课程信息", "question": "项目演示时间是多少分钟？", "expected_source_hint": ["project_requirements", "notice"]},

    # === B 类：技术概念查询（10 题） ===
    {"id": 11, "category": "技术概念", "question": "什么是检索增强生成（RAG）？", "expected_source_hint": ["wiki_检索增强生成", "rag_system_notes"]},
    {"id": 12, "category": "技术概念", "question": "向量数据库的工作原理是什么？", "expected_source_hint": ["wiki_向量数据库", "vector_db_notes"]},
    {"id": 13, "category": "技术概念", "question": "什么是 Apache Kafka？它有什么用途？", "expected_source_hint": ["wiki", "so_apache-kafka"]},
    {"id": 14, "category": "技术概念", "question": "Hadoop 和 Spark 有什么区别？", "expected_source_hint": ["wiki", "so_apache-spark", "csdn"]},
    {"id": 15, "category": "技术概念", "question": "什么是流处理和批处理？", "expected_source_hint": ["wiki", "term_stream_processing", "term_batch_processing"]},
    {"id": 16, "category": "技术概念", "question": "什么是嵌入向量（Embedding）？", "expected_source_hint": ["wiki", "embedding_notes"]},
    {"id": 17, "category": "技术概念", "question": "HNSW 索引算法是怎么工作的？", "expected_source_hint": ["wiki", "vector_db_notes"]},
    {"id": 18, "category": "技术概念", "question": "什么是 Delta Lake 的青铜白银黄金分层？", "expected_source_hint": ["term_bronze_silver_gold", "wiki"]},
    {"id": 19, "category": "技术概念", "question": "什么是 AI 幻觉？如何防止？", "expected_source_hint": ["term_hallucination", "rag_system_notes"]},
    {"id": 20, "category": "技术概念", "question": "什么是元数据？在 RAG 中有什么作用？", "expected_source_hint": ["term_metadata", "rag_system_notes"]},

    # === C 类：跨文档综合查询（10 题） ===
    {"id": 21, "category": "跨文档", "question": "向量数据库和传统关系型数据库有什么区别？各自的适用场景是什么？", "expected_source_hint": ["wiki_向量数据库", "vector_db_notes"]},
    {"id": 22, "category": "跨文档", "question": "RAG 系统中分块策略对检索质量有什么影响？", "expected_source_hint": ["chunking_notes", "rag_system_notes"]},
    {"id": 23, "category": "跨文档", "question": "如何评估一个 RAG 系统的好坏？有哪些指标？", "expected_source_hint": ["evaluation_notes", "rag_system_notes"]},
    {"id": 24, "category": "跨文档", "question": "在大数据项目中，数据清洗通常包括哪些步骤？", "expected_source_hint": ["csdn_etl", "wiki"]},
    {"id": 25, "category": "跨文档", "question": "Kafka 和 Flink 在流处理场景中各自扮演什么角色？", "expected_source_hint": ["so_apache-kafka", "so_apache-flink", "wiki"]},
    {"id": 26, "category": "跨文档", "question": "Spark 的内存计算模型相比 Hadoop MapReduce 有什么优势？", "expected_source_hint": ["so_apache-spark", "csdn_spark", "wiki"]},
    {"id": 27, "category": "跨文档", "question": "在 RAG 系统中，Embedding 模型的选择对最终效果有多大影响？", "expected_source_hint": ["embedding_notes", "rag_system_notes"]},
    {"id": 28, "category": "跨文档", "question": "如何处理 RAG 系统中的长文档？分块太小或太大分别会有什么问题？", "expected_source_hint": ["chunking_notes", "rag_system_notes"]},
    {"id": 29, "category": "跨文档", "question": "数据仓库中 ETL 和 ELT 有什么区别？", "expected_source_hint": ["csdn_etl", "wiki"]},
    {"id": 30, "category": "跨文档", "question": "Hive 在大数据生态中是什么角色？和 Spark SQL 有什么区别？", "expected_source_hint": ["csdn__hive", "so_apache-hive", "wiki"]},

    # === D 类：元数据过滤查询（10 题） ===
    {"id": 31, "category": "元数据过滤", "question": "2025年的通知有哪些？", "expected_source_hint": ["notice"]},
    {"id": 32, "category": "元数据过滤", "question": "老师在2025年说过关于考试的事情吗？", "expected_source_hint": ["notice"]},
    {"id": 33, "category": "元数据过滤", "question": "找一下 Wikipedia 上关于大数据术语的资料", "expected_source_hint": ["wiki"]},
    {"id": 34, "category": "元数据过滤", "question": "有没有 Stack Overflow 上关于 Spark 的问答？", "expected_source_hint": ["so_apache-spark"]},
    {"id": 35, "category": "元数据过滤", "question": "CSDN 上有哪些关于 Hadoop 的教程？", "expected_source_hint": ["csdn_hadoop"]},
    {"id": 36, "category": "元数据过滤", "question": "有哪些案例分析？", "expected_source_hint": ["case_study"]},
    {"id": 37, "category": "元数据过滤", "question": "查找关于 Flink 的中文资料", "expected_source_hint": ["wiki", "csdn_flink", "so_apache-flink"]},
    {"id": 38, "category": "元数据过滤", "question": "有没有关于 Kafka 的英文问答？", "expected_source_hint": ["so_apache-kafka"]},
    {"id": 39, "category": "元数据过滤", "question": "FAQ 类型的文档有哪些？", "expected_source_hint": ["faq"]},
    {"id": 40, "category": "元数据过滤", "question": "术语表里定义了哪些概念？", "expected_source_hint": ["term"]},

    # === E 类：边界 / 超纲查询（10 题） ===
    {"id": 41, "category": "边界测试", "question": "钢琴考级需要准备什么？", "expected_source_hint": []},
    {"id": 42, "category": "边界测试", "question": "今天天气怎么样？", "expected_source_hint": []},
    {"id": 43, "category": "边界测试", "question": "如何做红烧肉？", "expected_source_hint": []},
    {"id": 44, "category": "边界测试", "question": "Python 的 for 循环怎么写？", "expected_source_hint": []},
    {"id": 45, "category": "边界测试", "question": "2024年美国总统大选结果是什么？", "expected_source_hint": []},
    {"id": 46, "category": "边界测试", "question": "这门课的老师叫什么名字？", "expected_source_hint": []},
    {"id": 47, "category": "边界测试", "question": "项目的 GitHub 仓库地址是什么？", "expected_source_hint": []},
    {"id": 48, "category": "边界测试", "question": "隔壁班的项目做了什么方向？", "expected_source_hint": []},
    {"id": 49, "category": "边界测试", "question": "能不能帮我写一段 Java 代码？", "expected_source_hint": []},
    {"id": 50, "category": "边界测试", "question": "RAG 和 ChatGPT 哪个更好用？", "expected_source_hint": ["rag_system_notes", "wiki_检索增强生成"]},
]


def run_evaluation() -> None:
    """运行全部 50 个评估查询，输出结果到 evaluation_results.json。"""
    from src.embed_store import VectorStore
    from src.qa import generate_answer
    from src.query_parser import parse_query

    store = VectorStore()
    logger.info("向量库总块数: %d", store.count())

    results: list[dict] = []
    total_latency = 0.0
    hallucination_count = 0
    retrieval_hit_count = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        qid = test["id"]
        question = test["question"]
        category = test["category"]
        expected_hints = test["expected_source_hint"]

        logger.info("[%d/50] Q%d (%s): %s", i, qid, category, question)

        # ── Step 1: 查询解析 + 检索 ──
        t0 = time.time()
        parsed = parse_query(question)
        search_query = parsed["search_query"]
        filters = parsed["filters"]

        retrieved = store.search(search_query, top_k=3, where=filters)
        t_retrieve = time.time() - t0

        # ── Step 2: 答案生成 ──
        t1 = time.time()
        if retrieved:
            answer = generate_answer(question, retrieved)
        else:
            answer = "未找到相关文档，无法回答。"
        t_generate = time.time() - t1

        t_total = t_retrieve + t_generate
        total_latency += t_total

        # ── Step 3: 分析检索命中 ──
        retrieved_sources = [r.get("source", "") for r in retrieved]
        retrieved_texts = [r.get("text", "")[:300] for r in retrieved]

        # 命中判断：expected_hints 中任一关键词出现在任一 source 中
        hit = False
        if expected_hints:
            for hint in expected_hints:
                for src in retrieved_sources:
                    if hint.lower() in src.lower():
                        hit = True
                        break
                if hit:
                    break
        else:
            # 超纲题：期望检索到 0 个或低相关结果
            hit = True  # 超纲题默认"命中"（正确行为是无结果或低分）

        if hit:
            retrieval_hit_count += 1

        # ── Step 4: 幻觉检测（简单规则） ──
        is_out_of_scope = len(expected_hints) == 0
        hallucinated = False

        if is_out_of_scope and retrieved:
            # 超纲题但 LLM 给出了具体答案（非拒答），视为幻觉
            refusal_keywords = ["没有相关信息", "无法回答", "未找到", "不属于", "不了解", "不知道", "资料中没有"]
            if not any(kw in answer for kw in refusal_keywords):
                hallucinated = True
                hallucination_count += 1

        # ── 记录结果 ──
        result = {
            "id": qid,
            "category": category,
            "question": question,
            "search_query": search_query,
            "filters": filters,
            "retrieved_sources": retrieved_sources,
            "retrieved_scores": [r.get("score") for r in retrieved],
            "answer_snippet": answer[:500],
            "latency_s": round(t_total, 3),
            "retrieval_hit": hit,
            "expected_source_hints": expected_hints,
            "is_out_of_scope": is_out_of_scope,
            "hallucinated": hallucinated,
        }
        results.append(result)

        status = "HIT" if hit else "MISS"
        hall = " [HALLUCINATION]" if hallucinated else ""
        logger.info("  → %s | %.2fs | sources=%s%s", status, t_total, retrieved_sources[:3], hall)

    # ── 汇总统计 ──
    total = len(results)
    avg_latency = total_latency / total if total else 0
    in_scope = [r for r in results if not r["is_out_of_scope"]]
    out_scope = [r for r in results if r["is_out_of_scope"]]

    in_scope_hits = sum(1 for r in in_scope if r["retrieval_hit"])
    recall_at_3 = in_scope_hits / len(in_scope) if in_scope else 0

    out_scope_correct = sum(1 for r in out_scope if not r["hallucinated"])
    out_scope_accuracy = out_scope_correct / len(out_scope) if out_scope else 0

    summary = {
        "total_queries": total,
        "in_scope_queries": len(in_scope),
        "out_of_scope_queries": len(out_scope),
        "recall_at_3": round(recall_at_3, 4),
        "in_scope_hit_count": in_scope_hits,
        "hallucination_count": hallucination_count,
        "out_scope_accuracy": round(out_scope_accuracy, 4),
        "avg_latency_s": round(avg_latency, 3),
        "total_latency_s": round(total_latency, 3),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    output_path = BASE_DIR / "report" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("=== 评估完成 ===")
    logger.info("Recall@3: %.2f%% (%d/%d)", recall_at_3 * 100, in_scope_hits, len(in_scope))
    logger.info("幻觉次数: %d / %d 超纲题", hallucination_count, len(out_scope))
    logger.info("平均延迟: %.3fs", avg_latency)
    logger.info("结果已保存至: %s", output_path)


if __name__ == "__main__":
    init_env()
    run_evaluation()
