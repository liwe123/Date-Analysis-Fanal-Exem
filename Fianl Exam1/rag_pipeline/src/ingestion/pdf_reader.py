"""
PDF文本提取器 - 从PDF文件中提取文本内容
"""
from typing import List, Dict, Optional
from pathlib import Path


class PDFReader:
    """从PDF文件中提取文本"""
    
    def __init__(self):
        """初始化PDF读取器"""
        self._fitz = None
        self._pypdf2 = None
        self._pypdf = None
    
    def _get_fitz(self):
        """延迟导入PyMuPDF"""
        if self._fitz is None:
            try:
                import fitz
                self._fitz = fitz
            except ImportError:
                raise ImportError("PyMuPDF未安装，请运行: pip install PyMuPDF")
        return self._fitz
    
    def _get_pypdf2(self):
        """延迟导入PyPDF2"""
        if self._pypdf2 is None:
            try:
                import PyPDF2
                self._pypdf2 = PyPDF2
            except ImportError:
                raise ImportError("PyPDF2未安装，请运行: pip install PyPDF2")
        return self._pypdf2
    
    def read(self, file_path: str) -> List[Dict]:
        """
        读取PDF文件，返回每页的文本内容
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            页面文本列表，每个元素包含：
            - page: 页码（从1开始）
            - text: 该页的文本内容
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if file_path.suffix.lower() != '.pdf':
            raise ValueError(f"不是PDF文件: {file_path}")
        
        # 优先使用PyMuPDF（速度快、质量高）
        try:
            return self._read_with_fitz(file_path)
        except Exception as e:
            print(f"PyMuPDF读取失败: {e}，尝试使用PyPDF2...")
            return self._read_with_pypdf2(file_path)
    
    def _read_with_fitz(self, file_path: Path) -> List[Dict]:
        """使用PyMuPDF读取PDF"""
        fitz = self._get_fitz()
        pages = []
        
        doc = fitz.open(str(file_path))
        
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append({
                    'page': i + 1,
                    'text': text.strip()
                })
        
        doc.close()
        return pages
    
    def _read_with_pypdf2(self, file_path: Path) -> List[Dict]:
        """使用PyPDF2读取PDF"""
        PyPDF2 = self._get_pypdf2()
        pages = []
        
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages.append({
                        'page': i + 1,
                        'text': text.strip()
                    })
        
        return pages
    
    def read_as_single_text(self, file_path: str) -> str:
        """
        读取PDF文件，返回合并后的文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            合并后的文本内容
        """
        pages = self.read(file_path)
        return '\n\n'.join([page['text'] for page in pages])
    
    def get_page_count(self, file_path: str) -> int:
        """获取PDF页数"""
        pages = self.read(file_path)
        return len(pages)
    
    def read_page(self, file_path: str, page_number: int) -> Optional[str]:
        """
        读取指定页的文本
        
        Args:
            file_path: PDF文件路径
            page_number: 页码（从1开始）
            
        Returns:
            该页的文本内容，如果页码无效返回None
        """
        pages = self.read(file_path)
        
        for page in pages:
            if page['page'] == page_number:
                return page['text']
        
        return None


if __name__ == "__main__":
    # 测试PDF读取器
    reader = PDFReader()
    
    # 查找测试PDF文件
    from pathlib import Path
    
    test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
    pdf_files = list(test_dir.glob("*.pdf"))
    
    if pdf_files:
        test_file = pdf_files[0]
        print(f"测试文件: {test_file.name}")
        
        # 读取PDF
        pages = reader.read(str(test_file))
        
        print(f"页数: {len(pages)}")
        for page in pages:
            print(f"\n--- 第 {page['page']} 页 ---")
            print(page['text'][:200] + "..." if len(page['text']) > 200 else page['text'])
    else:
        print("未找到PDF测试文件")
