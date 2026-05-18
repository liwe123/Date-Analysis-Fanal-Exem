# 分工方案

4 人按照一条流水线接力，每人汇报自己那块就行。

| 成员 | 负责什么 | 要讲多久 | 对应文件 |
|------|---------|---------|---------|
| A | 读文件 + 清洗 | 2 分钟 | `ingest.py`, `collect_corpus.py`, `collect_stackoverflow.py`, `collect_csdn.py`, `preprocess.py`（clean_text） |
| B | 切块 + 打标签 | 2 分钟 | `preprocess.py`（chunk_text / extract_metadata / process_documents）, `utils.py` |
| C | 存向量 + 检索 | 2 分钟 | `embed_store.py`, `query_parser.py` |
| D | 生成回答 + 演示 | 4 分钟 | `qa.py`, `main.py`, `streamlit_app.py` |

---

## 给每个人：你只需要做三件事

1. **跑一遍系统**（15 分钟）
   ```
   pip install -r requirements.txt
   copy .env.example .env    # 填上 API Key
    python src/main.py collect          # Wikipedia
    python src/main.py collect-so       # Stack Overflow
    python src/main.py collect-csdn     # CSDN
    python src/main.py collect-all      # 全量采集
   python src/main.py build
   python src/main.py ask --question "课程项目最后提交要求是什么？"
   streamlit run app/streamlit_app.py
   ```

2. **读自己那块的代码**（30 分钟）—— 看下面每个人的章节

3. **背一下汇报词和可能被问的问题**（15 分钟）—— 看下面每个人的章节

---

## A：读文件 + 清洗

### 看哪些代码
- `src/ingest.py`：怎么遍历 `data/raw/` 文件夹，怎么读 .md / .txt / .pdf，怎么解析 `---` 包着的 YAML 头
- `src/collect_corpus.py`：怎么从 Wikipedia 自动扒 58 个词条（重试、限速、中英文回退）
- `src/preprocess.py` 里的 `clean_text()`：怎么去掉 HTML 标签、乱码字符、多余空行

### 汇报词（照着念）
> 我负责第一步，就是把原始文件读进来、洗干净。
>
> 数据源有三类：一是课程资料，`data/raw/` 下面大概 50 个 md 文件，包括课程介绍、FAQ、案例、通知这些；二是我们自动从 Wikipedia 扒的 83 个大数据相关词条；三是从 Stack Overflow 和 CSDN 采集的 48 篇技术问答和博客，全部放在 `data/raw/external/`。
>
> 我们支持 md、txt、pdf 三种格式。md 文件头部如果有 `---` 包着的 YAML（我们叫 Front-Matter），会被单独解析出来存为元数据，后面 B 同学会用到。
>
> 清洗这一步主要做四件事：去掉 HTML 标签、转义字符还原（把 `&amp;` 变回 `&`）、删掉乱码控制字符、压缩多余空行。洗干净的文本交给 B。

### 老师可能问
**Q：Wikipedia 怎么扒的，会不会被封 IP？**
A：用的 Wikipedia 官方 REST API，免费，有每秒请求限制。我们代码里有 `time.sleep(2)` 和重试机制，不会触发封禁。

**Q：Front-Matter 是什么？**
A：就是 md 文件开头 `---` 包着的那段，里面像这样写 `year: 2024`、`category: notice`，用来存文件的元信息。用 PyYAML 解析。

**Q：PDF 怎么读的？**
A：用 PyMuPDF（fitz），提取纯文本。它是 C 语言写的底层库，速度快，中文支持好。

**Q：图片、表格怎么办？**
A：目前只提文字，图片表格会被跳过。报告里写了这是后续改进方向。

---

## B：切块 + 打标签

### 看哪些代码
- `src/preprocess.py` 里的 `chunk_text()`：怎么把长文章切成 700 字左右的小块，保留 120 字重叠
- `src/preprocess.py` 里的 `extract_metadata()`：怎么让 GPT 自动识别文章的年份、分类、语言
- `src/preprocess.py` 里的 `process_documents()`：编排整个预处理流程，Front-Matter 元数据和 LLM 元数据怎么合并
- `src/utils.py`：OpenAI 客户端（单例）、读取环境变量、日志

