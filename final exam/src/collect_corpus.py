import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.utils import get_logger

logger = get_logger("collect_corpus")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "external"

USER_AGENT = "final-exam-rag-corpus-bot/1.0 (edu project)"

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 2  # 请求间隔（秒）


@dataclass
class Topic:
    zh_title: str
    en_title: str
    tag: str


TOPICS = [
    # 原有话题
    Topic("检索增强生成", "Retrieval-augmented generation", "rag"),
    Topic("向量数据库", "Vector database", "vector_db"),
    Topic("Apache Spark", "Apache Spark", "spark"),
    Topic("Apache Kafka", "Apache Kafka", "kafka"),
    Topic("数据湖仓一体", "Data lakehouse", "lakehouse"),
    Topic("ETL", "Extract, transform, load", "etl"),
    Topic("信息检索", "Information retrieval", "ir"),
    Topic("余弦相似度", "Cosine similarity", "similarity"),
    Topic("词嵌入", "Word embedding", "embedding"),
    Topic("TF-IDF", "Tf-idf", "retrieval"),
    Topic("BM25", "Okapi BM25", "retrieval"),
    Topic("倒排索引", "Inverted index", "retrieval"),
    Topic("数据清洗", "Data cleansing", "data_quality"),
    Topic("知识图谱", "Knowledge graph", "kg"),
    Topic("大语言模型", "Large language model", "llm"),
    Topic("Transformer", "Transformer (deep learning architecture)", "llm"),
    Topic("微调（机器学习）", "Fine-tuning (deep learning)", "llm"),
    Topic("提示工程", "Prompt engineering", "llm"),
    Topic("A/B测试", "A/B testing", "evaluation"),
    Topic("准确率与召回率", "Precision and recall", "evaluation"),
    Topic("平均倒数排名", "Mean reciprocal rank", "evaluation"),
    Topic("数据治理", "Data governance", "governance"),
    Topic("元数据", "Metadata", "metadata"),
    Topic("可观测性", "Observability", "ops"),
    Topic("分布式系统", "Distributed computing", "distributed"),
    Topic("容错", "Fault tolerance", "reliability"),
    Topic("流处理", "Stream processing", "streaming"),
    Topic("批处理", "Batch processing", "batch"),
    # 新增话题
    Topic("数据挖掘", "Data mining", "data_science"),
    Topic("机器学习", "Machine learning", "ml"),
    Topic("深度学习", "Deep learning", "dl"),
    Topic("自然语言处理", "Natural language processing", "nlp"),
    Topic("Hadoop", "Apache Hadoop", "hadoop"),
    Topic("MapReduce", "MapReduce", "hadoop"),
    Topic("Apache Hive", "Apache Hive", "hadoop"),
    Topic("SQL", "SQL", "database"),
    Topic("NoSQL", "NoSQL", "database"),
    Topic("数据仓库", "Data warehouse", "warehouse"),
    Topic("数据管道", "Data pipeline", "data_engineering"),
    Topic("特征工程", "Feature engineering", "ml"),
    Topic("交叉验证", "Cross-validation (statistics)", "ml"),
    Topic("过拟合", "Overfitting", "ml"),
    Topic("正则化（机器学习）", "Regularization (mathematics)", "ml"),
    Topic("梯度下降法", "Gradient descent", "ml"),
    Topic("随机森林", "Random forest", "ml"),
    Topic("主成分分析", "Principal component analysis", "ml"),
    Topic("聚类分析", "Cluster analysis", "ml"),
    Topic("决策树", "Decision tree learning", "ml"),
    Topic("Apache Flink", "Apache Flink", "streaming"),
    Topic("数据可视化", "Data and information visualization", "viz"),
    Topic("Docker", "Docker (software)", "devops"),
    Topic("云计算", "Cloud computing", "cloud"),
    Topic("图数据库", "Graph database", "database"),
    Topic("时序数据库", "Time series database", "database"),
    Topic("CAP定理", "CAP theorem", "distributed"),
    Topic("数据安全", "Data security", "security"),
    Topic("强化学习", "Reinforcement learning", "ml"),
    Topic("迁移学习", "Transfer learning", "ml"),
    Topic("降维", "Dimensionality reduction", "ml"),
]


def fetch_summary(lang: str, title: str) -> dict | None:
    """从 Wikipedia REST API 获取摘要，带重试机制。"""
    encoded_title = quote(title, safe="")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
    req = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            extract = payload.get("extract", "").strip()
            if not extract:
                return None

            real_title = payload.get("title", title).strip()
            source_url = payload.get("content_urls", {}).get("desktop", {}).get("page", url)
            return {"title": real_title, "extract": extract, "url": source_url}

        except HTTPError as exc:
            if exc.code == 429:
                wait = RETRY_DELAY * attempt * 3
                logger.warning("请求频率限制 [429] [%s/%s] 第%d次, 等待 %ds…", lang, title, attempt, wait)
                time.sleep(wait)
            elif exc.code == 404:
                return None
            else:
                logger.warning("HTTP %d [%s/%s] 第%d次", exc.code, lang, title, attempt)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

        except (URLError, TimeoutError, OSError) as exc:
            logger.warning("请求失败 [%s/%s] 第%d次: %s", lang, title, attempt, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    return None


def safe_name(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-\u4e00-\u9fff]", "", text)
    return text[:80] or "topic"


def write_markdown(topic: Topic, summary: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"wiki_{safe_name(topic.zh_title)}.md"
    out_path = OUTPUT_DIR / file_name
    fetched_at = datetime.now(timezone.utc).isoformat()

    content = (
        f"# {summary['title']}\n\n"
        f"- 主题标签: {topic.tag}\n"
        f"- 抓取时间(UTC): {fetched_at}\n"
        f"- 来源: {summary['url']}\n\n"
        "## 摘要\n"
        f"{summary['extract']}\n\n"
        "## 课程关联说明\n"
        "该条目可用于支持计划二报告中的技术解释、术语定义与答辩问答。\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def collect() -> tuple[list[str], list[str]]:
    success = []
    failed = []

    for topic in TOPICS:
        item = fetch_summary("zh", topic.zh_title)
        if item is None:
            time.sleep(REQUEST_DELAY)
            item = fetch_summary("en", topic.en_title)

        if item is None:
            logger.warning("采集失败: %s", topic.zh_title)
            failed.append(topic.zh_title)
            continue

        out_path = write_markdown(topic, item)
        success.append(str(out_path))
        logger.info("已写入: %s", out_path.name)
        time.sleep(REQUEST_DELAY)

    return success, failed


def main():
    success, failed = collect()
    logger.info("已写入资料: %d", len(success))
    for p in success:
        logger.info("  - %s", p)

    logger.info("失败主题: %d", len(failed))
    for t in failed:
        logger.info("  - %s", t)


if __name__ == "__main__":
    main()
