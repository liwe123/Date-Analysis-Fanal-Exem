# RAG Pipeline 运维文档

## 1. 系统概述

### 1.1 系统简介
RAG Pipeline 是一个企业级检索增强生成系统，用于处理非结构化文档，提供语义搜索和智能问答能力。

### 1.2 系统组件

| 组件 | 进程/服务 | 端口 | 说明 |
|------|-----------|------|------|
| ChromaDB | 无独立进程 | 无 | 嵌入式向量数据库，文件存储 |
| Sentence-Transformers | 无独立进程 | 无 | 本地嵌入模型，运行时加载 |
| Streamlit | Web服务 | 8501 | 演示界面（按需启动） |
| OpenAI API | 外部服务 | 443 | LLM生成（可选） |

### 1.3 部署模式
- **单机部署**：所有组件在同一台机器上运行
- **文件存储**：ChromaDB数据存储在本地 `chroma_db/` 目录

## 2. 安装部署

### 2.1 环境要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|----------|
| 操作系统 | Windows 10 / Linux / macOS | Windows 11 / Ubuntu 22.04 |
| Python | 3.9+ | 3.11 |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 2GB | 10GB+ (取决于文档量) |
| CPU | 2核 | 4核+ |

### 2.2 首次部署

**步骤1：克隆/复制项目**
```bash
# 如果是Git仓库
git clone <repo_url>
cd rag_pipeline

# 如果是直接复制
cd D:\date analysis\Fianl Exam1\rag_pipeline
```

**步骤2：创建虚拟环境（推荐）**
```bash
python -m venv venv

# Windows激活
venv\Scripts\activate

# Linux/Mac激活
source venv/bin/activate
```

**步骤3：安装依赖**
```bash
pip install -r requirements.txt
```

**步骤4：验证安装**
```bash
python -c "import chromadb; import sentence_transformers; import streamlit; print('OK')"
```

**步骤5：准备数据**
```bash
# 将文档放入 data/raw/documents/ 目录
# 支持的格式: .txt, .html, .htm, .pdf
# 编辑 data/raw/metadata.csv 添加元数据
```

**步骤6：执行首次索引**
```bash
python run.py index --reset
```

### 2.3 配置说明

编辑 `config/settings.py`：

```python
# 核心配置
CHROMA_DB_PATH = "./chroma_db"          # 向量数据库路径
CHROMA_COLLECTION_NAME = "documents"     # 集合名称
CHUNK_SIZE = 500                        # 分块大小（字符）
CHUNK_OVERLAP = 50                      # 分块重叠（字符）
TOP_K = 5                               # 检索返回数量

# 嵌入模型
EMBEDDING_MODEL = "all-MiniLM-L6-v2"    # 嵌入模型名称

# LLM配置（可选）
OPENAI_API_KEY = ""                     # OpenAI API密钥
OPENAI_MODEL = "gpt-3.5-turbo"         # LLM模型
```

## 3. 日常运维

### 3.1 索引管理

**全量索引（首次或重建）**
```bash
python run.py index --reset
```

**增量索引（添加新文档）**
```bash
# 将新文档放入 data/raw/documents/ 后执行
python run.py index
```

**查看索引统计**
```bash
python run.py stats
```

**重置数据库（清空所有索引）**
```bash
python run.py reset
```

### 3.2 查询测试

**命令行查询**
```bash
python run.py query "什么是Python？"
```

**交互式查询**
```bash
python run.py interactive
# 输入 quit 退出
```

**启动Web界面**
```bash
streamlit run app/streamlit_app.py
# 浏览器访问 http://localhost:8501
```

### 3.3 数据管理

**添加新文档**
1. 将文档复制到 `data/raw/documents/`
2. 更新 `data/raw/metadata.csv`（可选）
3. 运行 `python run.py index`

**删除文档**
目前不支持单独删除文档。如需删除：
1. 从 `data/raw/documents/` 移除文件
2. 运行 `python run.py index --reset` 重建索引

**更新文档**
1. 替换 `data/raw/documents/` 中的文件
2. 运行 `python run.py index --reset` 重建索引

### 3.4 日常监控

**检查索引数据库大小**
```bash
# Windows
dir chroma_db /s

# Linux/Mac
du -sh chroma_db/
```

**检查日志**
- ChromaDB日志：控制台输出
- 嵌入模型日志：首次加载时下载模型

