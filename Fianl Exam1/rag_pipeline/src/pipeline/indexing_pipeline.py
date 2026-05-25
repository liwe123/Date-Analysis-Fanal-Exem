"""
索引流水线 - 完整的文档索引流程
"""
import logging
from typing import Dict, List
from pathlib import Path

from tqdm import tqdm

from src.ingestion import FileScanner, PDFReader, TXTReader, HTMLReader, MetadataExtractor
from src.processing import TextCleaner, TextChunker, MetadataManager
from src.embedding import Embedder
from src.storage import ChromaManager
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """索引流水线，执行完整的文档索引流程"""
    
    def __init__(self, db_path: str = None, collection_name: str = "documents",
                 chunk_size: int = None, chunk_overlap: int = None,
                 embedding_backend: str = 'sentence-transformers',
                 metadata_csv_path: str = None):
        """
        初始化索引流水线
        
        Args:
            db_path: ChromaDB数据库路径
            collection_name: 集合名称
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            embedding_backend: 嵌入后端
            metadata_csv_path: 元数据CSV文件路径
        """
        # 初始化组件
        self.file_scanner = FileScanner()
        self.pdf_reader = PDFReader()
        self.txt_reader = TXTReader()
        self.html_reader = HTMLReader()
        self.text_cleaner = TextCleaner()
        self.text_chunker = TextChunker(
            chunk_size=chunk_size or CHUNK_SIZE,
            chunk_overlap=chunk_overlap or CHUNK_OVERLAP
        )
        self.metadata_manager = MetadataManager()
        self.metadata_extractor = MetadataExtractor(metadata_csv_path)
        self.embedder = Embedder(backend=embedding_backend, model_name=EMBEDDING_MODEL)
        self.chroma = ChromaManager(db_path=db_path, collection_name=collection_name)
    
    def run(self, data_dir: str, reset: bool = False) -> Dict:
        """
        执行完整的索引流程
        
        Args:
            data_dir: 数据目录路径
            reset: 是否重置数据库
            
        Returns:
            索引结果统计
        """
        logger.info("开始索引流程 (目录: %s)", data_dir)
        
        # 重置数据库
        if reset:
            logger.info("重置数据库...")
            self.chroma.delete_all()
        
        # 1. 扫描文件
        files = self.file_scanner.scan(data_dir)
        logger.info("发现 %d 个文件", len(files))
        
        if not files:
            logger.warning("没有找到可处理的文件")
            return {'total_files': 0, 'total_chunks': 0, 'collection_count': 0}
        
        total_chunks = 0
        
        # 2. 逐文件处理（流式：读取→分块→嵌入→存储）
        for file_info in tqdm(files, desc="处理文件", unit="file"):
            try:
                chunks, metadata_list = self._process_file(file_info)
                
                if not chunks:
                    continue
                
                # 生成chunk ID
                ids = []
                for i in range(len(chunks)):
                    file_name = metadata_list[i].get('file_name', 'unknown')
                    chunk_id = self.metadata_manager.generate_chunk_id(
                        file_name, metadata_list[i].get('chunk_index', i)
                    )
                    ids.append(chunk_id)
                
                # 生成嵌入向量
                embeddings = self.embedder.embed_batch(chunks)
                
                # 存入ChromaDB
                self.chroma.add_documents(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadata_list,
                    documents=chunks
                )
                
                total_chunks += len(chunks)
                
            except Exception as e:
                logger.error("处理文件失败 %s: %s", file_info['name'], e)
                continue
        
        logger.info("共生成 %d 个文本块", total_chunks)
        
        # 返回统计信息
        result = {
            'total_files': len(files),
            'total_chunks': total_chunks,
            'collection_count': self.chroma.count(),
        }
        
        logger.info("索引完成: %s", result)
        return result
    
    def _process_file(self, file_info: Dict) -> tuple:
        """
        处理单个文件
        
        Args:
            file_info: 文件信息
            
        Returns:
            (chunks, metadata_list)
        """
        file_path = file_info['path']
        file_name = file_info['name']
        extension = file_info['extension']
        
        # 1. 读取文件
        if extension == '.pdf':
            text = self.pdf_reader.read_as_single_text(file_path)
        elif extension == '.txt':
            text = self.txt_reader.read(file_path)
        elif extension in ['.html', '.htm']:
            text = self.html_reader.read(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {extension}")
        
        if not text or not text.strip():
            raise ValueError("文件内容为空")
        
        # 2. 清洗文本
        cleaned_text = self.text_cleaner.clean(text)
        
        if not cleaned_text or not cleaned_text.strip():
            raise ValueError("清洗后文本为空")
        
        # 3. 分块
        chunks = self.text_chunker.chunk(cleaned_text)
        
        if not chunks:
            raise ValueError("分块结果为空")
        
        # 4. 提取元数据
        file_metadata = self.metadata_extractor.extract(file_path, content=text)
        
        # 5. 为每个chunk创建元数据
        metadata_list = self.metadata_manager.create_batch_metadata(file_metadata, chunks)
        
        logger.info("处理文件: %s -> %d 个块", file_name, len(chunks))
        
        return chunks, metadata_list
    
    def add_file(self, file_path: str) -> Dict:
        """
        添加单个文件到索引（已存在则先删除旧数据）
        
        Args:
            file_path: 文件路径
            
        Returns:
            添加结果
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 先删除该文件的旧chunks
        existing = self.chroma.get(where={"file_name": file_path.name})
        old_ids = existing.get('ids', [])
        if old_ids:
            self.chroma.delete(old_ids)
        
        # 获取文件信息
        file_info = {
            'path': str(file_path),
            'name': file_path.name,
            'extension': file_path.suffix.lower(),
            'size': file_path.stat().st_size,
            'modified_time': file_path.stat().st_mtime,
        }
        
        # 处理文件
        chunks, metadata_list = self._process_file(file_info)
        
        # 生成ID
        ids = []
        for i in range(len(chunks)):
            chunk_id = self.metadata_manager.generate_chunk_id(
                file_path.name, metadata_list[i].get('chunk_index', i)
            )
            ids.append(chunk_id)
        
        # 生成嵌入
        embeddings = self.embedder.embed_batch(chunks)
        
        # 存入数据库
        self.chroma.add_documents(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadata_list,
            documents=chunks
        )
        
        return {
            'file_name': file_path.name,
            'chunks_added': len(chunks),
            'total_documents': self.chroma.count(),
        }
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return self.chroma.get_stats()


if __name__ == "__main__":
    # 测试索引流水线
    from config.settings import RAW_DATA_DIR, CHROMA_DB_PATH
    
    print("测试索引流水线:")
    
    # 创建流水线
    pipeline = IndexingPipeline(
        db_path=None,  # 使用内存模式
        collection_name="test_collection",
        metadata_csv_path=str(Path(__file__).parent.parent.parent / "data" / "raw" / "metadata.csv")
    )
    
    # 执行索引
    result = pipeline.run(str(RAW_DATA_DIR), reset=True)
    
    print(f"\n索引结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # 获取统计信息
    stats = pipeline.get_stats()
    print(f"\n统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
