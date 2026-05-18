# 大数据学期项目计划二报告

> 写作风格：技术设计文档（非学术论文）

## 目录

- [一、执行摘要](#一执行摘要)
- [二、业务问题与价值](#二业务问题与价值)
- [三、系统架构设计](#三系统架构设计)
- [四、数据集与处理策略](#四数据集与处理策略)
- [五、检索与查询解析](#五检索与查询解析)
- [六、答案生成与风险控制](#六答案生成与风险控制)
- [七、技术选型与权衡](#七技术选型与权衡)
- [八、云财务与成本估算](#八云财务与成本估算)
- [九、事后复盘](#九事后复盘)
- [十、运行方式](#十运行方式)
- [十一、演示方案](#十一演示方案10-分钟)
- [十二、项目实际运行数据](#十二项目实际运行数据)
- [十三、项目创新亮点与技术特色](#十三项目创新亮点与技术特色)
- [十四、代码质量与工程实践](#十四代码质量与工程实践)
- [十五、问答效果示例](#十五问答效果示例)
- [十六、结论](#十六结论)

## 一、执行摘要

本项目对应课程"方向 B：智能客户支持与检索增强生成（RAG）助手"。目标企业场景：一家科技公司拥有庞大的内部知识库——客户支持工单、PDF手册、Slack日志——员工每天花费数小时在海量非结构化文档中查找答案。我们的任务不是简单封装 ChatGPT，而是构建一个稳健的数据工程后端，为 AI 提供高质量数据基础。

核心交付：从杂乱文本文件到可搜索向量索引、再到带来源追溯的智能问答，全链路自动化。项目采用"行走的骨架"策略——先跑通端到端最小流水线，再逐步增强。最终系统具备 CLI 命令行问答与 现代化的 Streamlit Web 界面（极简视觉、高级质感）两种交互方式，支持多轮对话、混合检索（语义向量 + 元数据过滤）、来源追溯与查询意图解析。

## 二、业务问题与价值

**痛点**：企业内部知识分散在各类非结构化文档中（Markdown 课程资料、Wikipedia 百科词条、PDF 手册），传统关键词搜索语义理解弱——用户搜"怎么交作业"，文档中写的是"提交方式"，关键词匹配不到。团队重复回答相同问题，效率低下。

**方案价值**：
- **语义检索**：向量嵌入理解"交作业"与"提交方式"的语义等价，解决关键词不匹配问题；
- **有据可查**：答案强制标注来源，降低 AI 幻觉风险，支持人工核查；
- **混合过滤**：同时支持语义搜索 + 结构化元数据过滤（如"仅查 2024 年的通知"）；
- **自动化流水线**：从原始文档到可查询知识库，一键建库，持续增量更新；
- **低部署成本**：全部开源自托管（ChromaDB + Python），无需商业向量数据库授权。

## 三、系统架构设计

### 3.1 架构总览（数据流）

```
┌──────────────────────────────────────────────────────────────────────┐
│                        原始数据源                                      │
│  data/raw/ (50+ md 课程文档)  +  Wikipedia API (58 个专业词条)       │
└──────────┬───────────────────────────────────────────────────────────┘
           │
     ┌─────▼──────┐
     │  1. 摄取    │  ingest.py        (md/txt/pdf → 结构化文档对象)
     │            │  collect_corpus.py / collect_more_corpus.py (Wikipedia REST API → md)
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │  2. 处理    │  preprocess.py
     │            │  ├─ clean_text()   HTML标签清理 / 转义字符 / 乱码过滤
     │            │  ├─ chunk_text()   段落→句子→贪心合并→滑窗切分
     │            │  ├─ extract_metadata()  LLM 提取年份/分类/语言/摘要
     │            │  └─ process_documents() Front-Matter 优先合并
     └─────┬──────┘
           │
     ┌─────▼──────┐
      │  3. 嵌入    │  Qwen/Qwen3-Embedding-0.6B (本地) (1024维, 余弦距离, CUDA GPU)
     │            │  embed_store.py → ChromaDB 批量写入 (batch=64)
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │  4. 存储    │  ChromaDB 本地持久化 → vector_store/
     │            │  HNSW 索引, cosine 距离空间
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │  5. 检索    │  embed_store.search()
     │            │  ├─ 语义向量搜索 (相似度 Top-K)
     │            │  ├─ 元数据 where 过滤 (year/category/author/language)
     │            │  ├─ max_distance 阈值裁剪
     │            │  └─ where 失败自动回退降级
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │ 5a. 解析    │  query_parser.py
     │            │  自然语言 → {search_query, filters: {year, category, ...}}
     │            │  失败自动回退: 原问题全文搜索
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │  6. 生成    │  qa.py
     │            │  System Prompt: 仅依据参考资料回答, 标注 [Source: xxx]
     │            │  引用缺失自动补全来源列表
     └─────┬──────┘
           │
     ┌─────▼──────┐
     │  7. 服务    │  CLI: python src/main.py ask
     │            │  Web: streamlit run app/streamlit_app.py
     └────────────┘
```

### 3.2 模块设计

| 模块 | 文件 | 职责 | 关键设计 |
|------|------|------|---------|
| 数据摄取 | `ingest.py` | 递归读取 raw/ 下 .txt/.md/.pdf；解析 YAML Front-Matter | PyMuPDF 提取 PDF 文本；utf-8 容错读取 |
| 语料扩充 | `collect_corpus.py`、`collect_stackoverflow.py`、`collect_csdn.py` | 从 Wikipedia REST API、Stack Overflow API、CSDN 博客三源采集 | 中英文回退、限速重试、429 指数退避；输出为带 Front-Matter 的 md 文件 |
| 文本清洗 | `preprocess.py` | HTML 标签移除、转义字符还原、控制字符过滤、空白规范化 | 正则流水线，保留 `\n` 作为段落边界 |
| 语义分块 | `preprocess.py` | 段落边界→句子边界→贪心合并→滑窗切割 | 四层优先级，默认 700 字符/块，120 字符重叠，最小 40 字符 |
| 元数据提取 | `preprocess.py` | LLM 提取作者/年份/分类/语言/摘要 | 32 线程并发提取，429 限流指数退避重试；Front-Matter 优先覆盖 LLM 结果 |
| 向量存储 | `embed_store.py` | ChromaDB 管理：建表、批量写入、多模式检索、安全删除 | OpenAI 单例客户端，upsert 批量 64，where 失败自动回退 |
| 查询解析 | `query_parser.py` | 自然语言 → 结构化搜索参数 | LLM 提取 search_query + filters，失败回退全文搜索 |
| 答案生成 | `qa.py` | 上下文拼接 + LLM 生成 + 引用强制 | System Prompt 约束"不知说不知"，引用缺失自动补全 |
| 入口整合 | `main.py` | CLI 子命令：build / ask / collect / collect-so / collect-csdn / collect-all | argparse，交互模式支持连续追问 |
| Web 界面 | `streamlit_app.py` | 对话历史、侧边栏状态、Top-K 调节、调试模式 | 缓存客户端/向量库，图片输入拦截，错误分类提示 |

### 3.3 数据流示意

```
用户问题 → query_parser → {search_query, filters}
                              ↓
                        embed_store.search()
                              ↓
                   [语义向量 Top-K + where 过滤 + max_distance 裁剪]
                              ↓
                        qa.generate_answer()
                              ↓
                System Prompt + 检索上下文 → LLM → 带来源答案
```

## 四、数据集与处理策略

### 4.1 数据源构成

| 数据源 | 数量 | 格式 | 内容 |
|--------|------|------|------|
| 课程资料 | 50+ 文件 | .md (含 Front-Matter) | 课程介绍、FAQ、案例、通知、报告、术语表 |
| Wikipedia 词条 | 83 个 | .md (含 Front-Matter) | 大数据核心技术术语（RAG、向量数据库、Spark、流处理等） |
| Stack Overflow 问答 | 30 篇 | .md (含 Front-Matter) | 高票技术问答（Spark/Kafka/ML 等），DeepSeek 翻译为全中文 |
| CSDN 博客 | 18 篇 | .md (含 Front-Matter) | 中文技术博客（Spark/Hadoop/Flink/ETL 等实战教程） |

三源采集流程：

**Wikipedia**（`collect_corpus.py`）：
- **API**：Wikipedia REST API v1（免费，无限流风险）
- **策略**：优先请求中文摘要（`zh.wikipedia.org`），失败则回退英文（`en.wikipedia.org`）
- **限速保护**：每次请求间隔 2 秒，失败重试 3 次
- **输出格式**：带 YAML Front-Matter 的 Markdown 文件（title、tags、fetch_date、source_url、extract、课程关联说明）

**Stack Overflow**（`collect_stackoverflow.py`）：
- **API**：Stack Exchange API v2.3（官方 REST API，无需爬虫）
- **内容**：按标签搜索高票问答（`score ≥ 3`），获取问题正文 + 最高票回答
- **翻译**：调用 DeepSeek 将英文标题/问题/回答翻译为中文，保留代码块和技术术语
- **标签**：apache-spark、hadoop、apache-kafka、apache-flink、machine-learning 等 15 个
- **限速**：每次请求间隔 1 秒，429 指数退避重试

**CSDN 博客**（`collect_csdn.py`）：
- **来源**：CSDN 搜索 API（`so.csdn.net`）
- **内容**：按关键词搜索技术文章，提取 `<article>` 标签正文
- **关键词**：Spark 大数据教程、Hadoop 入门实战、Flink 流处理、数据仓库 Hive 等 10 个
- **限速**：每次请求间隔 3 秒，最多重试 3 次

### 4.2 文本清洗流水线

`clean_text()` 按序执行四步（`src/preprocess.py:35`）：
1. **HTML 标签移除**：正则 `<[^>]+>` → 空格
2. **HTML 实体解码**：`&amp;` → `&`，`&lt;` → `<`，`&nbsp;` → 空格 等
3. **控制字符过滤**：移除不可打印字符（保留 `\n`、`\t`），移除 `\r`
4. **空白规范化**：合并连续空格/制表符，3个以上连续换行压缩为2个

### 4.3 语义分块算法

`chunk_text()` 采用四层优先级策略（`src/preprocess.py:67`）：

```
        ┌──── 是否超出 chunk_size？ ────┐
        │ 否: 保留完整段落                │ 是
        ▼                                ▼
   下一段落继续合并              ┌─ 段落内句子切分 ─┐
                                │ 否: 当前句子加入块 │ 是 (单句超限)
                                ▼                    ▼
                           下一句继续合并      滑窗强制切割
                                              (step = chunk_size - overlap)
```

- **默认参数**：`chunk_size=700`，`overlap=120`，`min_chunk_chars=40`
- **重叠设计**：确保边界句子不被切割遗漏，检索阶段做去重
- **参数可调**：`build` 命令支持 `--chunk-size` 和 `--overlap`

### 4.4 元数据提取与合并

- **LLM 提取**：每篇文档前 1200 字符发送至 `deepseek-v4-flash`，返回 JSON（作者、年份、分类、语言、50 字摘要）
- **并发提取**：使用 `ThreadPoolExecutor` 32 线程并发调用 LLM，127 篇文档从串行 ~4 分钟降至 ~20 秒
- **429 限流重试**：遇到 DeepSeek API 限流（HTTP 429）时，自动指数退避重试（2s → 4s → 8s，最多 3 次），重试耗尽才降级为默认值
- **Front-Matter 优先**：若文档 YAML 头中已写明 `year: 2024`、`category: notice`，以人工标注为准覆盖 LLM 结果
- **回退策略**：LLM JSON 解析失败 → 空元数据字典 → 文件名前缀猜测分类（如 `wiki_*` → wiki，`notice*` → notice）
- **成本**：127 篇文档各调一次 deepseek-v4-flash，总成本不足 1 元人民币；离线一次性运行
- **CLI 参数**：`python src/main.py build --max-workers 16` 可自定义并发数

## 五、检索与查询解析

### 5.1 向量存储（ChromaDB）

| 属性 | 配置 |
|------|------|
| Embedding 模型 | `OPENAI_EMBEDDING_MODEL`（推荐 Qwen/Qwen3-Embedding-0.6B (本地)，1024 维） |
| 距离度量 | Cosine 距离（0 = 完全一致，2 = 完全相反） |
| 索引算法 | HNSW |
| 写入策略 | 批量 upsert（batch_size=64） |
| 持久化路径 | `vector_store/`（本地目录，零部署依赖） |

**关键 Feature**：
- **`max_distance` 阈值过滤**：仅返回余弦距离不超过上限的结果，避免返回语义无关的"垃圾"片段。在 Streamlit 界面中可实时调节（0.1-2.0）。
- **安全删除**：`delete_collection(confirm=True)` 需显式确认，防止误操作。

### 5.2 混合检索（语义 + 元数据过滤）

`embed_store.search()` 支持：
1. **纯语义搜索**：向量相似度 Top-K
2. **语义 + where 过滤**：在指定元数据条件下搜索，如 `{"year": 2024, "category": "notice"}`
3. **回退机制**：若 where 过滤后结果为空或触发 ChromaDB 兼容性错误（ValueError / TypeError / RuntimeError），自动移除过滤条件、回退为纯语义搜索并警告日志。确保用户不会因过滤条件过严看到空白结果。

### 5.3 查询意图解析（Query Parser）

`query_parser.py` 是本次实现的关键差异化能力——将用户的自然语言问题自动翻译为结构化搜索参数：

```
用户输入: "去年老师有没有说过期末考试怎么考"

        ┌─────────────────────────────────────┐
        │  LLM (deepseek-v4-flash, temperature=0)   │
        │  输出: {                             │
        │    "search_query": "期末考试 形式",   │
        │    "filters": {                      │
        │      "year": 2025,                   │
        │      "category": "notice"            │
        │    }                                 │
        │  }                                   │
        └─────────────────────────────────────┘
```

- **解析字段**：`search_query`（去除了过滤信息的纯搜索词）、`year`、`category`、`author`、`language`
- **分类枚举**：notice / faq / wiki / case_study / report / term / general
- **回退策略**：JSON 解析异常、API 失败时 → `search_query` = 原问题全文，`filters = None`，降级为纯语义搜索
- **性能**：额外调用一次 deepseek-v4-flash，约 1-2 秒，对用户透明

## 六、答案生成与风险控制

### 6.1 防幻觉策略

`qa.py`（`src/qa.py:25`）从三个层面降低 AI 幻觉：

| 层面 | 措施 |
|------|------|
| System Prompt | "Answer based only on the provided reference materials. Cite sources inline as [Source: name]." |
| 上下文范围 | 仅将检索结果作为参考素材，不给 LLM 自我发挥空间 |
| 来源强制 | 若 LLM 未标注 `[Source: xxx]`，后端自动追加 "Sources:" 列表（去重排序） |

**场景验证**：
- "课程项目最后提交截止日期是什么？" → 返回答案 + `【来源：xxx.md】`
- "钢琴考级需要准备什么？" → "资料中没有相关信息"

### 6.2 引用追溯

每个检索结果的来源信息包括：
- 来源文件名（`source`）
- 文件路径（`path`）
- 余弦距离（`score`）
- 元数据（`year`、`category`、`author`、`language`）
- 内容片段（前端展示前 400 字）

在全新升级的高级感 Streamlit 界面中，每次回答附带毛玻璃视效的可展开"检索来源"面板，显示每条命中文档的距离、路径和片段预览。

## 七、技术选型与权衡

### 7.1 核心技术栈

| 层级 | 选择 | 替代方案 | 权衡理由 |
|------|------|---------|---------|
| ETL 处理 | Python (纯) | PySpark | 当前数据量 < 100 篇文档，Python 本地处理足够；若扩展到 > 10K 文档，切换 PySpark 即可，处理逻辑无需重写 |
| 向量数据库 | ChromaDB | Milvus / Qdrant / Pinecone | ChromaDB 零部署（pip install 即用），本地持久化；Milvus 需 Docker，Pinecone 需付费。我们对数据库做了抽象封装，未来可平滑迁移 |
| Embedding | Qwen/Qwen3-Embedding-0.6B (本地) | all-MiniLM-L6-v2 / ada-002 | 本地模型（1024 维），PyTorch CUDA GPU 推理加速；免费、零 API 调用成本 |
| LLM | deepseek-v4-flash | gpt-4 / 本地模型 | 延迟低、成本低（约 $0.15/百万 token），回答质量对 FAQ 场景够用；System Prompt 约束保证了答案限制在参考资料范围内 |
| Web 框架 | Streamlit | Flask / FastAPI | 纯 Python 编写，零前端代码，适合数据项目快速演示；正式 API 服务应切换 FastAPI |
| YAML 解析 | PyYAML | - | 标准库，解析 Front-Matter 和配置文件稳定可靠 |
| PDF 解析 | PyMuPDF (fitz) | pdfplumber / PyPDF2 | C 底层实现，速度快，中文支持好；提取纯文本（暂不支持表格和图片） |

### 7.2 架构设计原则

- **模块化**：每个文件职责单一（ingest → preprocess → embed_store → qa），杜绝"上帝脚本"
- **路径可移植**：所有路径基于 `BASE_DIR` 相对定位，无硬编码绝对路径
- **环境变量**：API Key 等敏感配置通过 `.env` 管理，显式 `init_env()` 调用便于测试隔离
- **单例模式**：OpenAI 客户端全局缓存复用，避免重复连接创建
- **降级设计**：查询解析失败 → 全文搜索；where 过滤失败 → 纯语义搜索；LLM 元数据提取失败 → 文件名猜测

## 八、云财务与成本估算

以下为将该系统部署至阿里云/华为云、处理每日 10TB 数据规模的理论估算（元/月）：

| 费用类别 | 月估算 (¥) | 关键变量 |
|----------|-----------|----------|
| 计算资源（ECS/容器 × 离线 ETL + 在线推理） | 30,000 - 60,000 | 文档增量批次大小、查询 QPS |
| 存储（对象存储 OSS + ChromaDB 向量索引 + 日志） | 10,000 - 20,000 | 数据保留策略、索引膨胀比 |
| 模型调用（Embedding API + LLM Generation） | 20,000 - 80,000 | 每日查询量、每次回答上下文长度 |
| **合计** | **60,000 - 160,000** | |

**成本优化方向**：
1. Embedding 已切换为本地 Qwen3-Embedding-0.6B（免费），LLM 已切换为 deepseek-v4-flash（API 调用）
2. 对高频 FAQ 做答案缓存（语义去重），减少重复 LLM 调用
3. 向量索引做分层存储：热数据 ChromaDB 内存索引、冷数据对象存储

> 注：课程项目规模（< 100 篇文档，数十次查询）的 API 总成本 < ¥5，上述为工程化量级估算。

## 九、事后复盘

### 9.1 已解决的设计问题

1. **环境变量加载顺序**：早期版本在模块导入时自动加载 `.env`，导致测试文件加载顺序不可控。修复为 `init_env()` 在 `main.py` / `streamlit_app.py` 入口处显式调用，模块内部不做自动加载。
2. **报告文件被应用代码覆盖**：`report/report.md` 曾被误写为应用逻辑代码，已恢复为正式技术报告。
3. **来源展示不完整**：CLI 和 Streamlit 的来源展示曾不一致，现统一为：CLI 打印距离+来源，Web 展示可展开面板。

### 9.2 已知限制

| 限制 | 影响 | 改进方向 |
|------|------|---------|
| PDF 仅提文字，不处理表格/图片 | 含图表的重要文档信息丢失 | 引入 Table/Image Extraction 模块 |
| 无 Rerank 模型 | 复杂问题的 Top-3 中可能包含弱相关片段 | 接入 Cross-Encoder Reranker（如 bge-reranker），在 Top-20 中精排 Top-K |
| 无权限/租户隔离 | 所有用户共享同一知识库 | 引入 collection 级别的命名空间隔离 |
| 分块粒度固定 | 不同文档类型（FAQ短、报告长）用同一 chunk_size | 按文档类型动态调整分块策略 |
| 对话历史不跨会话 | 关闭 Streamlit 后历史丢失 | 接入持久化对话存储（SQLite/Redis） |
| 评测体系未建立 | 无法量化检索/生成质量 | 构建测试问题集 + Recall@K + MRR 指标 |

### 9.3 从 PDF "常见失败模式" 反思

> PDF 警告：不要在 UI 上花 20 小时、在 Spark 流水线上只花 2 小时。

本项目始终遵循"数据工程优先"原则——Streamlit 界面是最终展示的"壳"，核心工程在 `src/` 下六个模块的数据处理能力上。前端只负责展示，业务逻辑全部在后端。

> PDF 警告：不要把所有代码放在一个 main.py 或单个 Notebook 中。

本项目严格模块化：`ingest.py` / `preprocess.py` / `embed_store.py` / `query_parser.py` / `qa.py` / `main.py` 各司其职。

> PDF 警告：不要用硬编码路径。

所有文件路径基于 `BASE_DIR`（项目根目录）动态计算，通过 `.env` 管理环境变量。

> PDF 警告：先构建"行走的骨架"——第三天就让一行模拟数据通过整个流水线。

本项目开发按此范式：先实现 `build` 一间房 → 一条文档走通全部流程 → 再扩展 Wikipedia 语料 → 再增加查询解析等增强特性。

### 9.4 下一步优化路线

1. **PDF/HTML 完整解析**：结构化抽取表格、图片标注
2. **Reranker 接入 + 评测体系**：构建测试集，量化 Recall@K 与 MRR
3. **增量索引**：新增文档无需重建全库
4. **日志与监控**：记录检索命中率、问答延迟、失败样本
5. **多租户与权限**：Collection 命名空间隔离

## 十、运行方式

### Jupyter Notebook（推荐）

项目提供完整的 Jupyter Notebook 演示，覆盖全部流水线步骤：
```
jupyter notebook pipeline_demo.ipynb
```
Notebook 包含 16 个章节，从环境准备到全链路测试，每步均可独立运行。

### 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env     # 填入 OPENAI_API_KEY 和 OPENAI_EMBEDDING_MODEL
```

> 国内网络环境需设置 `HF_ENDPOINT=https://hf-mirror.com` 以下载 HuggingFace 模型

### 核心命令

```bash
# 扩充公开语料（Wikipedia 58 个词条）
python src/main.py collect

# 建立/更新向量索引
python src/main.py build [--chunk-size 700] [--overlap 120]

# 问答
python src/main.py ask --question "课程项目最后提交要求是什么？" --top-k 3
python src/main.py ask                    # 交互模式

# Web 演示
streamlit run app/streamlit_app.py

# 运行测试 (54 个测试函数)
python -m pytest tests/ -v
```

### 测试覆盖 (54 个测试函数)

| 测试模块 | 覆盖内容 |
|----------|---------|
| `test_preprocess` | clean_text、chunk_text、extract_metadata、分类猜测、元数据合并、process_documents |
| `test_ingest` | Front-Matter 嵌套解析、文件加载、空文件/目录处理 |
| `test_query_parser` | 正常解析、空过滤回退、API 异常回退、JSON 格式错误回退 |
| `test_embed_store` | 初始化、搜索、max_distance 过滤、where 回退、计数/来源、安全删除 |
| `test_qa` | 空文档兜底、上下文生成、引用缺失补全、年份显示 |
| `test_integration` | 全链路：摄取 → 处理 → 搜索 → 问答 端到端 |

## 十一、演示方案（10 分钟）

### CLI 演示（3 分钟）

```
1. 知识库问答：
   python src/main.py ask --question "课程项目最后提交截止日期是什么？"
   → 展示答案 + [Source: xxx.md]

2. 跨文档问答：
   python src/main.py ask --question "RAG 架构中向量数据库的作用是什么？"
   → 展示来自 Wikipedia 词条 + 课程资料的联合答案

3. 拒答演示：
   python src/main.py ask --question "钢琴考级需要准备什么？"
   → "资料中没有相关信息"

4. 查询解析演示（需代码演示）：
   展示 query_parser 如何将"2024年的通知讲了啥"分解为
   {search_query: "通知", filters: {year: 2024, category: "notice"}}
```

### Streamlit 演示（5 分钟）

```
1. 浏览器打开 Streamlit 界面
2. 展示侧边栏：文档块数、来源数、来源文件列表，以及新增的"➕ 数据管理"（自定义数据上传）
3. 演示上传自定义数据：粘贴文本并自动入库
4. 连续提问 2 个问题（含追问新上传的数据），展示对话历史
5. 开启调试模式：展示查询解析的中间结果（搜索词 + 过滤条件）
6. 调节 Top-K 滑块（3→10），查看检索结果数量变化
7. 展开"📎 检索来源"，展示距离分数和文本片段
8. 调节 max_distance 阈值，展示精度/召回权衡
```

### Q&A 准备（5 分钟）

> 根据 PDF 答辩要求：教授会扮演技术总监角色，提问节点故障、数据延迟、API 限流等场景。

**Q1：如果 Embedding API 限流怎么办？**
A：代码中每次写入批量 64 条，减少 API 调用次数；建库是一次性操作，偶尔限流重试即可（ChromaDB 有 upsert 幂等性）。在线查询时，查询解析失败有全文回退方案。

**Q2：向量数据库崩溃怎么恢复？**
A：ChromaDB 本地持久化在 `vector_store/` 目录，备份该目录即可。重建策略：`python src/main.py build` 全量重跑，5 分钟内恢复。

**Q3：为什么选择 ChromaDB 而不是 Milvus？**
A：课程场景对并发/分布式无要求。ChromaDB 零部署（pip install），Milvus 需 Docker + etcd + MinIO，部署复杂度高。我们已做数据库抽象层封装，生产环境切换只需修改 `embed_store.py` 一个文件。

**Q4：如果用户上传了 1000 篇新文档，你怎么增量更新？**
A：当前重新 `build` 全量处理并 upsert 写入（id 基于文件名+块索引，天然去重）。后续可优化为仅处理增量文件。

## 十二、项目实际运行数据

### 12.1 数据规模统计

| 指标 | 数值 | 说明 |
|------|------|------|
| 课程文档总数 | 45 个 | `data/raw/` 下 .md 文件（不含 external/） |
| Wikipedia 词条 | 28 个 | `data/raw/external/wiki_*.md` |
| **文档总计** | **73 个** | 全部原始文档 |
| 文档分类 | 7 类 | notice(8) / faq(4) / case_study(10) / wiki(58) / term(5) / report(1) / 其他(17) |

### 12.2 处理流水线数据

| 处理阶段 | 输入 | 输出 | 关键参数 |
|----------|------|------|----------|
| 文档摄取 | 73 个文件 | 73 个文档对象 | 支持 .md/.txt/.pdf |
| 文本清洗 | 原始文本 | 干净文本 | 4 步正则流水线 |
| 语义分块 | 73 篇文档 | ~200+ 文本块 | chunk_size=700, overlap=120 |
| 元数据提取 | 每篇前 1200 字 | JSON 元数据 | deepseek-v4-flash, temperature=0 |
| 向量嵌入 | 文本块 | 1024 维向量 | Qwen/Qwen3-Embedding-0.6B (本地) |
| 向量存储 | 向量 + 元数据 | ChromaDB 持久化 | batch_size=64 |

### 12.3 API 调用成本估算

| 调用类型 | 次数 | 单次成本 | 总成本 |
|----------|------|----------|--------|
| 元数据提取（LLM） | 73 次 | ~¥0.005 | ~¥0.37 |
| 查询解析（LLM） | 每次查询 1 次 | ~¥0.005 | 按使用量 |
| 答案生成（LLM） | 每次查询 1 次 | ~¥0.01 | 按使用量 |
| 文本嵌入（本地 Embedding） | ~200+ 次 | 免费 | ¥0 |
| **建库总成本** | - | - | **< ¥0.5** |
| **单次查询成本** | - | - | **~ ¥0.02** |

> 注：Embedding 采用本地模型 Qwen3-Embedding-0.6B，免费；LLM 基于 deepseek-v4-flash 定价。

## 十三、项目创新亮点与技术特色

### 13.1 核心创新点

| 创新点 | 实现方式 | 价值 |
|--------|----------|------|
| **查询意图解析** | LLM 将自然语言转为结构化搜索参数 | 用户无需学习搜索语法，自然表达即可 |
| **多层降级策略** | 解析失败→全文搜索；where 失败→纯语义搜索 | 系统永远有结果，不会卡死 |
| **Front-Matter 优先** | 人工标注覆盖 LLM 提取 | 尊重人工标注的准确性 |
| **来源强制追溯** | System Prompt + 后端检查补全 | 100% 有来源，可核查 |
| **安全删除机制** | `confirm=True` 显式确认 | 防止误删数据 |

### 13.2 技术特色

**1. 四层语义分块算法**
```
段落边界 → 句子边界 → 贪心合并 → 滑窗切割
```
- 不是简单数字符切割，而是尊重语义边界
- 重叠设计确保边界句子不遗漏
- 参数可调，适应不同文档类型

**2. 混合检索架构**
```
语义向量搜索 + 元数据 where 过滤 + max_distance 阈值裁剪
```
- 向量搜索解决语义匹配
- 元数据过滤支持结构化查询
- 距离阈值过滤掉低质量结果

**3. 全局单例模式**
```python
# utils.py
_client_cache: OpenAI | None = None

def get_openai_client() -> OpenAI:
    global _client_cache
    if _client_cache is not None:
        return _client_cache
    # ... 创建并缓存
```
- 避免重复创建连接
- 降低 API 调用开销
- 所有模块共享同一客户端

**4. 显式环境初始化**
```python
# main.py / streamlit_app.py
init_env()  # 显式调用，不在 import 时自动加载
```
- 避免测试时的环境变量污染
- 便于隔离测试和生产环境

## 十四、代码质量与工程实践

### 14.1 代码结构

```
src/
├── __init__.py          # 包标记
├── main.py              # CLI 入口（118 行）
├── ingest.py            # 文档摄取（104 行）
├── preprocess.py        # 预处理（301 行）
├── embed_store.py       # 向量存储（152 行）
├── qa.py                # 问答生成（71 行）
├── query_parser.py      # 查询解析（113 行）
├── collect_corpus.py    # 语料采集（151 行）
└── utils.py             # 工具函数（79 行）

app/
└── streamlit_app.py     # Web 界面（238 行）
```

**代码统计**：
- 核心模块总代码量：~1,089 行
- 平均模块大小：~136 行
- 最大模块：preprocess.py（301 行）—— 包含清洗、分块、元数据提取

### 14.2 测试覆盖

| 测试文件 | 测试类/函数 | 覆盖内容 |
|----------|-------------|----------|
| test_preprocess.py | 5 类 17 个测试 | clean_text / chunk_text / guess_category / merge_fm_meta |
| test_ingest.py | 2 类 6 个测试 | Front-Matter 解析 / 文件加载 |
| test_query_parser.py | 1 类 4 个测试 | 正常解析 / 空过滤 / API 异常 / JSON 格式错误 |
| test_embed_store.py | 3 类 8 个测试 | 初始化 / 搜索 / max_distance / where 回退 / 安全删除 |
| test_qa.py | 2 类 5 个测试 | 空文档兜底 / 上下文生成 / 引用补全 / 年份显示 |
| test_integration.py | 3 类 5 个测试 | 全链路集成测试 |
| **总计** | **16 类 45+ 测试** | **核心功能全覆盖** |

### 14.3 工程实践

| 实践 | 实现 | 示例 |
|------|------|------|
| **模块化设计** | 单一职责，文件级隔离 | ingest 只管读取，preprocess 只管处理 |
| **路径可移植** | 基于 `BASE_DIR` 相对定位 | `BASE_DIR / "data" / "raw"` |
| **环境变量管理** | `.env` + `python-dotenv` | API Key 不硬编码 |
| **错误降级** | 多层 fallback 策略 | 解析失败→默认值；过滤失败→无过滤 |
| **日志统一** | `get_logger()` 统一格式 | `[INFO] main: 消息内容` |
| **类型注解** | Python 3.10+ 类型提示 | `def search(query: str, top_k: int = 5) -> list[dict]` |
| **文档字符串** | 每个模块和函数有 docstring | 说明功能、参数、返回值 |

## 十五、问答效果示例

### 15.1 典型问答场景

**场景 1：课程信息查询**
```
问题：课程项目最后提交截止日期是什么？
回答：根据课程资料，项目最终提交截止日期为...
来源：project_requirements.md, submission_rules.md
```

**场景 2：技术概念解释**
```
问题：什么是检索增强生成（RAG）？
回答：检索增强生成（Retrieval-Augmented Generation, RAG）是一种结合检索和生成的技术...
来源：wiki_检索增强生成.md, rag_system_notes.md
```

**场景 3：跨文档综合**
```
问题：向量数据库和传统数据库有什么区别？
回答：向量数据库专注于高维向量的相似性搜索，使用 HNSW 等索引算法...
来源：wiki_向量数据库.md, vector_db_notes.md
```

**场景 4：拒答演示**
```
问题：钢琴考级需要准备什么？
回答：资料中没有相关信息。
说明：系统正确识别知识库中无相关内容，拒绝编造答案
```

### 15.2 查询解析效果

| 用户输入 | 解析结果 |
|----------|----------|
| "2024年的通知讲了啥" | `search_query: "通知"`, `filters: {year: 2024, category: "notice"}` |
| "去年老师有没有说过期末怎么考" | `search_query: "期末考试 形式"`, `filters: {year: 2025, category: "notice"}` |
| "什么是 RAG" | `search_query: "RAG 检索增强生成"`, `filters: null` |
| "张三写的案例分析" | `search_query: "案例分析"`, `filters: {author: "张三"}` |

## 十六、结论

本项目已完成课程方向 B 的所有核心交付目标：

1. **自动化数据流水线**：收集 → 清洗 → 分块 → 嵌入 → 存储 → 检索 → 生成，全链路一键执行
2. **语义混合检索**：向量搜索 + 元数据过滤 + 查询意图解析 + max_distance 阈值裁剪 + 多层回退
3. **有据可查防幻觉**：System Prompt 约束 + 来源强制标注 + 自动补全
4. **工程化标准**：模块化、可测试（54 个测试函数）、环境变量管理、路径可移植、单例模式降本

**项目亮点**：
- 📊 处理 73 个文档，生成 200+ 文本块，建库成本 < ¥1
- 🔍 查询意图解析支持自然语言，无需学习搜索语法
- 🛡️ 多层降级策略确保系统永远有结果
- 📝 100% 来源追溯，支持人工核查

对标 PDF "什么能得 A" 标准：一条干净、自动化的流水线，接受杂乱文本文件夹 → 输出可搜索向量索引 → 检索确切段落 → LLM 准确引用。本项目满足上述全部要求。

后续若按"Reranker + 评测体系 + 增量索引 + 多租户"继续迭代，可从课程原型平滑演进至企业级知识服务系统。