### 汇报词（照着念）
> 我负责第二步：把 A 洗干净的文本切成小块，再给每块打上标签。
>
> 为什么要切块？因为整篇文章太长，Embedding 模型一次只能处理有限长度，而且语义太杂——直接把一篇 5000 字的文章扔进去检索，什么问题和它都比不近。切成小块后每块语义集中，检索命中率更高。我默认切成 700 字一块，相邻两块有 120 字重叠，防止句子刚好卡在边界被切断。
>
> 切块不是简单数 700 个字符一刀切，那样会在句子中间断开。我按四层优先级：段落边界 → 句子边界 → 贪心合并 → 滑窗强制切。优先保留段落和句子的完整性。
>
> 然后我给每块打标签。每篇文章发前 1200 字给 GPT，让它返回 JSON，里面有作者、年份、分类、语言和一个摘要。但如果 md 文件头部自己写了 Front-Matter（比如 `year: 2024`），就以人写的为准覆盖 GPT 的——因为人写的更靠谱。
>
> 另外我还管工具类，OpenAI 客户端做成全局单例避免重复建连接，环境变量也是显式加载方便测试。

### 老师可能问
**Q：chunk_size 为什么是 700？**
A：太小（比如 300）语义会碎，太大（比如 2000）语义会散。700 加上 120 重叠，在课程文档上跑着刚好合适。这个值可以调，`build` 命令支持 `--chunk-size` 参数。

**Q：重叠 120 会导致两个块有重复内容吗？**
A：会，但这是故意设计的。一个句子如果刚好在切口上，两个块都保留它，检索时不会漏掉。重复问题在检索阶段有去重处理。

**Q：GPT 提取元数据会不会很慢很贵？**
A：不贵。50 篇文档各调一次 deepseek-v4-flash，加起来也就几毛钱。而且这是建库时离线跑一次，不影响用户使用速度。

**Q：如果 GPT 返回的 JSON 格式不对怎么办？**
A：代码里有 try/except，解析失败就返回空字典，不会崩。后面合并时 Front-Matter 的数据还在，不影响。

---

## C：存向量 + 检索

### 看哪些代码
- `src/embed_store.py`：ChromaDB 怎么建表、批量写入、检索、距离过滤、元数据过滤、安全删除
- `src/query_parser.py`：怎么把用户的自然语言问题翻译成检索词 + 过滤条件

### 汇报词（照着念）
> 我负责第三步：把 B 切好的文本块变成向量存进数据库，并在用户提问时找出最相关的。
>
> 为什么要向量？关键词搜索只能匹配一模一样的字。你搜「怎么交作业」，文档里写的是「提交方式」，关键词搜索就找不到。向量搜索能看到语义——「交作业」和「提交方式」向量很接近。
>
> 我用本地 Qwen3-Embedding-0.6B 模型把文本转成 1024 维的向量，通过 GPU CUDA 加速推理，存进 ChromaDB。ChromaDB 是个开源的本地向量数据库，不需要装 Docker，数据直接存硬盘上 `vector_store/` 文件夹。
>
> 检索时做了两层：第一层向量搜索，按语义找最像的；第二层元数据过滤——比如用户问「2024 年的通知」，我只在 `year=2024, category=notice` 的文档里搜。有个回退机制：如果加了过滤后一条都没有，自动去掉过滤重搜，保证用户不会看空白页。
>
> 我还做了一个查询解析器：用户说「去年老师有没有说过期末怎么考」，我用另一个 LLM 调用把这句话翻译成 `search_query: "期末考试 形式", filters: {year: "2025", category: "notice"}`。解析失败就直接用原问题搜，不会卡住。

