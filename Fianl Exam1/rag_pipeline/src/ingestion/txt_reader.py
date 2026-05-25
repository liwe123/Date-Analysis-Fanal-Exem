"""
TXT文本提取器 - 从TXT文件中提取文本内容
"""
from typing import Optional
from pathlib import Path


class TXTReader:
    """从TXT文件中提取文本"""
    
    # 常见编码列表，按优先级排序
    ENCODINGS = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'latin-1', 'ascii']
    
    def read(self, file_path: str) -> str:
        """
        读取TXT文件，返回文本内容
        
        Args:
            file_path: TXT文件路径
            
        Returns:
            文本内容
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 尝试不同编码读取文件
        for encoding in self.ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return content.strip()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise RuntimeError(f"读取文件失败: {e}")
        
        # 如果所有编码都失败，尝试使用errors='ignore'
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return content.strip()
        except Exception as e:
            raise RuntimeError(f"无法读取文件 {file_path}: {e}")
    
    def read_lines(self, file_path: str) -> list:
        """
        读取TXT文件，返回行列表
        
        Args:
            file_path: TXT文件路径
            
        Returns:
            行列表
        """
        content = self.read(file_path)
        return content.split('\n')
    
    def read_with_encoding(self, file_path: str) -> tuple:
        """
        读取TXT文件，返回文本内容和使用的编码
        
        Args:
            file_path: TXT文件路径
            
        Returns:
            (文本内容, 使用的编码)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        for encoding in self.ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return content.strip(), encoding
            except UnicodeDecodeError:
                continue
        
        # 回退方案
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content.strip(), 'utf-8 (with errors ignored)'
    
    def get_encoding(self, file_path: str) -> Optional[str]:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的编码，如果检测失败返回None
        """
        file_path = Path(file_path)
        
        for encoding in self.ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                return encoding
            except UnicodeDecodeError:
                continue
        
        return None


if __name__ == "__main__":
    # 测试TXT读取器
    reader = TXTReader()
    
    # 查找测试TXT文件
    test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
    txt_files = list(test_dir.glob("*.txt"))
    
    if txt_files:
        test_file = txt_files[0]
        print(f"测试文件: {test_file.name}")
        
        # 检测编码
        encoding = reader.get_encoding(str(test_file))
        print(f"检测到编码: {encoding}")
        
        # 读取文件
        content, used_encoding = reader.read_with_encoding(str(test_file))
        print(f"使用编码: {used_encoding}")
        print(f"内容长度: {len(content)} 字符")
        print(f"\n前500字符:")
        print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print("未找到TXT测试文件")
