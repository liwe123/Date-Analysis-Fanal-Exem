"""
test_query_parser.py
====================
对 query_parser 模块的单元测试（使用 mock 避免真实 API 调用）。
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.query_parser import parse_query


class TestParseQuery:
    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_normal_parse(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "search_query": "RAG 检索增强生成",
            "filters": {"year": 2024, "category": "wiki"}
        })
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = parse_query("2024年关于RAG的wiki文档", client=mock_client.return_value)

        assert result["search_query"] == "RAG 检索增强生成"
        assert result["filters"]["year"] == 2024
        assert result["filters"]["category"] == "wiki"

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_all_null_filters(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "search_query": "什么是向量数据库",
            "filters": {"year": None, "category": None, "author": None, "language": None}
        })
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = parse_query("什么是向量数据库", client=mock_client.return_value)

        assert result["search_query"] == "什么是向量数据库"
        assert result["filters"] is None

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_ignores_inferred_language_filter(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "search_query": "token用尽处理方法",
            "filters": {"year": None, "category": None, "author": None, "language": "zh"}
        })
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = parse_query("token用完之后怎么办", client=mock_client.return_value)

        assert result["search_query"] == "token用尽处理方法"
        assert result["filters"] is None
        assert result["raw_filters"]["language"] == "zh"

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_api_failure_fallback(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_client.return_value.chat.completions.create.side_effect = Exception("API Error")

        question = "测试问题"
        result = parse_query(question, client=mock_client.return_value)

        assert result["search_query"] == question
        assert result["filters"] is None

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_malformed_json_fallback(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "这不是JSON"
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = parse_query("测试", client=mock_client.return_value)

        # 应降级为原始问题
        assert result["search_query"] == "测试"

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_markdown_codeblock_parsing(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        # 返回带 ```json 标记的 Markdown 代码块
        mock_resp.choices[0].message.content = "```json\n{\n  \"search_query\": \"Hadoop\",\n  \"filters\": {\"year\": 2026}\n}\n```"
        mock_client.return_value.chat.completions.create.return_value = mock_resp

        result = parse_query("Hadoop in 2026", client=mock_client.return_value)
        assert result["search_query"] == "Hadoop"
        assert result["filters"]["year"] == 2026
        assert result["raw_filters"]["year"] == 2026
