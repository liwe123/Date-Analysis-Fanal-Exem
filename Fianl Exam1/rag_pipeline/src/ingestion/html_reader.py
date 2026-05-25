"""
HTML文本提取器 - 从HTML文件中提取纯文本内容
"""
from typing import Optional
from pathlib import Path


class HTMLReader:
    """从HTML文件中提取纯文本"""
    
    def __init__(self):
        """初始化HTML读取器"""
        self._BeautifulSoup = None
    
    def _get_bs4(self):
        """延迟导入BeautifulSoup"""
        if self._BeautifulSoup is None:
            try:
                from bs4 import BeautifulSoup
                self._BeautifulSoup = BeautifulSoup
            except ImportError:
                raise ImportError("beautifulsoup4未安装，请运行: pip install beautifulsoup4")
        return self._BeautifulSoup
    
    def read(self, file_path: str) -> str:
        """
        读取HTML文件，返回纯文本内容
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            纯文本内容
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取HTML内容
        html_content = self._read_html_file(file_path)
        
        # 提取纯文本
        text = self._extract_text(html_content)
        
        return text
    
    def _read_html_file(self, file_path: Path) -> str:
        """读取HTML文件内容"""
        # 尝试不同编码
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # 回退方案
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_text(self, html_content: str) -> str:
        """从HTML中提取纯文本"""
        BeautifulSoup = self._get_bs4()
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 
                         'aside', 'iframe', 'noscript']):
            tag.decompose()
        
        # 获取纯文本
        text = soup.get_text(separator='\n', strip=True)
        
        # 清理多余空行
        lines = text.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                    prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        return '\n'.join(cleaned_lines).strip()
    
    def read_with_title(self, file_path: str) -> tuple:
        """
        读取HTML文件，返回标题和文本内容
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            (标题, 文本内容)
        """
        file_path = Path(file_path)
        
        # 读取HTML内容
        html_content = self._read_html_file(file_path)
        
        # 提取标题
        title = self._extract_title(html_content)
        
        # 提取文本
        text = self._extract_text(html_content)
        
        return title, text
    
    def _extract_title(self, html_content: str) -> Optional[str]:
        """从HTML中提取标题"""
        BeautifulSoup = self._get_bs4()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试从<title>标签获取
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # 尝试从<h1>标签获取
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return None
    
    def extract_metadata(self, file_path: str) -> dict:
        """
        从HTML中提取元数据
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            元数据字典
        """
        file_path = Path(file_path)
        
        # 读取HTML内容
        html_content = self._read_html_file(file_path)
        
        BeautifulSoup = self._get_bs4()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        metadata = {}
        
        # 提取标题
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # 提取meta标签
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            
            if name and content:
                metadata[name] = content
        
        return metadata


if __name__ == "__main__":
    # 测试HTML读取器
    reader = HTMLReader()
    
    # 查找测试HTML文件
    test_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "documents"
    html_files = list(test_dir.glob("*.html"))
    
    if html_files:
        test_file = html_files[0]
        print(f"测试文件: {test_file.name}")
        
        # 读取HTML
        title, text = reader.read_with_title(str(test_file))
        print(f"标题: {title}")
        print(f"内容长度: {len(text)} 字符")
        print(f"\n前500字符:")
        print(text[:500] + "..." if len(text) > 500 else text)
    else:
        print("未找到HTML测试文件")
