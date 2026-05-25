"""
检索器 - 语义搜索 + 元数据过滤
"""
from typing import List, Dict, Optional

from .query_parser import QueryParser
from config.settings import SIMILARITY_THRESHOLD


class Retriever:
    """检索器，用于从向量数据库中检索相关文档"""
    
    def __init__(self, chroma_manager, embedder, top_k: int = 5,
                 similarity_threshold: float = None):
        """
        初始化检索器
        
        Args:
            chroma_manager: ChromaDB管理器
            embedder: 嵌入生成器
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
        """
        self.chroma = chroma_manager
        self.embedder = embedder
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold or SIMILARITY_THRESHOLD
        self.parser = QueryParser()
    
    def retrieve(self, query: str, filters: Dict = None) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 用户查询
            filters: 元数据过滤条件
            
        Returns:
            检索结果列表
        """
        # 生成查询向量
        query_embedding = self.embedder.embed_text(query)
        
        # 执行查询
        results = self.chroma.query(
            query_embedding=query_embedding,
            n_results=self.top_k,
            where=filters
        )
        
        # 格式化结果
        return self._format_results(results)
    
    def retrieve_with_query_parsing(self, query: str) -> List[Dict]:
        """
        使用查询解析进行检索
        
        Args:
            query: 用户查询
            
        Returns:
            检索结果列表
        """
        # 解析查询
        parsed = self.parser.parse(query)
        
        # 构建ChromaDB兼容的where子句
        chroma_where = self._build_chroma_where(parsed.get('filters'))
        
        # 执行检索
        return self.retrieve(
            query=parsed['query'],
            filters=chroma_where
        )
    
    def _build_chroma_where(self, filters: dict) -> dict:
        """将解析后的过滤条件转换为ChromaDB兼容的where子句"""
        if not filters:
            return None
        
        conditions = []
        
        for field, value in filters.items():
            if isinstance(value, dict):
                # 范围查询（如日期的 $gte/$lt）
                for op, val in value.items():
                    conditions.append({field: {op: val}})
            else:
                # 精确匹配
                conditions.append({field: value})
        
        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def _format_results(self, results: Dict) -> List[Dict]:
        """格式化查询结果（按相似度阈值过滤）"""
        formatted = []
        
        if not results or not results.get('ids') or not results['ids'][0]:
            return formatted
        
        ids = results['ids'][0]
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        for i in range(len(ids)):
            # ChromaDB cosine distance ∈ [0, 2]，score = 1 - distance
            score = max(0.0, 1 - distances[i])
            
            if score < self.similarity_threshold:
                continue
            
            formatted.append({
                'chunk_id': ids[i],
                'text': documents[i] if i < len(documents) else '',
                'metadata': metadatas[i] if i < len(metadatas) else {},
                'score': score,
            })
        
        return formatted
    
    def retrieve_by_metadata(self, filters: Dict, limit: int = None) -> List[Dict]:
        """
        仅通过元数据检索
        
        Args:
            filters: 元数据过滤条件
            limit: 返回数量限制
            
        Returns:
            检索结果列表
        """
        results = self.chroma.get(where=filters)
        
        formatted = []
        for i in range(len(results['ids'])):
            formatted.append({
                'chunk_id': results['ids'][i],
                'text': results['documents'][i] if i < len(results.get('documents', [])) else '',
                'metadata': results['metadatas'][i] if i < len(results.get('metadatas', [])) else {},
                'score': 1.0,  # 元数据查询没有相似度分数
            })
        
        if limit:
            formatted = formatted[:limit]
        
        return formatted


if __name__ == "__main__":
    from src.retrieval.query_parser import QueryParser
    from src.embedding import Embedder
    from src.storage import ChromaManager

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
