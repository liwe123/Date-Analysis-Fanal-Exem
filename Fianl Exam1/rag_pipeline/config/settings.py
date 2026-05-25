"""
RAG Pipeline 全局配置
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件 (优先项目根目录，其次config目录)
env_path = Path(__file__).parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "documents"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"


def ensure_directories():
    """确保所有必要目录存在"""
    for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DIR, CHUNKS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

# 嵌入模型配置
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 免费本地模型
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2的维度

# ChromaDB配置
CHROMA_DB_PATH = str(PROJECT_ROOT / "chroma_db")
CHROMA_COLLECTION_NAME = "documents"

# 分块配置
CHUNK_SIZE = 500         # 每个块的目标字符数
CHUNK_OVERLAP = 50       # 块之间的重叠字符数

# 检索配置
TOP_K = 5                # 返回前K个结果
SIMILARITY_THRESHOLD = 0.3  # 相似度阈值（cosine distance空间下，0.3更合理）

# LLM配置（可选，用于答案生成）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-3.5-turbo"

# 支持的文件格式
SUPPORTED_EXTENSIONS = {".txt", ".html", ".htm", ".pdf"}

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str = None):
    """初始化全局日志配置"""
    logging.basicConfig(
        level=getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器"""
    return logging.getLogger(name)
