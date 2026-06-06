"""
test_rendering.py
=================
对 Streamlit 安全渲染辅助函数的单元测试。
"""

from __future__ import annotations

from app.rendering import safe_text_to_html


class TestSafeTextToHtml:
    def test_escapes_html_tags(self):
        assert safe_text_to_html("<script>alert(1)</script>") == (
            "&lt;script&gt;alert(1)&lt;/script&gt;"
        )

    def test_preserves_line_breaks(self):
        assert safe_text_to_html("第一行\n第二行") == "第一行<br>第二行"