**检查系统资源**
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep python
```

## 4. 故障排查

### 4.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|----------|
| 索引失败 | 文档编码问题 | 检查文档是否为UTF-8编码 |
| 查询无结果 | 数据库为空 | 先执行 `python run.py index` |
| 嵌入模型加载失败 | 网络问题或磁盘空间不足 | 检查网络，清理磁盘空间 |
| 中文乱码 | 控制台编码问题 | 使用 Streamlit 界面查看 |
| 内存不足 | 文档太大 | 增大 CHUNK_SIZE，减少文档量 |
| ChromaDB错误 | 数据库损坏 | 执行 `python run.py reset` |

### 4.2 详细排查步骤

**问题1：索引失败**
```bash
# 1. 检查数据目录
ls data/raw/documents/

# 2. 检查文档编码
python -c "
from src.ingestion.txt_reader import TXTReader
reader = TXTReader()
encoding = reader.get_encoding('data/raw/documents/your_file.txt')
print(f'编码: {encoding}')
"

# 3. 检查ChromaDB
python -c "
from src.storage.chroma_manager import ChromaManager
manager = ChromaManager(db_path='./chroma_db')
print(f'文档数: {manager.count()}')
"
```

**问题2：查询无结果**
```bash
# 1. 验证数据库不为空
python run.py stats

# 2. 测试简单查询
python run.py query "Python"

# 3. 检查检索参数
# 编辑 config/settings.py 增大 TOP_K 或降低 SIMILARITY_THRESHOLD
```

**问题3：嵌入模型加载失败**
```bash
# 1. 测试模型下载
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print('模型加载成功')
"

# 2. 如果网络问题，使用镜像
export HF_ENDPOINT=https://hf-mirror.com

# 3. 或手动下载模型放到缓存目录
# 缓存目录通常在: ~/.cache/huggingface/hub/
```

**问题4：ChromaDB损坏**
```bash
# 1. 备份现有数据
cp -r chroma_db chroma_db_backup

# 2. 重置数据库
python run.py reset

# 3. 重新索引
python run.py index
```

### 4.3 性能诊断

**诊断索引性能**
```python
import time
from src.pipeline.indexing_pipeline import IndexingPipeline

start = time.time()
pipeline = IndexingPipeline(db_path="./chroma_db")
pipeline.run("./data/raw/documents")
print(f"索引耗时: {time.time() - start:.2f}秒")
```

**诊断查询性能**
```python
import time
from src.pipeline.query_pipeline import QueryPipeline
from src.storage import ChromaManager
from src.embedding import Embedder

chroma = ChromaManager(db_path="./chroma_db")
embedder = Embedder()
pipeline = QueryPipeline(chroma, embedder)

start = time.time()
result = pipeline.run("测试查询")
print(f"查询耗时: {time.time() - start:.2f}秒")
```

## 5. 备份与恢复

### 5.1 备份操作

**备份整个项目**
```bash
# Windows
xcopy rag_pipeline rag_pipeline_backup_$(Get-Date -Format 'yyyyMMdd') /E /I

# Linux/Mac
cp -r rag_pipeline rag_pipeline_backup_$(date +%Y%m%d)
```

**仅备份核心数据**
```bash
# 备份原始文档
cp -r data/raw/documents data_backup/documents

# 备份元数据
cp data/raw/metadata.csv data_backup/metadata.csv

# 备份ChromaDB数据库
cp -r chroma_db chroma_db_backup

