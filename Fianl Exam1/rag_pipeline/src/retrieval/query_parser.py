"""
查询解析器 - 从自然语言中提取过滤条件
"""
import re
from typing import Dict, Optional


class QueryParser:
    """查询解析器，从自然语言中提取过滤条件"""

    DATE_PATTERNS = [
        (r'(\d{4})年', lambda m: {'$gte': f'{m.group(1)}-01-01', '$lt': f'{int(m.group(1)) + 1}-01-01'}),
        (r'(\d{4})-(\d{2})', lambda m: {'$gte': f'{m.group(1)}-{m.group(2)}-01', '$lt': f'{m.group(1)}-{int(m.group(2)) + 1:02d}-01'}),
    ]

    AUTHOR_PATTERNS = [
        r'作者是(.+?)的',
        r'(.+?)写的',
        r'(.+?)的文档',
    ]

    CATEGORY_PATTERNS = [
        r'关于(.+?)的',
        r'(.+?)相关',
        r'(.+?)类',
        r'(.+?)领域',
    ]

    def parse(self, query: str) -> Dict:
        """
        解析查询，提取搜索词和过滤条件

        Args:
            query: 用户查询

        Returns:
            解析结果，包含：
            - query: 搜索词
            - filters: 过滤条件
        """
        result = {
            'query': query,
            'filters': None,
        }

        filters = {}

        date_filter = self._extract_date_filter(query)
        if date_filter:
            filters['date'] = date_filter

        author_filter = self._extract_author_filter(query)
        if author_filter:
            filters['author'] = author_filter

        category_filter = self._extract_category_filter(query)
        if category_filter:
            filters['category'] = category_filter

        if filters:
            result['filters'] = filters

        return result

    def _extract_date_filter(self, query: str) -> Optional[Dict]:
        """提取日期过滤条件"""
        for pattern, handler in self.DATE_PATTERNS:
            match = re.search(pattern, query)
            if match:
                return handler(match)
        return None

    def _extract_author_filter(self, query: str) -> Optional[str]:
        """提取作者过滤条件"""
        for pattern in self.AUTHOR_PATTERNS:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        return None

    def _extract_category_filter(self, query: str) -> Optional[str]:
        """提取类别过滤条件"""
        for pattern in self.CATEGORY_PATTERNS:
            match = re.search(pattern, query)
            if match:
                category = match.group(1).strip()
                if category not in ['什么', '如何', '怎么', '哪些', '这个', '那个']:
                    return category
        return None


if __name__ == "__main__":
    parser = QueryParser()

    test_queries = [
        "Python的列表和元组有什么区别？",
        "查找2024年的文档",
        "作者是张三的文档",
        "关于机器学习的文档",
        "2024年关于Python的文档",
    ]

    print("测试查询解析器:")
    for query in test_queries:
        result = parser.parse(query)
        print(f"\n查询: {query}")
        print(f"  搜索词: {result['query']}")
        print(f"  过滤条件: {result['filters']}")
