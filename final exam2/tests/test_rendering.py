"""
test_rendering.py
=================
对 Streamlit 安全渲染辅助函数的单元测试。
"""

from __future__ import annotations

from app.rendering import safe_markdown_to_html, safe_text_to_html


class TestSafeTextToHtml:
    def test_escapes_html_tags(self):
        assert safe_text_to_html("<script>alert(1)</script>") == (
            "&lt;script&gt;alert(1)&lt;/script&gt;"
        )

    def test_preserves_line_breaks(self):
        assert safe_text_to_html("第一行\n第二行") == "第一行<br>第二行"


class TestSafeMarkdownToHtml:
    def test_renders_common_markdown_and_table(self):
        rendered = safe_markdown_to_html(
            "### 标题\n\n**重点**\n\n| 错误 | 处理 |\n|---|---|\n| 429 | 重试 |"
        )

        assert "<h3>标题</h3>" in rendered
        assert "<strong>重点</strong>" in rendered
        assert "<table>" in rendered
        assert '<div class="markdown-table">' in rendered
        assert "<td>429</td>" in rendered

    def test_allows_only_escaped_line_break_tags(self):
        rendered = safe_markdown_to_html("第一步<br>第二步<script>alert(1)</script>")

        assert "第一步<br>第二步" in rendered
        assert "<script>" not in rendered

    def test_escapes_raw_html(self):
        rendered = safe_markdown_to_html("<script>alert(1)</script>")

        assert "<script>" not in rendered
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
