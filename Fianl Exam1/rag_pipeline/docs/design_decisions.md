# 技术选型说明

## 1. 嵌入模型选型

### 选项对比

| 模型 | 维度 | 大小 | 速度 | 质量 | 成本 |
|------|------|------|------|------|------|
| all-MiniLM-L6-v2 | 384 | 80MB | 快 | 良好 | 免费 |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 420MB | 中 | 优秀 | 免费 |
| text-embedding-ada-002 | 1536 | N/A | 慢 | 优秀 | 收费 |
| text-embedding-3-small | 1536 | N/A | 慢 | 优秀 | 收费 |

### 最终选择

**all-MiniLM-L6-v2**

**理由**：
1. **免费**：无需API Key，无使用成本
2. **轻量**：模型仅80MB，加载快
3. **本地**：离线运行，无网络延迟
4. **平衡**：在速度和质量之间取得良好平衡
5. **多语言**：支持中英文混合文本

**使用方式**：
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["文本1", "文本2"])
```

## 2. 向量数据库选型

### 选项对比

| 数据库 | 部署方式 | 元数据 | 规模 | 复杂度 |
|--------|----------|--------|------|--------|
| ChromaDB | 本地文件 | ✅ | 中小 | 低 |
| Milvus | Docker | ✅ | 大 | 高 |
| Qdrant | Docker | ✅ | 大 | 中 |
| FAISS | 本地文件 | ❌ | 大 | 中 |
| Pinecone | 云服务 | ✅ | 大 | 低 |

### 最终选择

**ChromaDB**

**理由**：
1. **简单**：无需额外服务，直接使用
2. **本地**：数据存储在本地文件
3. **集成**：内置嵌入函数支持
4. **元数据**：支持元数据过滤
5. **足够**：对于10-10000文档规模足够

**使用方式**：
```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("documents")

# 添加文档
collection.add(
    ids=["id1"],
    embeddings=[[0.1, 0.2, ...]],
    metadatas=[{"title": "文档1"}],
    documents=["文档内容"]
)

# 查询
results = collection.query(
    query_embeddings=[[0.1, 0.2, ...]],
    n_results=5
)
```

## 3. 分块策略选型

### 选项对比

| 策略 | 语义完整性 | 实现复杂度 | 适用场景 |
|------|-----------|-----------|----------|
| 固定大小 | ❌ | 低 | 通用 |
| 按句子 | ✅ | 低 | 短文档 |
| 按段落 | ✅ | 低 | 结构化文档 |
| 递归字符 | ✅ | 中 | 通用 |
| 语义分块 | ✅✅ | 高 | 高质量需求 |

### 最终选择

**递归字符分割 (RecursiveCharacterTextSplitter)**

**理由**：
1. **语义保持**：按分隔符优先级分割，保持语义完整性
2. **通用性**：适用于各种文档类型
3. **可配置**：支持自定义分隔符和块大小
4. **成熟**：LangChain库提供成熟实现

**配置**：
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", ".", " ", ""]
)

chunks = splitter.split_text(text)
```

**分隔符优先级**：
1. `\n\n`（段落分隔）- 最高优先级
2. `\n`（换行）
3. `。`（中文句号）
4. `.`（英文句号）
5. ` `（空格）
6. ``（空字符串）- 最低优先级

## 4. LLM选型

### 选项对比

| 模型 | 质量 | 速度 | 成本 | 部署 |
|------|------|------|------|------|
| GPT-4 | 优秀 | 慢 | 高 | API |
| GPT-3.5-turbo | 良好 | 快 | 中 | API |
| Claude-3 | 优秀 | 中 | 高 | API |
| Llama-3 | 良好 | 中 | 免费 | 本地 |
| 回退模式 | 低 | 快 | 免费 | 无 |

### 最终选择

**OpenAI GPT-3.5-turbo + 回退模式**

**理由**：
1. **质量**：GPT-3.5在中文问答上表现良好
2. **速度**：响应快，用户体验好
3. **成本**：相对GPT-4便宜
4. **回退**：无API Key时使用回退模式，保证系统可用

**使用方式**：
```python
import openai

client = openai.OpenAI(api_key="your_key")
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "问题"}
    ]
)
```

## 5. 文本提取选型

### PDF提取

| 库 | 速度 | 质量 | 依赖 |
|----|------|------|------|
| PyMuPDF | 快 | 高 | MuPDF |
| PyPDF2 | 中 | 中 | 无 |
| pypdf | 中 | 中 | 无 |

**选择**：PyMuPDF（主）+ PyPDF2（备）

### HTML提取

| 库 | 功能 | 依赖 |
|----|------|------|
| BeautifulSoup4 | 完善 | 无 |
| lxml | 快速 | C库 |

**选择**：BeautifulSoup4

## 6. Web界面选型

### 选项对比

| 框架 | 开发速度 | 美观度 | 功能 | 学习曲线 |
|------|---------|--------|------|----------|
| Streamlit | 快 | 中 | 中 | 低 |
| Gradio | 快 | 中 | 中 | 低 |
| Flask | 中 | 低 | 高 | 中 |
| FastAPI | 中 | 低 | 高 | 中 |

### 最终选择

**Streamlit**

**理由**：
1. **快速**：几行代码即可创建界面
2. **简单**：无需前端知识
3. **集成**：内置数据展示组件
4. **适合**：适合演示和原型开发

## 7. 依赖管理选型

### 选项对比

| 工具 | 锁文件 | 虚拟环境 | 速度 |
|------|--------|----------|------|
| pip + requirements.txt | ❌ | ❌ | 快 |
| Poetry | ✅ | ✅ | 中 |
| Conda | ✅ | ✅ | 慢 |

### 最终选择

**pip + requirements.txt**

**理由**：
1. **简单**：最基础的依赖管理方式
2. **通用**：所有Python环境都支持
3. **快速**：安装速度快
4. **足够**：对于课程项目足够

## 8. 总结

| 组件 | 选择 | 主要理由 |
|------|------|----------|
| 嵌入模型 | all-MiniLM-L6-v2 | 免费、本地、平衡 |
| 向量数据库 | ChromaDB | 简单、本地、足够 |
| 分块策略 | 递归字符分割 | 语义保持、通用 |
| LLM | GPT-3.5 + 回退 | 质量好、有备选 |
| PDF提取 | PyMuPDF | 速度快、质量高 |
| HTML提取 | BeautifulSoup4 | 功能完善 |
| Web界面 | Streamlit | 快速开发 |
| 依赖管理 | pip | 简单通用 |

## 9. 技术权衡

### 权衡1：本地 vs 云服务

**选择**：本地部署

**理由**：
- 数据安全：数据不离开本地
- 成本：无API调用费用
- 延迟：无网络延迟

**代价**：
- 模型质量：本地模型不如云端大模型
- 计算资源：需要本地计算资源

### 权衡2：简单 vs 功能丰富

**选择**：简单优先

**理由**：
- 开发速度：快速完成原型
- 维护成本：易于维护和调试
- 学习曲线：易于理解和学习

**代价**：
- 功能限制：某些高级功能无法实现
- 性能限制：某些场景性能不如专业方案

### 权衡3：准确性 vs 速度

**选择**：平衡

**理由**：
- 用户体验：响应时间在1-3秒内
- 准确性：检索结果相关性>80%

**实现**：
- 使用HNSW索引：O(log n)检索复杂度
- 限制返回数量：top_k=5
- 缓存机制：缓存常用查询
