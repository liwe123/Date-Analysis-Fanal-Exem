# Final Exam - Plan 2 RAG Project

本项目是"大数据学期项目计划二"实现版，目标是构建一个可复现的 RAG 问答流水线：文档摄取 -> 清洗分块 -> 向量索引 -> 检索生成 -> 引用追溯。

## 1. 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写你自己的配置值。

必填项：
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`

可选项：
- `OPENAI_MODEL`（不填则使用 `gpt-4o-mini`）
- `OPENAI_BASE_URL`（兼容 OpenAI 接口时使用）

环境变量通过显式调用 `init_env()` 加载（位于 `main.py` 和 `streamlit_app.py` 入口处），不在模块导入时自动载入，便于测试隔离。

## 3. 数据目录

默认读取目录：`data/raw/`

支持文本类型：
- `.md`（含 YAML Front-Matter，支持嵌套结构）
- `.txt`
- `.pdf`（需安装 PyMuPDF）

## 4. 建立索引

```bash
python src/main.py build
```

先扩充公开资料库（推荐）：

```bash
python src/main.py collect
```

可选参数：

```bash
python src/main.py build --data-dir "data/raw" --chunk-size 700 --overlap 120
```

> 分块默认参数：`chunk_size=700`, `overlap=120`

## 5. 问答

单次提问：

```bash
python src/main.py ask --question "课程项目最后提交要求是什么？" --top-k 3
```

交互提问：

```bash
python src/main.py ask
```

## 6. Web 演示

```bash
streamlit run app/streamlit_app.py
```

功能特性：
- 对话历史（支持追问）
- 侧边栏显示向量库状态与文档来源列表
- 查询意图解析与元数据过滤展示（year/category/author/language）
- 可调节检索条数（Top K）
- 调试模式：显示解析后的搜索词与过滤条件

## 7. 运行测试

```bash
python -m pytest tests/ -v
```

共 54 个测试用例，覆盖模块：
- `preprocess` — 清洗、分块、分类、元数据合并
- `ingest` — 前端解析（嵌套 YAML）、文件加载
- `query_parser` — 查询解析（正常/空过滤/API 失败/格式错误回退）
- `embed_store` — 初始化、搜索、`max_distance` 过滤、where 回退、计数/来源、安全删除
- `qa` — 空文档兜底、上下文生成、引用缺失补全、年份显示
- `integration` — 摄取→处理流水线、搜索→问答端到端

## 8. 关键设计

### OpenAI 客户端全局单例
`get_openai_client()` 内部缓存，所有模块共享同一连接，避免重复创建。

### 向量搜索距离过滤
`VectorStore.search()` 支持 `max_distance` 参数（余弦距离，0=最相似，2=完全相反），只返回距离不超过上限的结果。

### 安全删除
`VectorStore.delete_collection(confirm=True)` 需要显式确认，防止误删。

### YAML Front-Matter
使用 `pyyaml` 解析，支持嵌套结构（如 tags 列表）。

## 9. 项目结构

```
├── app/
│   └── streamlit_app.py      # Streamlit Web 界面
├── src/
│   ├── __init__.py            # 包标记
│   ├── main.py                # CLI 入口
│   ├── collect_corpus.py      # Wikipedia 语料自动采集
│   ├── ingest.py              # 文档摄取（md/txt/pdf）
│   ├── preprocess.py          # 清洗、分块、元数据提取
│   ├── embed_store.py         # ChromaDB 向量存储与检索
│   ├── qa.py                  # LLM 问答生成
│   ├── query_parser.py        # 查询意图解析
│   └── utils.py               # 公共工具（环境变量、日志、客户端）
├── tests/
│   ├── conftest.py            # Pytest 共享配置
│   ├── test_preprocess.py     # 预处理测试
│   ├── test_ingest.py         # 摄取测试
│   ├── test_query_parser.py   # 查询解析测试
│   ├── test_embed_store.py    # 向量库测试
│   ├── test_qa.py             # 问答测试
│   └── test_integration.py    # 集成测试
├── data/raw/                   # 原始文档目录
├── vector_store/               # ChromaDB 持久化目录（自动生成）
├── report/
│   ├── report.md               # 完整报告
│   ├── task_division.md        # 团队分工方案
│   └── resume_project.md       # 简历项目描述（可直接复制到简历）
├── pipeline_demo.ipynb         # Jupyter Notebook 演示（PDF 要求）
├── AGENTS.md                   # 代码修改规范指南（供 LLM 和开发者阅读）
└── requirements.txt
```

## 10. 报告

完整报告见：`report/report.md`

## 11. 代码规范

所有代码修改请遵循 `AGENTS.md`，该文件包含完整的编码风格、架构约束、错误处理规范和修改 Checklist。
