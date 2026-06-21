# 📚 课程知识库 RAG 助手

> 基于检索增强生成（RAG）的智能问答系统 | 大数据学期项目 — 方向 B

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-108%20passed-green.svg)](https://github.com/liwe123/Date-Analysis-Fanal-Exem)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![GPU](https://img.shields.io/badge/GPU-CUDA%2012.4-brightgreen.svg)](https://pytorch.org/)

---

## ✨ 特性

- **RAG 全流水线**：文档摄取 → 清洗分块 → 向量索引 → 混合检索 → LLM 答案生成 + 引用追溯。
- **算力云端卸载**：支持 **remote 远程 GPU 嵌入模式**，一键在租用的 AutoDL **RTX 4090（24GB）** 云服务器上通过 FastAPI 部署高性能 `BAAI/bge-large-zh-v1.5`（1024 维）模型。本项目的大规模数据已完成清洗、分块与向量化，并落入本地 ChromaDB 持久化结果；本地 GTX 1660 SUPER 显存不足时，可将批量 Embedding 推理卸载到云端 4090，保留本地 ETL 与向量库写入流程。
- **混合检索**：向量语义搜索 + 显式多键复合过滤器（ChromaDB 复合 where 兼容格式自动转换）。
- **AI 查询解析**：大模型自然语言自动分类并提取语义搜索词与 filters 元数据过滤条件（年份/分类/作者/语言）。
- **高鲁棒性预处理**：32 线程并发调用 LLM 提取元数据，遇到 API 高频 429 限流时自动进行带随机抖动的指数退避重试，极短有效文本自动兜底。
- **双端入口**：现代化 Streamlit Web 界面（来源追溯、响应式布局、安全 Markdown 渲染与按模式控制的写入网关） + CLI 命令行。
- **自动采集**：Wikipedia + Stack Overflow + CSDN 三源自动采集，BeautifulSoup 抓取 + html2text 极致过滤 90% 以上网页噪声，仅保留纯净 Markdown 语法。
- **自动化测试**：**108 个自动化测试用例**，覆盖检索回退、安全渲染和前端关键路径；离线测试无需真实 API 密钥，用例通过率 100%。
- **答辩保姆级支撑礼包**：附带团队 4 人任务分工报告 PDF、面向小白组员的项目架构与傻瓜式操作指南 PDF、评委高频提问防守卡片盒 PDF 以及 15 分钟现场演示逐字解说词。

---

## 🏗️ 架构

```
本地 ETL (src/ingest.py, preprocess.py) ──(切分 120万块)──> 批量打包 (batch_size=256)
                                                                 │
                                                                 ↓ (HTTP POST 并发卸载)
ChromaDB 本地向量库 <──(写入 1024维向量)── 本地 embed_store.py <── AutoDL 4090 GPU (FastAPI + Token)

                                       ↓

用户提问 ──> query_parser.py ──> VectorStore.search() ──> qa.py (防幻觉约束) ──> Streamlit 前台 (流式字元)
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

> **GPU 加速**：如需本地 CUDA 加速，可安装本地版 PyTorch
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu124
> ```

### 2. 算力云端卸载部署 (AutoDL RTX 4090)

1. **上传部署脚本**到租用的 AutoDL 实例：
   ```bash
   scp -P <端口> scripts/embedding_server.py scripts/setup_autodl.sh root@<AutoDL公网IP>:~/
   ```
2. **SSH 登录服务器一键拉起服务**：
   ```bash
   chmod +x setup_autodl.sh
   EMBEDDING_SERVER_TOKEN=<自定义访问令牌> bash setup_autodl.sh
   ```
3. **本地 `.env` 配置文件配置**：
   ```bash
   cp .env.example .env   # 填入授权密钥并开启云端算力卸载
   ```
   ```env
   OPENAI_API_KEY=sk-xxxx...
   OPENAI_EMBEDDING_MODEL=remote
   OPENAI_EMBEDDING_BASE_URL=https://<AutoDL分配的高速公网网址>/v1
   EMBEDDING_SERVER_TOKEN=<与云端服务一致的访问令牌>
   ```
   AutoDL 自定义服务通常是公网地址，建议在云端和本地同时配置
   `EMBEDDING_SERVER_TOKEN`，避免他人直接消耗你的 GPU 推理资源。

### 3. 一键建立向量索引

```bash
# 语料抓取采集（Wikipedia、CSDN、SO三源自动采集）
python src/main.py collect-all

# 云端算力卸载批量向量建库
python -m src.main build --metadata-strategy jsonl_only
```

### 4. 运行问答与 Web 界面

```bash
# 单次提问
python src/main.py ask --question "大数据学期项目的截止日期和提交要求是什么？"

# 极速一键拉起 Streamlit Web 前台
streamlit run app/streamlit_app.py

# 生成临时的 trycloudflare.com 公网演示地址
powershell -ExecutionPolicy Bypass -File scripts/start_public_streamlit.ps1
```

Cloudflare Quick Tunnel 地址会在每次启动时变化，且依赖本机 Streamlit、网络和
`cloudflared` 进程持续运行。固定域名需要配置 Named Tunnel 与 Cloudflare DNS。

---

## 🧪 自动化测试

```bash
python -m pytest tests/ -v
```

| 模块 | 测试数 | 覆盖细节 |
|------|--------|------|
| `preprocess` | 28 | 数据清洗标签去除、语义分块、Front-Matter 合并、JSON 安全解析、策略校验与元数据提取 |
| `embed_store` | 15 | 数据库初始化、双路检索融合、max_distance 距离过滤、远程 Token、ChromaDB upsert 幂等写入 |
| `ingest` | 27 | YAML 嵌套解析、多源文本递归加载、PDF 解析、JSONL 专用摄取与异常数据跳过 |
| `qa` | 11 | 上下文生成、引用补全、故障类型区分、异常链抛出与 KeyboardInterrupt 保护 |
| `query_parser` | 6 | 正常意图解析、空过滤降级、Markdown 过滤、API 异常与 JSON 格式错误兜底 |
| `integration` | 4 | 摄取→清洗预处理集成、语义搜索→大模型问答全链路端到端集成测试 |
| `app.rendering` | 5 | 安全 Markdown、表格渲染、HTML 转义与受控换行 |
| `retrieval_fallback` | 12 | SQLite/原始语料回退、Token 配额分流、领域词排序与快速统计 |

---

## 🛠️ 技术栈

| 组件 | 选用技术 |
|------|------|
| 大语言模型 | DeepSeek V4-flash / GPT-4o-mini (OpenAI-compatible API) |
| 特征向量模型 | BAAI/bge-large-zh-v1.5（通过 FastAPI 在 AutoDL 4090 GPU 上高吞吐推理） |
| 向量数据库 | ChromaDB (HNSW 索引，upsert 幂等去重，SQLite 元数据存储) |
| 文本流处理 | PyMuPDF (PDF 解析) + BeautifulSoup (HTML标签剥离) + html2text (Markdown转换) |
| 前端交互 | Streamlit (高级视觉， session_state 记忆，开发者调试看板，安全转义网关) |
| 单元测试 | Pytest (108 个用例，100% 通过) |

---

## 📁 项目结构

```
├── app/streamlit_app.py     # Streamlit Web 前端网页
├── src/
│   ├── main.py              # 核心命令行接口 CLI (build / ask / collect)
│   ├── collect_corpus.py    # Wikipedia 语料采集脚本
│   ├── collect_more_corpus.py # Wikipedia 补充语料采集 (解耦重构)
│   ├── collect_stackoverflow.py # Stack Overflow 问答采集 (带翻译)
│   ├── collect_csdn.py      # CSDN 博客采集
│   ├── ingest.py            # 文档读取解析 (md/txt/pdf)
│   ├── preprocess.py        # 清洗、四级语义分块、元数据并发提取 (带极短兜底)
│   ├── embed_store.py       # ChromaDB 向量存储与混合检索 (带复合 where 转换)
│   ├── qa.py                # LLM 问答生成 (带上下文截断与Facts引用)
│   ├── query_parser.py      # 查询意图解析 (Markdown 剥离)
│   └── utils.py             # 公共工具（环境变量读取、日志规范、客户端单例）
├── tests/                   # 108 个自动化测试用例
├── scripts/
│   ├── embedding_server.py  # AutoDL 远程 FastAPI 向量推理服务
│   ├── setup_autodl.sh      # AutoDL 远程一键部署环境脚本
│   ├── generate_task_division_pdf.py # 团队任务分工 PDF 自动生成脚本
│   ├── generate_defense_qa_pdf.py    # 答辩防守卡片盒 PDF 自动生成脚本
│   └── generate_onboarding_pdf.py    # 零基础小白组员架构与操作 PDF 自动生成脚本
├── data/raw/                # 原始文档 + Wikipedia/CSDN/SO 自动采集语料 (176 篇)
├── vector_store/            # 本地 ChromaDB SQLite/Parquet 持久化物理目录
├── report/
│   ├── report_ieee.html     # 精美 6 页 IEEETransactions 双栏双语论文报告
│   ├── task_division.md     # 团队成员任务分工说明文档
│   ├── task_division.pdf    # 自动编译的高清团队分工 PDF
│   ├── defense_qa_guide.md  # 评委提问应对与完美解答求生指南
│   ├── defense_qa_guide.pdf # 自动编译的高清答辩防守 PDF卡片盒 (7页)
│   ├── member_onboarding_guide.md # 零基础小白组员架构、目录与现场操作保姆级指南
│   ├── member_onboarding_guide.pdf # 自动编译的 5 页小白操作 PDF 指南 (左右防溢出)
│   └── presentation_guide.md # 15 分钟现场演示说服解说词及容灾备用方案
├── pipeline_demo.ipynb      # Jupyter Notebook 演示
└── requirements.txt
```

---

## 📖 支撑文档链接

- **双栏学术论文**：[report/report_ieee.html](./report/report_ieee.html) (IEEE 双栏紧凑，AutoDL 卸载架构)
- **小白求生指南**：[report/defense_qa_guide.md](./report/defense_qa_guide.md) (提问防守卡片盒) -> [高清 PDF](./report/defense_qa_guide.pdf)
- **小白操作指南**：[report/member_onboarding_guide.md](./report/member_onboarding_guide.md) (目录/命令/演示) -> [高清 PDF](./report/member_onboarding_guide.pdf)
- **团队任务分工**：[report/task_division.md](./report/task_division.md) (任务划分与单测映射) -> [高清 PDF](./report/task_division.pdf)
- **演示说服指南**：[report/presentation_guide.md](./report/presentation_guide.md) (15分钟甘特图与逐字演示解说词)
- **Jupyter 演示**：[pipeline_demo.ipynb](./pipeline_demo.ipynb)
- **开发规范**：[AGENTS.md](./AGENTS.md)

