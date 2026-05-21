"""
collect_more_corpus.py
======================
自适应高级语料采集模块：用于对核心技术主题进行补充性的 Wikipedia 语料抓取。
"""

from __future__ import annotations

# 1. 标准库
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# 2. 项目模块
from src.utils import get_logger

# ── 显式初始化与配置 ──────────────────────────────────────────────────

logger = get_logger("collect_more_corpus")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "raw" / "external"

USER_AGENT = "final-exam-rag-corpus-bot/1.0 (edu project)"

MAX_RETRIES = 3
RETRY_DELAY = 2


class Topic(NamedTuple):
    """主题结构体，包含中文名、英文名和关联标签。"""
    zh_title: str
    en_title: str
    tag: str


NEW_TOPICS = [
    Topic("Apache HBase", "Apache HBase", "hadoop"),
    Topic("Apache Cassandra", "Apache Cassandra", "database"),
    Topic("Elasticsearch", "Elasticsearch", "search"),
    Topic("Logstash", "Logstash", "data_engineering"),
    Topic("Kibana", "Kibana", "viz"),
    Topic("数据湖", "Data lake", "lakehouse"),
    Topic("联机分析处理", "Online analytical processing", "database"),
    Topic("联机事务处理", "Online transaction processing", "database"),
    Topic("Apache ZooKeeper", "Apache ZooKeeper", "distributed"),
    Topic("Apache Hadoop YARN", "Apache Hadoop YARN", "hadoop"),
    Topic("B树", "B-tree", "data_structure"),
    Topic("LSM树", "Log-structured merge-tree", "data_structure"),
    Topic("布隆过滤器", "Bloom filter", "data_structure"),
    Topic("一致性哈希", "Consistent hashing", "distributed"),
    Topic("微服务", "Microservices", "architecture"),
    Topic("REST", "Representational state transfer", "architecture"),
    Topic("GraphQL", "GraphQL", "architecture"),
    Topic("ClickHouse", "ClickHouse", "database"),
    Topic("数据血缘", "Data lineage", "governance"),
    Topic("数据集成", "Data integration", "data_engineering"),
    Topic("数据脱敏", "Data masking", "security"),
    Topic("图神经网络", "Graph neural network", "dl"),
    Topic("生成对抗网络", "Generative adversarial network", "dl"),
    Topic("支持向量机", "Support vector machine", "ml"),
    Topic("朴素贝叶斯分类器", "Naive Bayes classifier", "ml"),
    Topic("K-近邻算法", "K-nearest neighbors algorithm", "ml"),
    Topic("K-平均算法", "K-means clustering", "ml"),
    Topic("循环神经网络", "Recurrent neural network", "dl"),
    Topic("卷积神经网络", "Convolutional neural network", "dl"),
    Topic("长短期记忆", "Long short-term memory", "dl"),
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
    """将文本转为安全的文件名（小写、下划线、去除特殊字符）。"""
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-\u4e00-\u9fff]", "", text)
    return text[:80] or "topic"


def write_markdown(topic: Topic, summary: dict) -> Path:
    """将采集到的摘要写入 Markdown 文件，返回输出路径。"""
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


def collect_new() -> tuple[list[str], list[str]]:
    """
    遍历核心新主题并采集其 Wikipedia 摘要。

    返回：
      (成功写入的文件路径列表, 失败的主题中文名列表)
    """
    success = []
    failed = []
    for topic in NEW_TOPICS:
        out_path = OUTPUT_DIR / f"wiki_{safe_name(topic.zh_title)}.md"
        if out_path.exists():
            logger.info("跳过已存在: %s", out_path.name)
            continue

        item = fetch_summary("zh", topic.zh_title)
        if item is None:
            time.sleep(1)
            item = fetch_summary("en", topic.en_title)

        if item is None:
            logger.warning("采集失败: %s", topic.zh_title)
            failed.append(topic.zh_title)
            continue

        out_path = write_markdown(topic, item)
        success.append(str(out_path))
        logger.info("已写入: %s", out_path.name)
        time.sleep(1)

    return success, failed


if __name__ == "__main__":
    success, failed = collect_new()
    logger.info("新增资料: %d", len(success))
    logger.info("失败主题: %d", len(failed))
