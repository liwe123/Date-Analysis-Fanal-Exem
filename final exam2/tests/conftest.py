"""
conftest.py
===========
Pytest 共享配置与 Fixtures。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根目录到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@pytest.fixture
def mock_store_deps():
    """Mock VectorStore 依赖的 chromadb 和环境变量。"""
    with patch("src.embed_store.chromadb.PersistentClient") as mock_client, \
         patch("src.embed_store.get_openai_client") as mock_openai, \
         patch("src.embed_store.use_local_embedding", return_value=False), \
         patch("src.embed_store.clean_env", return_value=""):
        yield mock_client, mock_openai


@pytest.fixture
def sample_doc() -> dict:
    """返回一个测试用的标准清洗前文档字典。"""
    return {
        "source": "test_doc.md",
        "path": "/mock/path/test_doc.md",
        "text": "---\nauthor: Alice\nyear: 2026\ncategory: notice\n---\nHello World!",
        "fm_meta": {"author": "Alice", "year": 2026, "category": "notice"}
    }


@pytest.fixture
def mock_openai_client():
    """提供一个完全 Mock 的 OpenAI 客户端，模拟 chat.completions.create 行为。"""
    client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"author": "Bob", "year": 2025, "category": "wiki", "language": "zh", "summary": "test"}'
    client.chat.completions.create.return_value.choices = [mock_choice]
    return client
