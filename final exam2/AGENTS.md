# AGENTS.md — 项目规范化修改指南

> **面向对象**：人 + 大模型。任何对代码库的修改都应遵循本文档。

---

## 一、项目概述

| 项 | 值 |
|---|-----|
| 项目名称 | 大数据学期项目 — 方向 B：RAG 检索增强生成助手 |
| 语言 | Python 3.11+ |
| 核心能力 | 文档摄取 → 清洗分块 → 向量索引 → 混合检索 → 答案生成 |
| 入口 | `src/main.py` (CLI), `app/streamlit_app.py` (Web) |
| 测试 | `pytest` (91 个用例, `tests/`) |
| 编码 | UTF-8，注释/文档字符串用中文 |

---

## 二、代码风格（必须遵守）

### 2.1 文件头

每个 `.py` 文件必须以下列格式开头：

```python
"""
module_name.py
==============
一句话描述模块职责。
"""
```

第一行放 `from __future__ import annotations`（若文件需要类型标注）。

### 2.2 导入顺序

严格按四组排列，组间空一行：

```python
# 1. __future__
from __future__ import annotations

# 2. 标准库
import json
from pathlib import Path

# 3. 第三方库
import chromadb
from openai import OpenAI

# 4. 项目模块
from src.utils import get_logger, get_openai_client
```

### 2.3 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | `snake_case` | `embed_store.py`, `query_parser.py` |
| 函数 (公开) | `snake_case`, `verb_noun` | `load_text_files`, `parse_query` |
| 函数 (私有) | `_` 前缀 + `snake_case` | `_parse_front_matter`, `_guess_category` |
| 类 | `PascalCase` | `VectorStore`, `Topic` |
| 常量 | `UPPER_CASE` 模块级 | `MAX_RETRIES`, `SUPPORTED_SUFFIXES` |
| 变量 | `snake_case` | `data_dir`, `chunk_size`, `top_k` |
| 布尔变量 | `is_` / `has_` 前缀 | `HAS_PYMUPDF`, `is_extract_meta` |

### 2.4 类型标注

- 使用 PEP 604 联合类型语法：`str | None`（不使用 `Optional[str]`）
- 所有公开函数必须标注参数和返回值
- 不可变默认值直接用，可变默认值用 `None` 哨兵：

```python
# ✅ 正确
def search(query: str, top_k: int = 5, where: dict | None = None) -> list[dict]:
    ...

# ❌ 错误
def search(query, top_k=5, where={}):
    ...
```

### 2.5 字符串

- 一律使用双引号 `"`（除非内嵌于 f-string 中需要转义时用单引号）
- 文档字符串用 `"""..."""`
- f-string 优先于 `.format()` 和 `%`

### 2.6 行长度

- 目标 90 字符，硬上限 120 字符
- 长字符串用隐式拼接拆分

### 2.7 代码区块分隔

模块内不同功能区用 Unicode 绘图字符分隔：

```python
# ── 搜索 ──────────────────────────────────────────────
```

### 2.8 路径处理

- 必须使用 `pathlib.Path`，禁止 `os.path` 和硬编码路径
- 项目根目录统一从 `Path(__file__)` 推导：

```python
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
```

---

## 三、架构约束（不可违反）

### 3.1 模块职责边界

| 模块 | 允许做的事 | 禁止做的事 |
|------|-----------|-----------|
| `ingest.py` | 读文件、解析 Front-Matter | 清洗文本、调用 LLM |
| `preprocess.py` | 清洗、分块、调用 LLM 提取元数据 | 读写 ChromaDB |
| `embed_store.py` | 向量嵌入、ChromaDB 读写 | 生成回答、解析查询 |
| `qa.py` | 生成答案、格式化引用 | 操作数据库 |
| `query_parser.py` | 解析查询意图 | 执行检索、生成答案 |
| `collect_corpus.py` | Wikipedia 语料采集 | 操作 ChromaDB |
| `collect_stackoverflow.py` | Stack Overflow 问答采集 | 操作 ChromaDB |
| `collect_csdn.py` | CSDN 博客采集 | 操作 ChromaDB |
| `collect_more_corpus.py` | 自适应高级语料采集 | 操作 ChromaDB |
| `main.py` | 编排流水线、CLI 入口 | 包含业务逻辑 |
| `utils.py` | 环境变量、日志、客户端单例 | 包含业务逻辑 |

### 3.2 依赖方向

```
main.py / streamlit_app.py
    ├── ingest.py ────── 依赖 utils.py
    ├── preprocess.py ── 依赖 utils.py
    ├── embed_store.py ─ 依赖 utils.py
    ├── qa.py ────────── 依赖 utils.py
    ├── query_parser.py ─ 依赖 utils.py
    ├── collect_corpus.py ─── 依赖 utils.py
    ├── collect_stackoverflow.py ── 依赖 utils.py
    ├── collect_csdn.py ───── 依赖 utils.py
    ├── collect_more_corpus.py ── 依赖 utils.py
    └── utils.py ─────── 无内部依赖
```

