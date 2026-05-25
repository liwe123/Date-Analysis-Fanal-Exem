"""
ChromaDB管理器 - 管理向量数据库的存储和查询
"""
import logging
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaManager:
    """ChromaDB管理器，用于存储和查询向量"""
    
    def __init__(self, db_path: str = None, collection_name: str = "documents"):
        """
        初始化ChromaDB管理器
        
        Args:
            db_path: 数据库路径（None表示使用内存模式）
            collection_name: 集合名称
        """
        self.db_path = db_path
        self.collection_name = collection_name
        
        # 初始化客户端
        if db_path:
            self.client = chromadb.PersistentClient(path=db_path)
        else:
            self.client = chromadb.Client()
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("ChromaDB初始化完成 (集合: %s, 文档数: %d)", collection_name, self.count())
    
    def add_documents(self, ids: List[str], embeddings: List[List[float]], 
                     metadatas: List[Dict], documents: List[str]):
        """
        添加文档到集合
        
        Args:
            ids: 文档ID列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表
            documents: 文档文本列表
        """
        if not ids:
            return
        
        # ChromaDB要求元数据值为基本类型
        cleaned_metadatas = self._clean_metadatas(metadatas)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=cleaned_metadatas,
            documents=documents
        )
        
        logger.info("已添加 %d 个文档", len(ids))
    
    def _clean_metadatas(self, metadatas: List[Dict]) -> List[Dict]:
        """清理元数据，确保值为基本类型"""
        cleaned = []
        
        for metadata in metadatas:
            cleaned_metadata = {}
            for key, value in metadata.items():
                # 只保留基本类型
                if isinstance(value, (str, int, float, bool)):
                    cleaned_metadata[key] = value
                elif value is None:
                    cleaned_metadata[key] = ""
                else:
                    cleaned_metadata[key] = str(value)
            
            cleaned.append(cleaned_metadata)
        
        return cleaned
    
    def query(self, query_embedding: List[float], n_results: int = 5, 
             where: Dict = None) -> Dict:
        """
        查询相似文档
        
        Args:
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 元数据过滤条件
            
        Returns:
            查询结果
        """
        current_count = self.count()
        if current_count == 0:
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, current_count),
        }
        
        if where:
            query_params["where"] = where
        
        results = self.collection.query(**query_params)
        
        return results
    
    def query_by_text(self, query_text: str, n_results: int = 5, 
                     where: Dict = None) -> Dict:
        """
        通过文本查询（使用ChromaDB默认嵌入）
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            where: 元数据过滤条件
            
        Returns:
            查询结果
        """
        query_params = {
            "query_texts": [query_text],
            "n_results": min(n_results, self.count()),
        }
        
        if where:
            query_params["where"] = where
        
        results = self.collection.query(**query_params)
        
        return results
    
    def count(self) -> int:
        """获取集合中的文档数量"""
        return self.collection.count()
    
    def delete(self, ids: List[str]):
        """删除指定文档"""
        self.collection.delete(ids=ids)
        logger.info("已删除 %d 个文档", len(ids))
    
    def delete_all(self):
        """删除所有文档"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("已清空并重建集合")
        except Exception as e:
            logger.error("清空集合失败: %s", e)
    
    def get(self, ids: List[str] = None, where: Dict = None) -> Dict:
        """
        获取文档
        
        Args:
            ids: 文档ID列表
            where: 元数据过滤条件
            
        Returns:
            文档数据
        """
        get_params = {}
        
        if ids:
            get_params['ids'] = ids
        
        if where:
            get_params['where'] = where
        
        return self.collection.get(**get_params)
    
    def update(self, ids: List[str], embeddings: List[List[float]] = None,
              metadatas: List[Dict] = None, documents: List[str] = None):
        """更新文档"""
        update_params = {'ids': ids}
        
        if embeddings:
            update_params['embeddings'] = embeddings
        
        if metadatas:
            update_params['metadatas'] = self._clean_metadatas(metadatas)
        
        if documents:
            update_params['documents'] = documents
        
        self.collection.update(**update_params)
        logger.info("已更新 %d 个文档", len(ids))
    
    def peek(self, n: int = 5) -> Dict:
        """预览集合中的文档"""
        return self.collection.peek(n)
    
    def get_stats(self) -> Dict:
        """获取集合统计信息"""
        count = self.count()
        
        if count == 0:
            return {
                'collection_name': self.collection_name,
                'total_documents': 0,
                'db_path': self.db_path,
            }
        
        # 获取样本数据
        sample = self.peek(min(5, count))
        
        return {
            'collection_name': self.collection_name,
            'total_documents': count,
            'db_path': self.db_path,
            'sample_ids': sample.get('ids', []),
        }


if __name__ == "__main__":
    # 测试ChromaDB管理器
    print("测试ChromaDB管理器:")
    
    # 使用内存模式
    manager = ChromaManager(db_path=None, collection_name="test_collection")
    
    # 测试添加文档
    test_ids = ["doc_001", "doc_002", "doc_003"]
    test_embeddings = [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.2, 0.3, 0.4, 0.5, 0.6],
        [0.3, 0.4, 0.5, 0.6, 0.7],
    ]
    test_metadatas = [
        {"title": "文档1", "author": "张三", "category": "Python"},
        {"title": "文档2", "author": "李四", "category": "Java"},
        {"title": "文档3", "author": "王五", "category": "Python"},
    ]
    test_documents = [
        "Python是一种高级编程语言",
        "Java是一种面向对象编程语言",
        "Python支持多种编程范式",
    ]
    
    print("\n1. 添加文档:")
    manager.add_documents(test_ids, test_embeddings, test_metadatas, test_documents)
    
    # 测试查询
    print("\n2. 查询相似文档:")
    query_embedding = [0.15, 0.25, 0.35, 0.45, 0.55]
    results = manager.query(query_embedding, n_results=2)
    
    for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
        print(f"  结果 {i + 1}: ID={doc_id}, 距离={distance:.4f}")
    
    # 测试元数据过滤
    print("\n3. 元数据过滤查询:")
    results = manager.query(query_embedding, n_results=2, where={"category": "Python"})
    
    for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
        print(f"  结果 {i + 1}: ID={doc_id}, 距离={distance:.4f}")
    
    # 测试统计信息
    print("\n4. 统计信息:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 测试删除
    print("\n5. 删除文档:")
    manager.delete(["doc_001"])
    print(f"  删除后文档数: {manager.count()}")
