# 失败案例深度分析（报告用）

## 失败案例 1：SentenceTransformer 方法名变更导致全链路崩溃

### 现象
在切换本地嵌入模型（从远程 API 切换到 Qwen3-Embedding-0.6B）后，所有单元测试通过，但实际运行 `build` 或 `ask` 命令时，系统在首次调用嵌入时抛出 `AttributeError: 'SentenceTransformer' object has no attribute 'get_embedding_dimension'`，导致整个流水线无法运行。

### 根因分析
在 commit `92bc9b2` 中，开发者为修复 PyTorch 的 `FutureWarning` 警告，将 `_get_local_embedding_model()` 中的 `get_sentence_embedding_dimension()` 方法名修改为 `get_embedding_dimension()`。这一修改基于当时 PyTorch/Sentence-Transformers 的 deprecation 提示，但：

1. **未验证新方法是否可用**：`get_embedding_dimension()` 是未来版本的 API，当前安装的 `sentence-transformers 2.2.x` 仍使用旧方法名 `get_sentence_embedding_dimension()`。
2. **单元测试未覆盖此路径**：测试文件中 Mock 了整个 `_get_local_embedding_model()` 函数，返回一个简单的 mock 对象，因此不会触发真实的方法调用错误。
3. **缺乏集成冒烟测试**：没有在真实环境中运行一次端到端测试来验证 API 兼容性。

### 修复过程
将方法名改回 `get_sentence_embedding_dimension()`，同时保留对新版本 API 的兼容性检查：
```python
# 修复前（错误）
logger.info("本地嵌入模型加载完成（%d 维）。", _LOCAL_EMBEDDING_MODEL.get_embedding_dimension())

# 修复后（正确）
logger.info("本地嵌入模型加载完成（%d 维）。", _LOCAL_EMBEDDING_MODEL.get_sentence_embedding_dimension())
```

### 经验教训
- **不要盲目跟随 deprecation 警告修改代码**：必须确认目标版本的 API 实际存在。
- **Mock 测试无法发现 API 兼容性问题**：需要至少一个集成测试在真实环境中运行核心路径。
- **依赖版本锁定很重要**：`requirements.txt` 中应明确指定 `sentence-transformers>=2.2.0,<3.0.0`，避免 API 变更。

---

## 失败案例 2：ChromaDB 不支持复合 where 条件导致元数据过滤静默失败

### 现象
在评估测试中，Q31 "2025年的通知有哪些？" 使用查询解析器提取了 `filters: {"year": 2025, "category": "notice"}` 复合条件。系统日志显示：
```
[WARNING] embed_store: 检索发生错误，回退为纯向量搜索: Expected where to have exactly one operator, got {'year': 2025, 'category': 'notice'} in query.
```
系统自动回退为纯语义搜索，虽然仍返回了结果，但返回的是通用相关文档而非精确匹配 2025 年通知的文档。类似的失败在 Q38、Q39 中也出现。

### 根因分析
ChromaDB 的 `where` 参数在当前版本中**不支持直接传递多个键值对作为隐式 AND 条件**。期望 `{"year": 2025, "category": "notice"}` 等价于 SQL 的 `WHERE year=2025 AND category='notice'`，但 ChromaDB 要求使用显式的 `$and` 操作符：
```python
# ❌ 错误写法（ChromaDB 不支持）
where={"year": 2025, "category": "notice"}

# ✅ 正确写法
where={"$and": [{"year": 2025}, {"category": "notice"}]}
```

代码中的 `embed_store.search()` 虽然有 `try-except` 回退机制（移除 where 条件后重新查询），但这种静默降级意味着用户指定了过滤条件却得到了未过滤的结果，是一种**语义上的失败**（返回了不精确的结果）而非**技术上的失败**（报错）。

### 修复方案（待实施）
在 `embed_store.py` 的 `hybrid_search()` 方法中，当 `where` 字典包含多个键时，自动构造 `$and` 复合条件：
```python
if where and len(where) > 1:
    where = {"$and": [{k: v} for k, v in where.items()]}
```

### 经验教训
- **不要假设 API 的隐式行为**：ChromaDB 的 where 语法与 SQL 不同，必须查阅文档确认复合条件的写法。
- **静默回退是一种债务**：当前的回退机制虽然保证了系统不崩溃，但返回了不精确的结果。应该在回退时明确告知用户"过滤条件被忽略"。
- **评估驱动的发现**：如果没有运行系统性评估测试，这类边界条件很难被发现。

---

## 额外发现：评估中的幻觉模式

在 9 个超纲（out-of-scope）查询中，有 4 个触发了幻觉（44.4%）：

| 查询 | 系统行为 | 是否正确拒答 |
|------|---------|------------|
| 钢琴考级需要准备什么？ | 拒答 + 来源列表 | ✅ 正确（但脚本标记为幻觉，因返回了来源） |
| 今天天气怎么样？ | 拒答 + 来源列表 | ✅ 正确（同上） |
| Python 的 for 循环怎么写？ | **给出了详细代码示例** | ❌ 幻觉 |
| 项目的 GitHub 仓库地址是什么？ | 拒答 | ✅ 正确 |

**关键发现**：Q44（Python for 循环）检索到了 Stack Overflow 上的 pandas 代码片段，LLM 基于这些代码片段给出了详细的 for 循环示例。这暴露了一个设计缺陷：**当检索结果中包含代码时，LLM 倾向于"回答"而非"拒答"**，即使问题与知识库主题无关。

**修复方向**：在 System Prompt 中增加"如果参考资料与问题主题不相关，即使包含表面相关的关键词，也应拒答"的约束。
