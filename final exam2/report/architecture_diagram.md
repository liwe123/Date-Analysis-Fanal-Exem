# RAG 系统架构图（Mermaid 格式）

> 可直接嵌入 Markdown，或在 [mermaid.live](https://mermaid.live) 导出为 PNG/SVG

```mermaid
graph TB
    subgraph 数据源层
        A1[data/raw/*.md<br/>50+ 课程文档]
        A2[Wikipedia API<br/>83 个词条]
        A3[Stack Overflow API<br/>30 篇问答]
        A4[CSDN 搜索 API<br/>18 篇博客]
    end

    subgraph 摄取层
        B1[ingest.py<br/>MD/TXT/PDF 解析<br/>YAML Front-Matter]
        B2[collect_corpus.py<br/>Wikipedia REST API]
        B3[collect_stackoverflow.py<br/>Stack Exchange API]
        B4[collect_csdn.py<br/>CSDN 搜索 API]
    end

    subgraph 处理层
        C1[clean_text()<br/>HTML标签/实体/控制符/空白]
        C2[chunk_text()<br/>段落→句子→贪心→滑窗<br/>chunk=700, overlap=120]
        C3[extract_metadata()<br/>LLM 提取作者/年份/分类/摘要<br/>32线程并发, 429退避重试]
    end

    subgraph 存储层
        D1[Qwen3-Embedding-0.6B<br/>1024维, CUDA GPU]
        D2[ChromaDB<br/>HNSW 索引, cosine 距离<br/>vector_store/]
    end

    subgraph 查询层
        E1[query_parser.py<br/>LLM 意图解析<br/>自然语言→search_query+filters]
        E2[embed_store.search()<br/>语义向量 + 元数据过滤<br/>+ max_distance 阈值]
        E3[qa.py<br/>System Prompt 约束<br/>+ 来源强制标注]
    end

    subgraph 服务层
        F1[CLI<br/>python -m src.main ask]
        F2[Streamlit Web<br/>多轮对话/调试模式/数据管理]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
    B1 --> C1
    B2 --> C1
    B3 --> C1
    B4 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D1
    D1 --> D2

    E1 --> E2
    D2 --> E2
    E2 --> E3
    E3 --> F1
    E3 --> F2

    style A1 fill:#e1f5fe
    style A2 fill:#e1f5fe
    style A3 fill:#e1f5fe
    style A4 fill:#e1f5fe
    style D2 fill:#fff3e0
    style E3 fill:#e8f5e9
    style F2 fill:#f3e5f5
```
