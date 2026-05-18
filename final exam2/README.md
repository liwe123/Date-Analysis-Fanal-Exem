# 📚 课程知识库 RAG 助手

> 基于检索增强生成（RAG）的智能问答系统 | 大数据学期项目 — 方向 B

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-54%20passed-green.svg)](https://github.com/liwe123/Date-Analysis-Fanal-Exem)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![GPU](https://img.shields.io/badge/GPU-CUDA%2012.4-brightgreen.svg)](https://pytorch.org/)

---

## ✨ 特性

- **RAG 全流水线**：文档摄取 → 清洗分块 → 向量索引 → 混合检索 → LLM 答案生成 + 引用追溯
- **本地嵌入**：`Qwen3-Embedding-0.6B`（1024 维），GPU CUDA 加速，零 API 费用
- **混合检索**：向量语义搜索 + 元数据过滤器（年份/分类/作者/语言）
- **AI 查询解析**：自然语言自动提取搜索词与过滤条件
- **双端入口**：CLI 命令行 + 现代化 Streamlit Web 界面（极简黑白高级质感、SVG 矢量图标、毛玻璃视效）
- **自动采集**：Wikipedia API 自动获取 58 个大数据专业词条作为背景知识库
- **54 个测试**：全覆盖单元测试 + 集成测试

---

## 🏗️ 架构

```
data/raw/*.md → ingest.py → preprocess.py → embed_store.py ─┐
                  读取       清洗 / 分块       ChromaDB 索引   │
                                                              ↓
用户问题 → query_parser.py ───────────────────────────→ VectorStore.search()
              LLM 意图解析                                 混合检索

       ↓
  qa.py → 生成回答 + 引用来源 → CLI / Streamlit 展示
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
git clone https://github.com/liwe123/Date-Analysis-Fanal-Exem.git
cd "final exam2"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> **GPU 加速**：如需 CUDA 加速，额外安装 PyTorch CUDA 版
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu124
> ```

### 2. 配置

```bash
cp .env.example .env   # 编辑填入 OPENAI_API_KEY
```

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM API 密钥 |
| `OPENAI_BASE_URL` | ❌ | 自定义 API 地址（兼容 DeepSeek 等） |
| `OPENAI_MODEL` | ❌ | 默认 `deepseek-v4-flash` |
| `OPENAI_EMBEDDING_MODEL` | ❌ | 设为 `local` 使用本地模型 |
| `LOCAL_EMBEDDING_MODEL` | ❌ | 默认 `Qwen/Qwen3-Embedding-0.6B` |
| `HF_ENDPOINT` | ❌ | 国内网络设 `https://hf-mirror.com` |

### 3. 建立索引

```bash
# 先采集 Wikipedia 背景知识（推荐）
python src/main.py collect

# 构建向量索引
python src/main.py build
```

### 4. 问答

```bash
# 单次提问
python src/main.py ask --question "课程项目提交要求是什么？"

# 交互模式
python src/main.py ask
```

### 5. Web 界面

```bash
streamlit run app/streamlit_app.py
```

---

## 🧪 测试

```bash
python -m pytest tests/ -v
```

| 模块 | 测试数 | 覆盖 |
|------|--------|------|
| `preprocess` | 14 | 清洗、分块、分类、元数据合并 |
| `embed_store` | 9 | 初始化、搜索、距离过滤、安全删除 |
| `ingest` | 8 | YAML 解析、文件加载（含递归） |
| `qa` | 5 | 上下文生成、引用补全、回退 |
| `query_parser` | 4 | 正常/异常/格式错误/API 失败 |
| `integration` | 4 | 摄取→处理、搜索→问答端到端 |

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DeepSeek V4 Flash (OpenAI-compatible API) |
| Embedding | Qwen3-Embedding-0.6B（本地，1024 维，GPU CUDA） |
| 向量数据库 | ChromaDB |
| 文档解析 | PyMuPDF (PDF) + PyYAML (Front-Matter) |
| 前端 | Streamlit |
| 测试 | Pytest (54 用例) |
| 语料 | 78 篇课程文档 + 58 篇 Wikipedia 词条 |

---

## 📁 项目结构

```
├── app/streamlit_app.py     # Streamlit Web 界面
├── src/
│   ├── main.py              # CLI 入口 (build / ask / collect)
│   ├── collect_corpus.py    # Wikipedia 语料采集
│   ├── ingest.py            # 文档摄取 (md/txt/pdf)
│   ├── preprocess.py        # 清洗、分块、元数据提取
│   ├── embed_store.py       # ChromaDB 向量存储与检索
│   ├── qa.py                # LLM 问答生成
│   ├── query_parser.py      # 查询意图解析
│   └── utils.py             # 公共工具（环境变量、日志、客户端）
├── tests/                   # 54 个测试用例
├── data/raw/                # 原始文档 + Wikipedia 词条
├── vector_store/            # ChromaDB 持久化目录
├── report/report.md         # 完整项目报告
├── pipeline_demo.ipynb      # Jupyter Notebook 演示
├── AGENTS.md                # 代码规范指南
└── requirements.txt
```

---

## 📖 文档

- 完整报告：[report/report.md](./report/report.md)
- Jupyter 演示：[pipeline_demo.ipynb](./pipeline_demo.ipynb)
- 开发规范：[AGENTS.md](./AGENTS.md)
