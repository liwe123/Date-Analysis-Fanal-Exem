"""
conftest.py
===========
Pytest 共享配置：添加项目根目录到 sys.path，使所有测试可通过 `from src.xxx` 导入。
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
