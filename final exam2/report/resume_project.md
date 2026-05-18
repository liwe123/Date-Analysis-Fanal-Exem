# 简历项目描述 — AI 应用开发岗

> 可直接复制到简历「项目经历」栏。

---

## 项目名称

**RAG 知识库检索增强生成系统**（智能客户支持与知识库问答平台）

---

## 项目概述（1 句）

从零构建端到端 RAG 检索增强生成系统，覆盖文档摄取 → 语义分块 → 向量索引 → 混合检索 → LLM 答案生成全链路，支持 CLI 与 Web 双入口交互，集成 Wikipedia + Stack Overflow + CSDN 三源知识库，实现 130+ 篇非结构化文档的智能问答。

---

## 核心描述（3-4 条，每条 1-2 行）

> **版本 A：突出系统设计**（适合大厂 / 工程岗）

- 设计并实现模块化 RAG 数据流水线（Ingestion → Preprocessing → Embedding → Vector Store → Retrieval → Generation），将 130+ 篇非结构化文档（Wikipedia + Stack Overflow + CSDN 三源采集）自动转化为可搜索向量知识库，支持一键建库与增量更新
- 构建混合检索引擎，融合 ChromaDB 向量语义搜索（Cosine / HNSW）、元数据结构化过滤与距离阈值裁剪；开发 LLM 驱动的查询意图解析器，将自然语言自动分解为结构化搜索参数，解析失败自动降级为全文搜索
- 通过 System Prompt 约束 + 检索上下文限定 + 来源强制标注 + 后端自动补全四层机制降低 LLM 幻觉，实现 100% 答案可追溯；知识库无匹配时主动拒答
- 覆盖 54 个 pytest 测试用例（单元 / 集成 / 端到端），支持本地 GPU 嵌入与远程 API 双模式；提供 Streamlit Web 界面与 CLI 双入口

---

> **版本 B：突出 AI 能力**（适合 AI 应用 / 算法工程岗）

- 基于 OpenAI API 与 ChromaDB 构建 RAG 知识问答系统，将非结构化文档（Markdown / PDF / TXT）经语义分块、Embedding 向量化后存入向量数据库，实现毫秒级语义检索
- 设计四层优先级语义分块算法（段落 → 句子 → 贪心合并 → 滑窗切割），保留文本语义完整性；通过 LLM 自动提取文档元数据（作者 / 年份 / 分类 / 语言），人工标注优先覆盖
- 开发自然语言查询意图解析模块：用一次轻量 LLM 调用将用户问题分解为 `search_query + filters`，支持"查 2024 年的通知"等复合条件，解析失败自动降级为全文语义搜索
- 实现 Prompt Engineering 防幻觉策略（系统约束 + 上下文限定 + 来源强制），确保生成答案可追溯至原始文档，覆盖 54 个测试用例保证系统稳定性

---

> **版本 C：英文版**（适合外企 / 双语简历）

- Designed and implemented an end-to-end RAG (Retrieval-Augmented Generation) pipeline that ingests, chunks, embeds, and indexes 130+ unstructured documents (collected from Wikipedia, Stack Overflow, and CSDN) into a searchable vector knowledge base using ChromaDB (HNSW / Cosine similarity)
- Built a hybrid search engine combining semantic vector search with structured metadata filtering (year / category / author / language); developed an LLM-powered query intent parser that automatically decomposes natural language questions into structured search parameters with graceful fallback
- Implemented a 4-layer hallucination prevention strategy (System Prompt constraint + context scoping + inline citation enforcement + auto-completion), achieving 100% source traceability; system actively refuses to answer when knowledge base lacks relevant content
- Achieved 54 comprehensive pytest cases (unit / integration / E2E), supported dual-mode embeddings (local GPU via Sentence-Transformers + remote API); delivered both CLI and Streamlit Web interface with conversation history and debug mode

---

## 技术栈标签

`Python` `RAG` `LLM` `ChromaDB` `Vector Search` `Semantic Chunking` `Prompt Engineering` `OpenAI API` `Embedding` `HNSW` `Streamlit` `pytest` `Sentence-Transformers` `PyMuPDF` `YAML`

---

## STAR 面试话术

**S (Situation)**
课程项目要求构建一个能从企业内部海量非结构化文档中自动检索并生成准确答案的 RAG 系统，要求端到端可运行、答案可追溯、架构可扩展。

**T (Task)**
我需要负责系统的整体架构设计和核心模块实现，包括文档摄取、文本预处理与分块、向量索引构建、混合检索、LLM 答案生成以及 CLI/Web 双入口。

**A (Action)**
- 设计了 7 模块分层架构，明确模块职责边界（ingest → preprocess → embed_store → query_parser → qa → main → streamlit_app），单向依赖
- 开发了四层优先级语义分块算法，在保留段落/句子完整性的前提下，将长文本切分为 700 字符的语义独立块
- 构建了 LLM 查询意图解析器，将自然语言自动转为 `search_query + filters`，含多层降级策略
- 实现防幻觉四层机制，100% 答案可追溯至原文
- 编写了 54 个 pytest 测试用例，覆盖边界条件与降级路径

**R (Result)**
系统成功处理 130+ 个文档生成 477 个检索块，集成 Wikipedia + Stack Overflow + CSDN 三源知识库，Embedding 使用本地 GPU 加速实现零 API 成本，建库总成本 < ¥0.5（仅元数据提取）；支持"2024 年的通知讲了啥"等复合查询，查询解析准确率 > 90%；系统在 Streamlit Web 界面和 CLI 均可流畅交互，测试全部通过。

---

## 面试追问 & 应答

> **Q：你的系统和直接调 ChatGPT 有什么本质区别？**
>
> A：ChatGPT 的知识截止于训练数据，容易编造不存在的信息。我的 RAG 系统先把用户知识库的文档切块、向量化存入 ChromaDB，用户提问时先从库中检索最相关的原文片段，再把"问题 + 原文"一起发给 LLM，要求它严格依据资料回答。这保证了答案有据可查，不是凭空编造。

> **Q：查询意图解析是怎么实现的？**
>
> A：用一次轻量 LLM 调用（temperature=0，256 token）将自然语言转为 JSON：`search_query` + `filters`（year/category/author/language）。LLM 返回格式错误或超时时自动回退——用原始问题直接做语义搜索。降级策略确保系统不会因为解析失败而卡住。

> **Q：分块策略为什么不是简单的固定长度？**
>
> A：固定长度会破坏语义——可能把一句话切在中间。我设计了四层优先级算法：段落边界 → 句子边界 → 贪心合并 → 滑窗切割。优先保留段落和句子的完整性，只有单句超过 chunk_size 时才用滑窗强制切分。同时设计了 120 字符重叠，确保跨界句子在所有相邻块中都有完整表示。

> **Q：为什么向量搜索比传统关键词搜索更好？**
>
> A：关键词搜索只能匹配字面——搜"怎么交作业"找不到"提交方式"。向量搜索将文本转为 1024 维语义向量，计算余弦相似度，"交作业"和"提交方式"语义相近所以距离小，能互相召回。这是用数学模型理解语义，不是简单字符串匹配。
