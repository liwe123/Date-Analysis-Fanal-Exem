"""
rendering.py
============
Streamlit 页面安全渲染辅助函数。
"""

from __future__ import annotations

import html


def safe_text_to_html(text: str) -> str:
    """将普通文本安全转换为可放入 HTML 气泡的内容。"""
    return html.escape(text).replace("\n", "<br>")
