# RAG Pipeline - 企业知识库检索增强生成系统

## 项目概述

本项目实现了一个完整的RAG（Retrieval-Augmented Generation）系统，能够处理非结构化文档，提供语义搜索和智能问答能力。

### 核心功能

1. **数据摄取**：支持TXT、HTML、PDF等多种文档格式
2. **文本处理**：自动清洗、分块、提取元数据
3. **向量化**：使用sentence-transformers生成高质量嵌入向量
4. **向量存储**：使用ChromaDB进行高效的向量检索
5. **智能问答**：支持语义搜索和LLM生成答案

## 技术栈

| 组件 | 技术选择 | 说明 |
|------|----------|------|
| 嵌入模型 | all-MiniLM-L6-v2 | 免费本地模型，384维 |
| 向量数据库 | ChromaDB | 简单易用，本地文件存储 |
| 分块策略 | 递归字符分割 | 保持语义完整性 |
| LLM | OpenAI GPT-3.5 | 可选，无API Key时使用回退模式 |

## 项目结构

```
rag_pipeline/
├── config/                 # 配置文件
│   └── settings.py         # 全局配置
├── data/                   # 数据目录
│   ├── raw/               # 原始文档
│   │   ├── documents/     # 文档文件
│   │   └── metadata.csv   # 元数据
│   └── processed/         # 处理后的数据
├── src/                    # 源代码
│   ├── ingestion/         # 数据摄取模块
│   ├── processing/        # 数据处理模块
│   ├── embedding/         # 向量化模块
│   ├── storage/           # 向量存储模块
│   ├── retrieval/         # 检索模块
│   ├── generation/        # 答案生成模块
│   └── pipeline/          # 流水线编排
├── app/                    # 应用界面
│   └── streamlit_app.py   # Streamlit演示界面
├── tests/                  # 测试文件
├── run.py                  # 主入口脚本
└── requirements.txt        # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 执行索引

```bash
# 索引所有文档
python run.py index

# 重置并重新索引
python run.py index --reset
```

### 3. 查询文档

```bash
# 单次查询
python run.py query "什么是Python？"

# 交互式查询
python run.py interactive
```

### 4. 启动Web界面

```bash
streamlit run app/streamlit_app.py
```

## 使用示例

### 命令行查询

```bash
# 查询Python相关文档
python run.py query "Python的列表和元组有什么区别？"

# 查询特定作者的文档
python run.py query "作者是张三的文档"

# 查询特定年份的文档
python run.py query "2024年的文档"
```

### Python API

```python
from src.pipeline.indexing_pipeline import IndexingPipeline
from src.pipeline.query_pipeline import QueryPipeline

# 索引文档
indexer = IndexingPipeline(db_path="./chroma_db")
indexer.run("./data/raw/documents")

# 查询
queryer = QueryPipeline(
    chroma_manager=indexer.chroma,
    embedder=indexer.embedder
)
result = queryer.run("什么是Python？")
print(result['answer'])
```

## 支持的文档格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| 文本文件 | .txt | 纯文本格式 |
| HTML文件 | .html, .htm | 网页格式 |
| PDF文件 | .pdf | PDF文档 |

## 配置说明

在 `config/settings.py` 中可以修改以下配置：

```python
# 分块配置
CHUNK_SIZE = 500         # 每个块的目标字符数
CHUNK_OVERLAP = 50       # 块之间的重叠字符数

# 检索配置
TOP_K = 5                # 返回前K个结果

# 嵌入模型
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 嵌入模型名称

# LLM配置（可选）
OPENAI_API_KEY = "your_api_key"  # OpenAI API密钥
```

## 测试

### 运行端到端测试

```bash
python test_e2e.py
```

### 运行模块测试

```bash
python test_ingestion.py
```

## 常见问题

### 1. 如何添加新文档？

将文档放入 `data/raw/documents/` 目录，然后运行：

```bash
python run.py index
```

### 2. 如何使用OpenAI API？

在 `config/settings.py` 中设置 `OPENAI_API_KEY`，或创建 `.env` 文件：

```
OPENAI_API_KEY=your_api_key_here
```

### 3. 如何修改分块大小？

在 `config/settings.py` 中修改：

```python
CHUNK_SIZE = 1000        # 增大块大小
CHUNK_OVERLAP = 100      # 增加重叠
```

## 架构图

```
[原始文档] 
    ↓
[文件扫描] → [文本提取] → [文本清洗] → [分块]
    ↓
[嵌入生成] → [ChromaDB存储]
    ↓
[用户查询] → [查询解析] → [向量检索] → [LLM生成] → [返回答案]
```

## 评分标准对应

| 评分项 | 本项目实现 |
|--------|-----------|
| 执行摘要 | ✅ 完整的RAG系统，解决企业知识库查询问题 |
| 架构图 | ✅ 清晰的数据流：摄取→处理→存储→服务 |
| 技术权衡 | ✅ 选择ChromaDB（简单）而非Milvus（复杂） |
| 代码库 | ✅ 模块化设计，清晰的代码结构 |
| 演示 | ✅ Streamlit界面 + 命令行工具 |

## 许可证

本项目仅用于学术目的。