### 老师可能问
**Q：为什么选 ChromaDB？**
A：轻量、零部署、直接 pip install 就能用，适合课程项目。Milvus 要装 Docker，Pinecone 要付费。如果要真的上线用，可以换，但我们把它封装了一层，换数据库只改一个文件。

**Q：余弦距离是什么？**
A：就是两个向量夹角的余弦值。0 表示方向完全一样，2 表示完全相反。用来衡量两段文本语义有多接近——不看长度只看方向。

**Q：embedding 模型为什么不用 OpenAI 的？**
A：我们用的是本地 Qwen3-Embedding-0.6B 模型，GPU 推理零费用，而且中文效果更好。建库时一次性生成向量，不产生持续 API 开销。

**Q：查询解析也用 GPT，会不会让速度变慢？**
A：多调一次 deepseek-v4-flash，大概多花 1-2 秒。但这对用户透明，而且有个好处——用户怎么说话都行，不用学特定格式。失败了也有降级策略。

---

## D：生成回答 + 全系统演示

### 看哪些代码
- `src/qa.py`：怎么把检索结果拼成上下文喂给 GPT，System Prompt 怎么写，答案里怎么追溯来源
- `src/main.py`：CLI 子命令（build / ask / collect / collect-so / collect-csdn / collect-all）怎么编排整个流水线
- `app/streamlit_app.py`：Web 界面怎么做的（对话记录、侧边栏、调参、调试模式）

### 汇报词（照着念）

> 我负责最后一步：用检索到的资料让 GPT 生成答案，然后把前面三位同学的所有东西串成一个能用的产品。
>
> **防幻觉**：GPT 有一个毛病——被问到资料里没有的东西时，它会自己编。我写的 System Prompt 明确规定：只能依据我给的资料回答，找不到就说找不到，不许编。这是 RAG 和普通聊天机器人最大的区别。
>
> **引用追溯**：每个答案都要带来源。我要求 GPT 在回答里标注 `【来源：xxx.md】`。如果它忘了写，后端会自动补一个参考资料列表。这样老师和同学可以回去查看原始文档。
>
> **系统集成**：我把整条流水线串成了多个命令——`build` 一键建库，`ask` 交互问答，`collect`/`collect-so`/`collect-csdn`/`collect-all` 拉取三源知识库。还做了一个 Web 界面，在浏览器里就能用，支持多轮对话、调检索参数、看调试信息。

### 现场演示（4 分钟）

```
1. 终端演示：
   python src/main.py ask --question "课程项目最后提交截止日期是什么？"
   → 展示答案 + 来源

2. 拒答演示：
   python src/main.py ask --question "钢琴考级需要准备什么？"
   → 展示"资料中没有相关信息"

3. 打开浏览器，streamlit run app/streamlit_app.py
   → 问一个跨文档的问题
   → 点开调试模式，展示搜索词和过滤条件
   → 调 Top-K 滑块，看结果变化
```

### 老师可能问
**Q：你怎么防止 GPT 瞎编？**
A：三招：System Prompt 写死「找不到就说不知道」；只把检索到的内容作为参考不给它自己发挥的空间；强制要求标注来源，后端检查补全。不是 100% 但大幅降低了幻觉。

**Q：对话历史怎么存的？**
A：Streamlit 的 `st.session_state` 里存一个消息列表，每次提问把历史消息一起发给 GPT。本质是用上下文窗口来理解前面说了什么，不是真的记忆。

**Q：Streamlit 为什么不用 Flask？**
A：Streamlit 纯 Python 写界面，不用写 HTML/CSS/JS，做数据项目演示开发快。要做正式 API 的话应该换 FastAPI。

**Q：整个系统哪个环节最慢？**
A：GPT 生成答案最慢，用户能感觉到。向量检索和查询解析都是毫秒级。

---

## 别忘了

- [ ] 亲手跑过 `build` + `ask` + streamlit
- [ ] 读过自己那块的代码
- [ ] 念一遍汇报词
- [ ] 知道前后同学大概做什么（老师可能跨模块问）
