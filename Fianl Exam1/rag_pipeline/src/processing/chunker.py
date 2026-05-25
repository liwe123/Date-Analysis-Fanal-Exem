"""
文本分块器 - 将文本分割成语义上有意义的块
"""
import re
from typing import List, Optional, Callable


class TextChunker:
    """文本分块器，支持多种分块策略"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文本分块器
        
        Args:
            chunk_size: 每个块的目标大小（字符数）
            chunk_overlap: 块之间的重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk(self, text: str, strategy: str = 'recursive') -> List[str]:
        """
        将文本分割成块
        
        Args:
            text: 要分割的文本
            strategy: 分块策略 ('recursive', 'fixed', 'sentence', 'paragraph')
            
        Returns:
            文本块列表
        """
        if not text or not text.strip():
            return []
        
        # 清理文本
        text = text.strip()
        
        # 如果文本小于chunk_size，直接返回
        if len(text) <= self.chunk_size:
            return [text]
        
        # 根据策略选择分块方法
        if strategy == 'recursive':
            return self._chunk_recursive(text)
        elif strategy == 'fixed':
            return self._chunk_fixed(text)
        elif strategy == 'sentence':
            return self._chunk_by_sentence(text)
        elif strategy == 'paragraph':
            return self._chunk_by_paragraph(text)
        else:
            raise ValueError(f"不支持的分块策略: {strategy}")
    
    def _chunk_recursive(self, text: str) -> List[str]:
        """
        递归字符分块（推荐）
        按分隔符优先级递归分割：段落 → 句子 → 词
        """
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            raise ImportError(
                "递归分块需要 langchain-text-splitters，请运行: pip install langchain-text-splitters"
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "？", "！", ".", "?", "!", "；", ";", "：", ":", " ", ""],
            length_function=len,
            keep_separator=True,
        )
        
        chunks = splitter.split_text(text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def _chunk_fixed(self, text: str) -> List[str]:
        """
        固定大小分块
        按固定字符数分割，可能会切断句子
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在空格处断开
            if end < len(text):
                # 在chunk_size范围内找最后一个空格
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 下一块的起始位置（考虑重叠）
            start = end - self.chunk_overlap
        
        return chunks
    
    def _chunk_by_sentence(self, text: str) -> List[str]:
        """
        按句子分块
        保持句子完整性
        """
        # 中英文句子分隔符
        sentence_endings = re.compile(r'([。！？.!?])')
        
        # 分割句子
        sentences = sentence_endings.split(text)
        
        # 合并句子和标点
        merged_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            merged_sentences.append(sentences[i] + sentences[i + 1])
        
        # 如果最后一个元素没有标点，也加入
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            merged_sentences.append(sentences[-1])
        
        # 合并小句子
        chunks = []
        current_chunk = ""
        
        for sentence in merged_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 如果当前块加上新句子不超过chunk_size
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个句子太长，使用递归分块
                if len(sentence) > self.chunk_size:
                    sub_chunks = self._chunk_recursive(sentence)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_paragraph(self, text: str) -> List[str]:
        """
        按段落分块
        保持段落完整性
        """
        # 按双换行符分割段落
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 如果当前块加上新段落不超过chunk_size
            if len(current_chunk) + len(paragraph) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                
                # 如果单个段落太长，使用递归分块
                if len(paragraph) > self.chunk_size:
                    sub_chunks = self._chunk_recursive(paragraph)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_with_metadata(self, text: str, metadata: dict, 
                           strategy: str = 'recursive') -> List[dict]:
        """
        分块并为每个块添加元数据
        
        Args:
            text: 要分割的文本
            metadata: 基础元数据
            strategy: 分块策略
            
        Returns:
            包含文本和元数据的字典列表
        """
        chunks = self.chunk(text, strategy)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_size': len(chunk),
            })
            
            result.append({
                'text': chunk,
                'metadata': chunk_metadata
            })
        
        return result


if __name__ == "__main__":
    # 测试文本分块器
    chunker = TextChunker(chunk_size=200, chunk_overlap=50)
    
    test_text = """
Python是一种高级编程语言，由Guido van Rossum于1991年创建。
Python的设计哲学强调代码的可读性和简洁性。

Python的主要特点包括：
1. 简洁易读的语法
2. 动态类型系统
3. 自动内存管理
4. 丰富的标准库
5. 跨平台兼容性

Python支持多种编程范式，包括面向对象编程、函数式编程和过程式编程。
安装Python：可以从Python官方网站下载最新版本的Python。
"""
    
    print("测试递归分块策略:")
    chunks = chunker.chunk(test_text, strategy='recursive')
    for i, chunk in enumerate(chunks):
        print(f"\n--- 块 {i + 1} (长度: {len(chunk)}) ---")
        print(chunk)
    
    print("\n\n测试按句子分块策略:")
    chunks = chunker.chunk(test_text, strategy='sentence')
    for i, chunk in enumerate(chunks):
        print(f"\n--- 块 {i + 1} (长度: {len(chunk)}) ---")
        print(chunk)