# 备份配置文件
cp config/settings.py config_backup/settings.py
```

### 5.2 恢复操作

**恢复ChromaDB数据库**
```bash
# 停止相关进程
# 恢复数据库文件
rm -rf chroma_db
cp -r chroma_db_backup chroma_db
```

**完整恢复**
```bash
# 恢复所有数据
cp -r data_backup/* data/raw/
cp -r chroma_db_backup chroma_db
cp config_backup/settings.py config/settings.py
```

### 5.3 备份策略建议

| 数据类型 | 备份频率 | 保留时间 |
|---------|---------|---------|
| 原始文档 | 每次变更后 | 永久 |
| ChromaDB | 每日 | 7天 |
| 配置文件 | 每次变更后 | 永久 |

## 6. 升级指南

### 6.1 依赖升级

**检查可升级的包**
```bash
pip list --outdated
```

**升级所有依赖**
```bash
pip install --upgrade -r requirements.txt
```

**升级特定包**
```bash
pip install --upgrade chromadb
pip install --upgrade sentence-transformers
```

### 6.2 代码升级

**拉取最新代码**
```bash
git pull origin main
```

**重新安装依赖**
```bash
pip install -r requirements.txt
```

**重建索引（如数据格式变更）**
```bash
python run.py index --reset
```

### 6.3 升级注意事项

1. **升级前备份**：始终备份 `chroma_db/` 和 `data/` 目录
2. **测试升级**：在测试环境先验证
3. **检查兼容性**：查看依赖库的CHANGELOG
4. **回滚准备**：保留旧版本依赖的备份

## 7. 安全指南

### 7.1 API密钥管理

**使用环境变量**
```bash
# Windows
set OPENAI_API_KEY=your_key_here

# Linux/Mac
export OPENAI_API_KEY=your_key_here
```

**使用.env文件（不要提交到Git）**
```bash
# 创建 config/.env
echo "OPENAI_API_KEY=your_key_here" > config/.env
```

**在.gitignore中添加**
```
.env
config/.env
chroma_db/
```

### 7.2 数据安全

1. **本地存储**：所有数据存储在本地，不经过第三方
2. **API调用**：仅在使用LLM时调用OpenAI API
3. **无日志泄露**：系统不记录用户查询内容

### 7.3 访问控制

**文件权限**
```bash
# Linux/Mac
chmod 700 chroma_db/       # 仅所有者可访问
chmod 600 config/.env      # 仅所有者可读写
```

**Streamlit访问控制**
```bash
# 仅本地访问
streamlit run app/streamlit_app.py --server.address localhost

# 指定端口
streamlit run app/streamlit_app.py --server.port 8501
```

## 8. 性能调优

### 8.1 索引性能调优

| 参数 | 默认值 | 调优建议 |
|------|--------|---------|
| CHUNK_SIZE | 500 | 增大可减少块数，加快索引 |
| BATCH_SIZE | 32 | 嵌入批处理大小，增大可提速 |
| CHUNK_OVERLAP | 50 | 减少可降低冗余 |

### 8.2 查询性能调优

| 参数 | 默认值 | 调优建议 |
|------|--------|---------|
| TOP_K | 5 | 减少可加快查询 |
| hnsw:search_ef | 100 | 降低可加快查询（需修改代码） |
| hnsw:M | 16 | 调整可平衡速度与精度 |

### 8.3 存储优化

**压缩向量**
```python
# 在 chroma_manager.py 中修改
self.collection = self.client.get_or_create_collection(
    name=collection_name,
    metadata={
        "hnsw:space": "cosine",
        "hnsw:M": 16,              # 降低连接数
        "hnsw:construction_ef": 100, # 降低构建参数
        "hnsw:search_ef": 50        # 降低搜索参数
    }
)
```

### 8.4 大数据量优化

当文档数量超过10000时：
1. **分批索引**：将文档分组，分别索引
2. **多集合**：按类别创建多个集合
3. **定期清理**：删除不常用的索引

## 9. 监控与日志

### 9.1 健康检查脚本

创建 `scripts/health_check.py`：
```python
"""系统健康检查"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_imports():
    """检查依赖导入"""
    try:
        import chromadb
        import sentence_transformers
        import streamlit
        print("[OK] 核心依赖正常")
    except ImportError as e:
        print(f"[FAIL] 依赖缺失: {e}")

def check_chromadb():
    """检查ChromaDB状态"""
    try:
        from src.storage.chroma_manager import ChromaManager
        from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
        manager = ChromaManager(db_path=CHROMA_DB_PATH, collection_name=CHROMA_COLLECTION_NAME)
        count = manager.count()
        print(f"[OK] ChromaDB正常, 文档数: {count}")
    except Exception as e:
        print(f"[FAIL] ChromaDB异常: {e}")

def check_data():
    """检查数据目录"""
    from config.settings import RAW_DATA_DIR
    files = list(Path(RAW_DATA_DIR).glob("*"))
    supported = ['.txt', '.html', '.htm', '.pdf']
    doc_count = sum(1 for f in files if f.suffix in supported)
    print(f"[OK] 数据目录正常, 文档数: {doc_count}")

if __name__ == "__main__":
    print("=" * 40)
    print("RAG Pipeline 健康检查")
    print("=" * 40)
    check_imports()
    check_chromadb()
    check_data()
    print("=" * 40)
```

**运行健康检查**
```bash
python scripts/health_check.py
```

### 9.2 日志配置

在 `config/settings.py` 中添加：
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('rag_pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 9.3 监控指标

| 指标 | 获取方式 | 正常范围 |
|------|---------|---------|
| 索引文档数 | `python run.py stats` | > 0 |
| 查询响应时间 | 性能诊断脚本 | < 3秒 |
| ChromaDB大小 | `dir chroma_db /s` | 按文档量 |
| 内存使用 | 任务管理器 | < 2GB |
| API调用次数 | OpenAI Dashboard | 按使用量 |

## 10. 自动化运维

### 10.1 定时任务

**Windows定时任务**
```powershell
# 创建定时索引任务（每天凌晨2点）
$action = New-ScheduledTaskAction -Execute "python" -Argument "run.py index" -WorkingDirectory "D:\date analysis\Fianl Exam1\rag_pipeline"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00am
Register-ScheduledTask -TaskName "RAG_Index" -Action $action -Trigger $trigger
```

**Linux cron任务**
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点执行索引
0 2 * * * cd /path/to/rag_pipeline && python run.py index
```

### 10.2 备份自动化

**Windows备份脚本** (`scripts/backup.bat`)
```batch
@echo off
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%
set BACKUP_DIR=backup_%DATE%
mkdir %BACKUP_DIR%
xcopy data\raw\documents %BACKUP_DIR%\documents /E /I
copy data\raw\metadata.csv %BACKUP_DIR%\
xcopy chroma_db %BACKUP_DIR%\chroma_db /E /I
copy config\settings.py %BACKUP_DIR%\
echo 备份完成: %BACKUP_DIR%
```

**Linux备份脚本** (`scripts/backup.sh`)
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="backup_${DATE}"

mkdir -p "$BACKUP_DIR"
cp -r data/raw/documents "$BACKUP_DIR/documents"
cp data/raw/metadata.csv "$BACKUP_DIR/"
cp -r chroma_db "$BACKUP_DIR/chroma_db"
cp config/settings.py "$BACKUP_DIR/"

echo "备份完成: $BACKUP_DIR"
```

### 10.3 一键启动脚本

**Windows** (`scripts/start.bat`)
```batch
@echo off
echo 启动 RAG Pipeline...
start "RAG Streamlit" cmd /c "streamlit run app/streamlit_app.py"
echo Web界面启动中...
timeout /t 3
start http://localhost:8501
echo 完成！
pause
```

**Linux** (`scripts/start.sh`)
```bash
#!/bin/bash
echo "启动 RAG Pipeline..."
streamlit run app/streamlit_app.py --server.address 0.0.0.0 &
sleep 3
echo "Web界面: http://localhost:8501"
```

## 11. 扩容指南

### 11.1 数据量增长应对

| 文档数量 | 策略 | 说明 |
|---------|------|------|
| < 1000 | 单机部署 | 当前方案 |
| 1000-10000 | 优化分块 | 增大CHUNK_SIZE |
| 10000-100000 | 多集合 | 按类别分集合 |
| > 100000 | 分布式 | 迁移到Milvus |

### 11.2 迁移到更大规模方案

**迁移到Milvus的步骤**
1. 安装Milvus（Docker部署）
2. 修改 `src/storage/` 添加Milvus适配器
3. 数据迁移脚本
4. 性能对比测试

## 12. 常见运维命令速查

```bash
# 索引相关
python run.py index                    # 执行索引
python run.py index --reset            # 重建索引
python run.py stats                    # 查看统计
python run.py reset                    # 清空数据库

# 查询相关
python run.py query "问题"             # 单次查询
python run.py interactive              # 交互式查询

# 服务相关
streamlit run app/streamlit_app.py     # 启动Web界面

# 测试相关
python test_e2e.py                     # 端到端测试
python test_ingestion.py               # 摄取模块测试

# 维护相关
pip list --outdated                    # 检查可升级包
pip install --upgrade -r requirements.txt  # 升级依赖
python scripts/health_check.py         # 健康检查
```

## 13. 应急预案

### 13.1 服务不可用

**症状**：Web界面无法访问
**排查**：
1. 检查Streamlit进程是否运行
2. 检查端口是否被占用：`netstat -an | findstr 8501`
3. 重新启动：`streamlit run app/streamlit_app.py`

### 13.2 查询返回空结果

**症状**：所有查询返回"未找到相关文档"
**排查**：
1. 检查是否有数据：`python run.py stats`
2. 重新索引：`python run.py index --reset`
3. 测试简单查询：`python run.py query "的"`

### 13.3 嵌入模型不可用

**症状**：索引时提示模型加载失败
**应急方案**：
1. 切换为ChromaDB默认嵌入：修改 `config/settings.py` 中 EMBEDDING_MODEL
2. 或使用OpenAI API嵌入（需API Key）

### 13.4 磁盘空间不足

**症状**：索引或查询时报磁盘错误
**应急方案**：
1. 清理ChromaDB：`python run.py reset`
2. 删除旧的备份文件
3. 使用ChromaDB内存模式（不持久化）

## 14. 联系与支持

| 问题类型 | 处理方式 |
|---------|---------|
| 配置问题 | 检查 config/settings.py |
| 使用问题 | 查看 README.md |
| 架构问题 | 查看 docs/architecture.md |
| 技术选型 | 查看 docs/design_decisions.md |
| 系统故障 | 参照本文档故障排查章节 |
