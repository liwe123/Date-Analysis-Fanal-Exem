"""
rendering.py
============
Streamlit 页面安全渲染辅助函数。
"""

from __future__ import annotations

import html

from markdown_it import MarkdownIt

MARKDOWN_RENDERER = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "breaks": True,
        "linkify": False,
    },
).enable("table")


def safe_text_to_html(text: str) -> str:
    """将普通文本安全转换为可放入 HTML 气泡的内容。"""
    return html.escape(text).replace("\n", "<br>")


def safe_markdown_to_html(text: str) -> str:
    """将 Markdown 安全渲染为 HTML，并禁用原始 HTML 标签。"""
    rendered = MARKDOWN_RENDERER.render(text)
    for escaped_break in ("&lt;br&gt;", "&lt;br/&gt;", "&lt;br /&gt;"):
        rendered = rendered.replace(escaped_break, "<br>")
    return rendered.replace(
        "<table>",
        '<div class="markdown-table"><table>',
    ).replace("</table>", "</table></div>")
