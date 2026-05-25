"""
文件扫描器 - 扫描指定文件夹，发现所有可处理的文档文件
"""
import os
from pathlib import Path
from typing import List, Dict, Set
from config.settings import SUPPORTED_EXTENSIONS


class FileScanner:
    """扫描文件夹，发现所有支持的文档文件"""
    
    def __init__(self, supported_extensions: Set[str] = None):
        """
        初始化文件扫描器
        
        Args:
            supported_extensions: 支持的文件扩展名集合
        """
        self.supported_extensions = supported_extensions or SUPPORTED_EXTENSIONS
    
    def scan(self, directory: str) -> List[Dict]:
        """
        扫描指定目录，返回所有支持的文件信息
        
        Args:
            directory: 要扫描的目录路径
            
        Returns:
            文件信息列表，每个元素包含：
            - path: 文件完整路径
            - name: 文件名
            - extension: 文件扩展名
            - size: 文件大小（字节）
            - modified_time: 最后修改时间
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"不是目录: {directory}")
        
        files = []
        
        # 递归遍历目录
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                file_path = Path(root) / filename
                
                # 检查文件扩展名
                if file_path.suffix.lower() in self.supported_extensions:
                    file_info = self._get_file_info(file_path)
                    files.append(file_info)
        
        # 按文件名排序
        files.sort(key=lambda x: x['name'])
        
        return files
    
    def _get_file_info(self, file_path: Path) -> Dict:
        """获取文件信息"""
        stat = file_path.stat()
        
        return {
            'path': str(file_path),
            'name': file_path.name,
            'extension': file_path.suffix.lower(),
            'size': stat.st_size,
            'modified_time': stat.st_mtime
        }
    
    def get_file_count_by_type(self, directory: str) -> Dict[str, int]:
        """统计各类型文件数量"""
        files = self.scan(directory)
        
        count_by_type = {}
        for file in files:
            ext = file['extension']
            count_by_type[ext] = count_by_type.get(ext, 0) + 1
        
        return count_by_type
    
    def filter_files(self, files: List[Dict], 
                     min_size: int = None, 
                     max_size: int = None,
                     extensions: Set[str] = None) -> List[Dict]:
        """过滤文件列表"""
        filtered = files.copy()
        
        if min_size is not None:
            filtered = [f for f in filtered if f['size'] >= min_size]
        
        if max_size is not None:
            filtered = [f for f in filtered if f['size'] <= max_size]
        
        if extensions is not None:
            filtered = [f for f in filtered if f['extension'] in extensions]
        
        return filtered


if __name__ == "__main__":
    # 测试文件扫描器
    scanner = FileScanner()
    
    # 扫描示例目录
    test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
    
    if test_dir.exists():
        files = scanner.scan(str(test_dir))
        
        print(f"扫描目录: {test_dir}")
        print(f"找到 {len(files)} 个文件\n")
        
        for file in files:
            print(f"  {file['name']} ({file['extension']}) - {file['size']} bytes")
        
        print("\n各类型文件统计:")
        count_by_type = scanner.get_file_count_by_type(str(test_dir))
        for ext, count in count_by_type.items():
            print(f"  {ext}: {count} 个文件")
    else:
        print(f"测试目录不存在: {test_dir}")