**规则**：`utils.py` 不依赖任何项目模块。其他所有模块在需要读取配置/日志时仅依赖 `utils.py`。模块之间不交叉依赖（例如，采集脚本彼此独立）。

---

## 四、环境变量管理

### 4.1 支持的变量

| 变量名 | 必填 | 默认值 | 用途 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API 密钥 |
| `OPENAI_EMBEDDING_MODEL` | ❌ | `local` | Embedding 模型名（若设为 local 或为空，则默认启用本地嵌入模式） |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | 对话模型名 |
| `OPENAI_BASE_URL` | ❌ | `None` | 自定义 API 地址 |
| `OPENAI_EMBEDDING_BASE_URL` | ❌ | `None` | 远程 Embedding 服务地址 |
| `EMBEDDING_SERVER_TOKEN` | ❌ | `None` | AutoDL 远程 Embedding 服务访问令牌 |
| `LOCAL_EMBEDDING_MODEL` | ❌ | `BAAI/bge-large-zh-v1.5` | 本地/远程嵌入模型名 |
| `HF_ENDPOINT` | ❌ | `https://hf-mirror.com` | Hugging Face 镜像端点（用于本地模型国内加速下载） |


### 4.2 使用规则

- 新增配置项必须同时更新 `.env.example`
- 环境变量仅在 `main.py` / `streamlit_app.py` 入口处通过 `init_env()` 加载
- 模块代码通过 `utils.py` 的 `get_openai_client()` / `get_model_name()` 等函数间接获取配置，不直接读 `os.getenv()`
- 读取环境变量必须用 `utils.clean_env()` 去除首尾空白和引号

---

## 五、错误处理规范

### 5.1 分层策略

| 场景 | 处理方式 |
|------|---------|
| 输入验证失败 | `raise ValueError("消息")` |
| 操作条件不满足 | `raise RuntimeError("消息")` |
| 外部 API 调用失败 | 捕获 → 日志警告 → 返回安全回退值 |
| 解析 JSON 失败 | 捕获 → 日志警告 → 返回默认结构 |

### 5.2 系统信号保护

任何捕获宽泛异常的地方，必须先重新抛出系统信号：

```python
except Exception as e:
    if isinstance(e, (KeyboardInterrupt, SystemExit)):
        raise
    logger.warning("操作失败: %s", e)
    return fallback_value
```

### 5.3 异常链

重新抛出新异常时使用 `raise ... from exc` 保留原始堆栈：

```python
try:
    ...
except OpenAIError as exc:
    raise RuntimeError("LLM 调用失败") from exc
```

---

## 六、日志规范

- 所有模块通过 `utils.get_logger(__name__)` 获取 logger
- 日志格式：`[LEVEL] name: message`
- 级别选择：

| 场景 | 级别 |
|------|------|
| 正常流程、进度计数 | `INFO` |
| 可恢复问题（重试、回退） | `WARNING` |
| 不可恢复错误 | `ERROR` |

- 不使用 `DEBUG` 级别（当前项目无调试日志需求）
- 禁止使用 `print()` 输出日志信息

---

## 七、返回值规范

### 7.1 数据结构

本项目不使用 Pydantic/dataclass。所有函数返回以下类型之一：
- 简单类型：`str`, `int`, `bool`, `None`
- `dict` — 字典键名全小写 `snake_case` 字符串
- `list[dict]` — 同类字典的列表
- `tuple[X, Y]` — 仅在极少数情况下（如 `_parse_front_matter`）

### 7.2 关键字典结构（修改时保持兼容）

```python
# ingest 输出
{"source": str, "path": str, "text": str, "fm_meta": dict}

# chunk 输出
{"text": str, "char_start": int, "char_end": int}

# process_documents 输出
{"id": str, "text": str, "metadata": {
    "source": str, "path": str, "chunk_id": int,
    "char_start": int, "char_end": int,
    "author": str|None, "year": int|None,
    "category": str, "language": str, "summary": str
}}

# VectorStore.search 输出
{"text": str, "source": str, "metadata": dict, "score": float}

# parse_query 输出
{"search_query": str, "filters": dict|None, "raw_filters": dict}
```

---

## 八、测试规范

### 8.1 测试结构

- 测试文件命名：`tests/test_<模块名>.py`
- 测试函数命名：`test_<功能描述>` (snake_case)
- 测试类命名：`Test<功能描述>` (PascalCase)
- 共享 fixtures 放在 `tests/conftest.py`

