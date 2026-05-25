"""
元数据提取器 - 从文件和CSV中提取元数据
"""
import csv
import logging
import re
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """从文件和CSV中提取元数据"""
    
    def __init__(self, metadata_csv_path: str = None):
        """
        初始化元数据提取器
        
        Args:
            metadata_csv_path: 元数据CSV文件路径
        """
        self.metadata_csv_path = metadata_csv_path
        self._metadata_cache = {}
        
        # 如果提供了CSV文件，预加载元数据
        if metadata_csv_path and Path(metadata_csv_path).exists():
            self._load_metadata_csv()
    
    def _load_metadata_csv(self):
        """从CSV文件加载元数据"""
        for enc in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
            try:
                with open(self.metadata_csv_path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        file_name = row.get('file_name', '')
                        if file_name:
                            self._metadata_cache[file_name] = row
                break
            except UnicodeDecodeError:
                continue
    
    def extract(self, file_path: str, content: str = None) -> Dict:
        """
        提取文件的元数据
        
        Args:
            file_path: 文件路径
            content: 文件内容（可选，避免重复读取）
            
        Returns:
            元数据字典，包含：
            - file_name: 文件名
            - title: 标题
            - author: 作者
            - date: 日期
            - category: 类别
            - source: 来源（文件属性或CSV）
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 基础元数据（从文件属性获取）
        metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'file_extension': file_path.suffix.lower(),
            'file_size': file_path.stat().st_size,
            'modified_time': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
        
        # 尝试从CSV获取元数据
        csv_metadata = self._get_csv_metadata(file_path.name)
        if csv_metadata:
            metadata.update(csv_metadata)
            metadata['source'] = 'csv'
        else:
            # 尝试从文件内容提取元数据
            content_metadata = self._extract_from_content(file_path, content)
            metadata.update(content_metadata)
            metadata['source'] = 'content'
        
        # 确保所有必要字段存在
        metadata.setdefault('title', file_path.stem)
        metadata.setdefault('author', '未知')
        metadata.setdefault('date', '未知')
        metadata.setdefault('category', '未分类')
        
        return metadata
    
    def _get_csv_metadata(self, file_name: str) -> Optional[Dict]:
        """从CSV缓存中获取元数据"""
        return self._metadata_cache.get(file_name)
    
    def _extract_from_content(self, file_path: Path, content: str = None) -> Dict:
        """从文件内容中提取元数据"""
        metadata = {}
        
        try:
            # 读取文件内容
            if content is None:
                content = self._read_file_content(file_path)
            
            # 提取标题
            title = self._extract_title(content, file_path)
            if title:
                metadata['title'] = title
            
            # 提取作者
            author = self._extract_author(content)
            if author:
                metadata['author'] = author
            
            # 提取日期
            date = self._extract_date(content)
            if date:
                metadata['date'] = date
            
            # 提取类别
            category = self._extract_category(content)
            if category:
                metadata['category'] = category
        
        except Exception as e:
            logger.warning("从文件内容提取元数据失败: %s", e)
        
        return metadata
    
    def _read_file_content(self, file_path: Path) -> str:
        """读取文件内容（复用已有的Reader类）"""
        ext = file_path.suffix.lower()

        if ext == '.txt':
            try:
                from .txt_reader import TXTReader
                return TXTReader().read(str(file_path))
            except Exception:
                return ''
        elif ext in ['.html', '.htm']:
            try:
                from .html_reader import HTMLReader
                return HTMLReader().read(str(file_path))
            except Exception:
                return ''
        elif ext == '.pdf':
            try:
                from .pdf_reader import PDFReader
                return PDFReader().read_as_single_text(str(file_path))
            except Exception:
                return ''
        else:
            return ''
    
    def _extract_title(self, content: str, file_path: Path) -> Optional[str]:
        """从内容中提取标题"""
        # 尝试从第一行提取
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) < 100:  # 标题通常不会太长
                return line
        
        # 使用文件名作为标题
        return file_path.stem
    
    def _extract_author(self, content: str) -> Optional[str]:
        """从内容中提取作者"""
        # 尝试匹配 "作者：xxx" 或 "Author: xxx" 模式
        patterns = [
            r'作者[：:]\s*(.+)',
            r'Author[：:]\s*(.+)',
            r'By[：:]\s*(.+)',
            r'Written by[：:]\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                # 清理作者名（去除多余字符）
                author = re.sub(r'[\n\r].*', '', author)
                return author[:50]  # 限制长度
        
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """从内容中提取日期"""
        # 尝试匹配各种日期格式
        patterns = [
            r'日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
            r'Date[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_category(self, content: str) -> Optional[str]:
        """从内容中提取类别"""
        # 尝试匹配 "类别：xxx" 或 "Category: xxx" 模式
        patterns = [
            r'类别[：:]\s*(.+)',
            r'Category[：:]\s*(.+)',
            r'Type[：:]\s*(.+)',
            r'Tags[：:]\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                category = match.group(1).strip()
                # 清理类别（去除多余字符）
                category = re.sub(r'[\n\r].*', '', category)
                return category[:50]  # 限制长度
        
        return None
    
    def extract_batch(self, file_paths: List[str]) -> List[Dict]:
        """批量提取元数据"""
        return [self.extract(fp) for fp in file_paths]
    
    def get_metadata_for_files(self, directory: str) -> Dict[str, Dict]:
        """获取目录下所有文件的元数据"""
        from .file_scanner import FileScanner
        
        scanner = FileScanner()
        files = scanner.scan(directory)
        
        metadata_dict = {}
        for file_info in files:
            metadata = self.extract(file_info['path'])
            metadata_dict[file_info['name']] = metadata
        
        return metadata_dict


if __name__ == "__main__":
    # 测试元数据提取器
    from pathlib import Path
    
    # 尝试从CSV加载元数据
    csv_path = Path(__file__).parent.parent.parent / "data" / "raw" / "metadata.csv"
    
    if csv_path.exists():
        extractor = MetadataExtractor(str(csv_path))
        print(f"从CSV加载了 {len(extractor._metadata_cache)} 条元数据")
        
        # 测试提取
        test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
        txt_files = list(test_dir.glob("*.txt"))
        
        if txt_files:
            test_file = txt_files[0]
            print(f"\n测试文件: {test_file.name}")
            
            metadata = extractor.extract(str(test_file))
            for key, value in metadata.items():
                print(f"  {key}: {value}")
    else:
        print(f"元数据CSV不存在: {csv_path}")
        
        # 测试从内容提取
        extractor = MetadataExtractor()
        
        test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
        txt_files = list(test_dir.glob("*.txt"))
        
        if txt_files:
            test_file = txt_files[0]
            print(f"\n测试文件: {test_file.name}")
            
            metadata = extractor.extract(str(test_file))
            for key, value in metadata.items():
                print(f"  {key}: {value}")
