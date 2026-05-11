"""
test_query_parser.py
====================
对 query_parser 模块的单元测试（使用 mock 避免真实 API 调用）。
"""

import json
from unittest.mock import MagicMock, patch


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

        from src.query_parser import parse_query
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

        from src.query_parser import parse_query
        result = parse_query("什么是向量数据库", client=mock_client.return_value)

        assert result["search_query"] == "什么是向量数据库"
        assert result["filters"] is None

    @patch("src.query_parser.get_openai_client")
    @patch("src.query_parser.get_model_name")
    def test_api_failure_fallback(self, mock_model, mock_client):
        mock_model.return_value = "test-model"
        mock_client.return_value.chat.completions.create.side_effect = Exception("API Error")

        from src.query_parser import parse_query
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

        from src.query_parser import parse_query
        result = parse_query("测试", client=mock_client.return_value)

        # 应降级为原始问题
        assert result["search_query"] == "测试"
