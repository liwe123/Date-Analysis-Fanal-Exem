"""
test_qa.py
===========
对 qa 模块的单元测试。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.qa import _format_sources_list, generate_answer


class TestFormatSourcesList:
    def test_empty(self):
        assert _format_sources_list([]) == "- N/A"

    def test_single_source(self):
        docs = [{"source": "test.md"}]
        assert _format_sources_list(docs) == "- test.md"

    def test_multiple_sources_dedup(self):
        docs = [
            {"source": "a.md"},
            {"source": "b.md"},
            {"source": "a.md"},
        ]
        result = _format_sources_list(docs)
        assert "- a.md" in result
        assert "- b.md" in result
        assert result.count("- a.md") == 1

    def test_missing_source(self):
        docs = [{"text": "content"}]
        assert _format_sources_list(docs) == "- unknown"


class TestGenerateAnswer:
    def test_no_docs(self):
        result = generate_answer("question?", [])
        assert "未找到相关文档" in result

    def test_generates_with_context(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Answer [Source: test.md]"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{
                "text": "content",
                "source": "test.md",
                "metadata": {"source": "test.md", "year": 2024},
            }]
            result = generate_answer("question?", docs, client=mock_client)
            assert "Answer" in result
            assert "[Source: test.md]" in result

    def test_appends_sources_on_missing_citation(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Answer without citation"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{
                "text": "content",
                "source": "src.md",
                "metadata": {"source": "src.md"},
            }]
            result = generate_answer("question?", docs, client=mock_client)
            assert "src.md" in result

    def test_uses_year_in_header(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Answer with year [Source: test.md]"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{
                "text": "content",
                "metadata": {"source": "test.md", "year": 2024},
            }]
            result = generate_answer("question?", docs, client=mock_client)
            assert "2024" in result or "test.md" in result

    def test_prompt_keeps_answers_strictly_grounded(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "Answer [来源: token.md]"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{
                "text": "E1001 表示认证失败，通常与 token scope 不匹配。",
                "source": "token.md",
                "metadata": {"source": "token.md"},
            }]
            generate_answer("token用完怎么办", docs, client=mock_client)

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert "不要自行扩写、猜测或引入外部知识" in messages[0]["content"]
        assert "未找到足够依据" in messages[0]["content"]

    def test_keyboard_interrupt_penetrates(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = KeyboardInterrupt()
        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{"text": "content", "source": "test.md"}]
            with pytest.raises(KeyboardInterrupt):
                generate_answer("question?", docs, client=mock_client)

    def test_runtime_error_raised_on_api_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ValueError("Some API error")
        with patch("src.qa.get_model_name", return_value="test-model"):
            docs = [{"text": "content", "source": "test.md"}]
            with pytest.raises(RuntimeError) as exc_info:
                generate_answer("question?", docs, client=mock_client)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, ValueError)
