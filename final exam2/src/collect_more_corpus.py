import time
from pathlib import Path
from src.collect_corpus import fetch_summary, write_markdown, Topic, OUTPUT_DIR, safe_name, logger

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

def collect_new():
    success = []
    failed = []
    for topic in NEW_TOPICS:
        out_path = OUTPUT_DIR / f"wiki_{safe_name(topic.zh_title)}.md"
        if out_path.exists():
            logger.info(f"跳过已存在: {out_path.name}")
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

if __name__ == '__main__':
    success, failed = collect_new()
    logger.info("新增资料: %d", len(success))
    logger.info("失败主题: %d", len(failed))
