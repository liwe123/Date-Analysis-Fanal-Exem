"""
查询流水线 - 完整的查询流程
"""
import logging
from typing import Dict, List, Optional

from src.retrieval import Retriever, QueryParser
from src.generation import LLMClient, AnswerGenerator
from src.embedding import Embedder
from src.storage import ChromaManager

logger = logging.getLogger(__name__)


class QueryPipeline:
    """查询流水线，执行完整的查询流程"""
    
    def __init__(self, chroma_manager: ChromaManager, embedder: Embedder,
                 llm_client: LLMClient = None, top_k: int = 5):
        """
        初始化查询流水线
        
        Args:
            chroma_manager: ChromaDB管理器
            embedder: 嵌入生成器
            llm_client: LLM客户端（可选）
            top_k: 返回结果数量
        """
        self.chroma = chroma_manager
        self.embedder = embedder
        self.retriever = Retriever(chroma_manager, embedder, top_k)
        self.parser = QueryParser()
        self.generator = AnswerGenerator(llm_client)
    
    def run(self, query: str, filters: Dict = None, top_k: int = None) -> Dict:
        """
        执行完整的查询流程
        
        Args:
            query: 用户查询
            filters: 元数据过滤条件
            top_k: 返回结果数量（覆盖默认值）
            
        Returns:
            查询结果
        """
        logger.info("执行查询: %s", query)

        if top_k is not None:
            self.retriever.top_k = top_k
        
        # 1. 检索相关文档
        if filters:
            chunks = self.retriever.retrieve(query, filters)
        else:
            chunks = self.retriever.retrieve_with_query_parsing(query)
        
        logger.info("检索到 %d 个相关文档", len(chunks))
        
        # 2. 生成答案
        result = self.generator.generate(query, chunks)
        
        return result
    
    def retrieve_only(self, query: str, filters: Dict = None) -> List[Dict]:
        """
        仅执行检索（不生成答案）
        
        Args:
            query: 用户查询
            filters: 元数据过滤条件
            
        Returns:
            检索结果列表
        """
        if filters:
            return self.retriever.retrieve(query, filters)
        else:
            return self.retriever.retrieve_with_query_parsing(query)
    
    def search_by_metadata(self, filters: Dict, limit: int = 10) -> List[Dict]:
        """
        通过元数据搜索
        
        Args:
            filters: 元数据过滤条件
            limit: 返回数量限制
            
        Returns:
            搜索结果列表
        """
        return self.retriever.retrieve_by_metadata(filters, limit)
    
    def get_similar_documents(self, chunk_id: str, n_results: int = 5) -> List[Dict]:
        """
        获取与指定chunk相似的文档
        
        Args:
            chunk_id: chunk ID
            n_results: 返回结果数量
            
        Returns:
            相似文档列表
        """
        # 获取指定chunk
        results = self.chroma.get(ids=[chunk_id])
        
        if not results['ids']:
            return []
        
        # 使用该chunk的文本进行查询
        text = results['documents'][0]
        return self.retriever.retrieve(text, n_results=n_results)
    
    def get_stats(self) -> Dict:
        """获取查询流水线统计信息"""
        return {
            'chroma_stats': self.chroma.get_stats(),
            'top_k': self.retriever.top_k,
            'llm_available': self.generator.llm is not None and self.generator.llm.is_available(),
        }


if __name__ == "__main__":
    # 测试查询流水线
    from src.pipeline.indexing_pipeline import IndexingPipeline
    from config.settings import RAW_DATA_DIR
    
    print("测试查询流水线:")
    
    # 先执行索引
    print("\n1. 执行索引:")
    indexing_pipeline = IndexingPipeline(
        db_path=None,
        collection_name="test_collection",
        metadata_csv_path=str(Path(__file__).parent.parent.parent / "data" / "raw" / "metadata.csv")
    )
    
    indexing_pipeline.run(str(RAW_DATA_DIR), reset=True)
    
    # 创建查询流水线
    print("\n2. 创建查询流水线:")
    query_pipeline = QueryPipeline(
        chroma_manager=indexing_pipeline.chroma,
        embedder=indexing_pipeline.embedder,
        top_k=3
    )
    
    # 测试查询
    test_queries = [
        "什么是Python？",
        "如何定义函数？",
        "Pandas如何读取CSV文件？",
    ]
    
    print("\n3. 测试查询:")
    for query in test_queries:
        print(f"\n查询: {query}")
        result = query_pipeline.run(query)
        
        print(f"答案预览: {result['answer'][:200]}...")
        print(f"来源数量: {len(result['sources'])}")
    
    # 测试元数据过滤查询
    print("\n4. 测试元数据过滤查询:")
    result = query_pipeline.run("关于Python的文档", filters={"category": "Python"})
    print(f"过滤查询结果数量: {len(result['sources'])}")
