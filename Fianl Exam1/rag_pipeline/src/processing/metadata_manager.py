"""
元数据管理器 - 为每个chunk生成唯一ID和关联元数据
"""
import hashlib
from typing import List, Dict, Optional
from pathlib import Path


class MetadataManager:
    """元数据管理器，为每个chunk生成唯一ID和关联元数据"""
    
    def __init__(self):
        """初始化元数据管理器"""
        pass
    
    def generate_chunk_id(self, file_name: str, chunk_index: int) -> str:
        """
        生成chunk的唯一ID
        
        Args:
            file_name: 文件名
            chunk_index: chunk索引
            
        Returns:
            唯一ID，格式: {文件名}_chunk_{索引}
        """
        # 移除文件扩展名
        stem = Path(file_name).stem
        
        # 生成ID
        chunk_id = f"{stem}_chunk_{chunk_index:04d}"
        
        return chunk_id
    
    def generate_chunk_ids(self, file_name: str, chunk_count: int) -> List[str]:
        """
        批量生成chunk ID
        
        Args:
            file_name: 文件名
            chunk_count: chunk数量
            
        Returns:
            ID列表
        """
        return [self.generate_chunk_id(file_name, i) for i in range(chunk_count)]
    
    def create_chunk_metadata(self, file_metadata: Dict, chunk_index: int, 
                             total_chunks: int, chunk_text: str,
                             char_offset: int = 0) -> Dict:
        """
        为单个chunk创建元数据
        
        Args:
            file_metadata: 文件级别的元数据
            chunk_index: chunk索引
            total_chunks: 总chunk数
            chunk_text: chunk文本
            char_offset: 在原文件中的字符偏移量
            
        Returns:
            chunk元数据字典
        """
        # 复制文件元数据
        chunk_metadata = file_metadata.copy()
        
        # 添加chunk特定信息
        chunk_metadata.update({
            'chunk_id': self.generate_chunk_id(file_metadata.get('file_name', ''), chunk_index),
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'chunk_size': len(chunk_text),
            'char_offset': char_offset,
        })
        
        # 确保所有必要字段存在
        chunk_metadata.setdefault('file_name', '')
        chunk_metadata.setdefault('title', '')
        chunk_metadata.setdefault('author', '')
        chunk_metadata.setdefault('date', '')
        chunk_metadata.setdefault('category', '')
        
        return chunk_metadata
    
    def create_batch_metadata(self, file_metadata: Dict, chunks: List[str]) -> List[Dict]:
        """
        批量创建chunk元数据（计算准确的字符偏移量）
        
        Args:
            file_metadata: 文件级别的元数据
            chunks: chunk文本列表
            
        Returns:
            chunk元数据列表
        """
        total_chunks = len(chunks)
        metadata_list = []
        offset = 0
        
        for i, chunk in enumerate(chunks):
            metadata = self.create_chunk_metadata(
                file_metadata, i, total_chunks, chunk, char_offset=offset
            )
            metadata_list.append(metadata)
            offset += len(chunk)
        
        return metadata_list
    
    def merge_metadata(self, base_metadata: Dict, additional_metadata: Dict) -> Dict:
        """
        合并元数据
        
        Args:
            base_metadata: 基础元数据
            additional_metadata: 额外元数据
            
        Returns:
            合并后的元数据
        """
        merged = base_metadata.copy()
        merged.update(additional_metadata)
        return merged
    
    def filter_metadata_for_storage(self, metadata: Dict) -> Dict:
        """
        过滤元数据，只保留适合存储的字段
        
        Args:
            metadata: 原始元数据
            
        Returns:
            过滤后的元数据
        """
        # 定义适合存储的字段
        storage_fields = {
            'chunk_id', 'file_name', 'title', 'author', 'date', 
            'category', 'chunk_index', 'total_chunks', 'chunk_size',
            'file_extension', 'source'
        }
        
        return {k: v for k, v in metadata.items() if k in storage_fields}
    
    def validate_metadata(self, metadata: Dict) -> bool:
        """
        验证元数据是否完整
        
        Args:
            metadata: 元数据字典
            
        Returns:
            是否有效
        """
        required_fields = ['chunk_id', 'file_name']
        
        for field in required_fields:
            if field not in metadata:
                return False
            
            value = metadata[field]
            if not value or (isinstance(value, str) and not value.strip()):
                return False
        
        return True
    
    def get_metadata_summary(self, metadata_list: List[Dict]) -> Dict:
        """
        获取元数据统计摘要
        
        Args:
            metadata_list: 元数据列表
            
        Returns:
            统计摘要
        """
        if not metadata_list:
            return {}
        
        # 统计信息
        total_chunks = len(metadata_list)
        files = set()
        authors = set()
        categories = set()
        
        for metadata in metadata_list:
            files.add(metadata.get('file_name', ''))
            authors.add(metadata.get('author', ''))
            categories.add(metadata.get('category', ''))
        
        return {
            'total_chunks': total_chunks,
            'total_files': len(files),
            'unique_authors': len(authors),
            'unique_categories': len(categories),
            'files': list(files),
            'authors': list(authors),
            'categories': list(categories),
        }


if __name__ == "__main__":
    # 测试元数据管理器
    manager = MetadataManager()
    
    # 模拟文件元数据
    file_metadata = {
        'file_name': 'doc_001_python_basics.txt',
        'title': 'Python编程语言入门指南',
        'author': '张三',
        'date': '2024-01-15',
        'category': 'Python基础',
        'file_extension': '.txt',
    }
    
    # 模拟chunks
    chunks = [
        "Python是一种高级编程语言，由Guido van Rossum于1991年创建。",
        "Python的设计哲学强调代码的可读性和简洁性。",
        "Python的主要特点包括：简洁易读的语法、动态类型系统等。",
    ]
    
    # 测试批量创建元数据
    metadata_list = manager.create_batch_metadata(file_metadata, chunks)
    
    print("测试元数据管理器:")
    for i, metadata in enumerate(metadata_list):
        print(f"\n--- Chunk {i + 1} ---")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    
    # 测试统计摘要
    summary = manager.get_metadata_summary(metadata_list)
    print("\n--- 统计摘要 ---")
    for key, value in summary.items():
        print(f"  {key}: {value}")