### 8.2 Mock 规范

使用 `unittest.mock.patch` 装饰器，不使用 `pytest-mock` 插件：

```python
@patch("src.qa.get_model_name", return_value="gpt-4o-mini")
def test_generate_answer(mock_model):
    ...
```

### 8.3 覆盖要求

- 每个公开函数至少有一个正常路径测试
- 每个回退/降级路径必须测试
- 集成测试放在 `test_integration.py`，覆盖多模块串联路径

### 8.4 运行

```bash
python -m pytest tests/ -v
```

---

## 九、修改操作规范

### 9.1 添加新功能

1. 确定功能属于哪个模块（参见第三章架构约束）
2. 如果跨模块，优先在现有模块中扩展，而非新建模块
3. 新公开函数必须：
   - 添加类型标注
   - 添加中文文档字符串
   - 添加至少一个测试
4. 新增依赖需同时更新 `requirements.txt`
5. 新增环境变量需同时更新 `.env.example` 和 `utils.py`
6. 更新 `pipeline_demo.ipynb` 中的相关章节
7. 更新 `report/report.md` 中的相关描述

### 9.2 修改现有代码

1. 保持原有命名风格（snake_case, verb_noun, 中文注释）
2. 保持字典返回结构的键名不变（向后兼容）
3. 修改函数签名时，新增参数必须有默认值
4. 修改后运行全量测试确保不破坏已有功能：

```bash
python -m pytest tests/ -v
```

### 9.3 不要做的事（反模式）

| 反模式 | 说明 |
|--------|------|
| 上帝脚本 | 不要把代码塞进一个文件；保持模块化 |
| 硬编码路径 | 禁止 `C:/Users/xxx/data.csv`；用 `BASE_DIR` 推导 |
| `print()` 替代日志 | 用 `logger.info()` |
| 忽略异常 | 必须 at least 打日志 |
| 静默吞异常 | 即使回退也要 `logger.warning()` |
| 修改字典键名 | 下游模块依赖现有键名 |
| 在 `utils.py` 中加业务逻辑 | 它只是工具层 |
| 新增 `.env` 变量不更新 `.env.example` | 队友跑不起来 |

---

## 十、Git 提交规范

### 10.1 提交信息格式

```
<类型>: <简短描述（中文）>

<详细说明（可选）>
```

### 10.2 类型标签

| 标签 | 含义 |
|------|------|
| `feat` | 新功能 |
| `fix` | 错误修复 |
| `refactor` | 重构（不改变行为） |
| `test` | 添加或修改测试 |
| `docs` | 文档修改 |
| `chore` | 杂项（依赖更新、配置等） |

### 10.3 示例

```
feat: 添加 max_distance 阈值过滤支持

embed_store.py 的 search() 新增 max_distance 参数，仅返回余弦距离不超过上限的结果。
```

---

## 十一、依赖清单

```txt
openai>=1.0.0                 # OpenAI API 客户端
chromadb>=0.4.0               # 向量数据库
python-dotenv>=1.0.0          # .env 加载
streamlit>=1.28.0             # Web 界面
PyMuPDF>=1.23.0               # PDF 解析
pyyaml>=6.0                   # Front-Matter 解析
pytest>=8.0                   # 测试框架
sentence-transformers>=2.2.0  # 本地嵌入模型
fastapi>=0.110.0              # 远程 Embedding 服务 Web 框架
uvicorn>=0.27.0               # 远程 Embedding 服务 ASGI 服务器
pydantic>=2.0.0               # 远程服务请求/响应模型
beautifulsoup4>=4.12.0        # HTML 解析（语料抓取用）
requests>=2.31.0              # HTTP 请求客户端（语料抓取用）
lxml>=4.9.0                   # 高效 XML/HTML 解析引擎
html2text>=2020.1.16          # 将 HTML 网页转换为干净的 Markdown 文本
pysocks>=1.7.1                # SOCKS5 代理支持
python-pptx>=0.6.21           # PowerPoint (.pptx) 文档生成工具
fpdf2>=2.7.0                  # PDF 文档生成工具
torch>=2.0.0                  # 本地深度学习框架（本地 Embedding 支持）
```

---

## 十二、快速参考卡片

```
新功能 Checklist:
□ 归属哪个现有模块？
□ 类型标注 + 文档字符串？
□ 测试写了吗？
□ pytest tests/ -v 跑过了吗？
□ .env.example 要更新吗？
□ requirements.txt 要更新吗？
□ pipeline_demo.ipynb 要更新吗？
□ report/report.md 要更新吗？

修改 Checklist:
□ 保持原有命名/字典结构/导入顺序了吗？
□ 新增参数有默认值吗？
□ pytest tests/ -v 全部通过了吗？
```
