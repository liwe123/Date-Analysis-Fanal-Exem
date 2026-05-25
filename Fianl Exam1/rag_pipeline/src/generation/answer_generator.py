"""
答案生成器 - 基于检索结果生成答案
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# 提示词模板
RAG_PROMPT_TEMPLATE = """你是一个智能助手。根据以下检索到的上下文信息回答用户的问题。
如果上下文中没有相关信息，请如实说明"根据现有文档，我无法找到相关信息"。
请在回答中标注信息来源。

上下文信息：
{context}

用户问题：{question}

请提供准确、有据可查的回答："""

CONTEXT_FORMAT = """
[来源: {source_file} | 标题: {title} | 作者: {author} | 日期: {date}]
{text}
---
"""


class AnswerGenerator:
    """答案生成器，基于检索结果生成答案"""
    
    def __init__(self, llm_client=None):
        """
        初始化答案生成器
        
        Args:
            llm_client: LLM客户端（可选）
        """
        self.llm = llm_client
    
    def generate(self, question: str, retrieved_chunks: List[Dict]) -> Dict:
        """
        生成答案
        
        Args:
            question: 用户问题
            retrieved_chunks: 检索到的chunk列表
            
        Returns:
            生成结果：
            - answer: 答案文本
            - sources: 来源信息
            - has_llm: 是否使用了LLM
        """
        if not retrieved_chunks:
            return {
                'answer': '未找到相关文档。',
                'sources': [],
                'has_llm': False,
            }
        
        # 格式化上下文
        context = self._format_context(retrieved_chunks)
        
        # 提取来源信息
        sources = self._extract_sources(retrieved_chunks)
        
        # 生成答案
        if self.llm and self.llm.is_available():
            answer = self._generate_with_llm(question, context, retrieved_chunks)
            has_llm = True
        else:
            answer = self._fallback_answer(question, retrieved_chunks)
            has_llm = False
        
        return {
            'answer': answer,
            'sources': sources,
            'has_llm': has_llm,
        }
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """格式化上下文"""
        context_parts = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            
            context_part = CONTEXT_FORMAT.format(
                source_file=metadata.get('file_name', '未知'),
                title=metadata.get('title', '未知'),
                author=metadata.get('author', '未知'),
                date=metadata.get('date', '未知'),
                text=chunk.get('text', ''),
            )
            
            context_parts.append(context_part)
        
        return '\n'.join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """提取来源信息"""
        sources = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            
            sources.append({
                'chunk_id': chunk.get('chunk_id', ''),
                'file': metadata.get('file_name', '未知'),
                'title': metadata.get('title', '未知'),
                'author': metadata.get('author', '未知'),
                'date': metadata.get('date', '未知'),
                'category': metadata.get('category', '未知'),
                'score': chunk.get('score', 0),
                'text_preview': chunk.get('text', '')[:200] + '...' if len(chunk.get('text', '')) > 200 else chunk.get('text', ''),
            })
        
        return sources
    
    def _generate_with_llm(self, question: str, context: str, chunks: List[Dict]) -> str:
        """使用LLM生成答案"""
        try:
            prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error("LLM生成失败: %s", e)
            return self._fallback_answer(question, chunks)
    
    def _fallback_answer(self, question: str, chunks: List[Dict]) -> str:
        """
        回退答案生成（不使用LLM）
        直接展示检索到的相关内容
        """
        if not chunks:
            return "未找到相关文档。"
        
        answer_parts = [
            f"根据您的问题「{question}」，以下是相关文档内容：\n",
        ]
        
        for i, chunk in enumerate(chunks[:3], 1):  # 最多展示3个
            metadata = chunk.get('metadata', {})
            score = chunk.get('score', 0)
            
            answer_parts.append(f"--- 相关文档 {i} (相似度: {score:.2f}) ---")
            answer_parts.append(f"来源: {metadata.get('title', '未知')} - {metadata.get('author', '未知')}")
            answer_parts.append(f"内容: {chunk.get('text', '')[:500]}")
            answer_parts.append("")
        
        answer_parts.append("注：以上为检索到的相关文档内容，未经LLM生成。")
        
        return '\n'.join(answer_parts)
    
    def generate_summary(self, chunks: List[Dict]) -> str:
        """生成检索结果摘要"""
        if not chunks:
            return "无检索结果。"
        
        summary_parts = [f"共找到 {len(chunks)} 个相关文档：\n"]
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            score = chunk.get('score', 0)
            
            summary_parts.append(
                f"{i}. {metadata.get('title', '未知')} "
                f"(作者: {metadata.get('author', '未知')}, "
                f"相似度: {score:.2f})"
            )
        
        return '\n'.join(summary_parts)


if __name__ == "__main__":
    # 测试答案生成器
    generator = AnswerGenerator()
    
    # 模拟检索结果
    test_chunks = [
        {
            'chunk_id': 'doc_001_chunk_0001',
            'text': 'Python是一种高级编程语言，由Guido van Rossum于1991年创建。',
            'metadata': {
                'file_name': 'doc_001_python_basics.txt',
                'title': 'Python编程语言入门指南',
                'author': '张三',
                'date': '2024-01-15',
            },
            'score': 0.95,
        },
        {
            'chunk_id': 'doc_002_chunk_0001',
            'text': 'Python支持多种数据类型，包括整数、浮点数、字符串等。',
            'metadata': {
                'file_name': 'doc_002_python_data_types.txt',
                'title': 'Python数据类型详解',
                'author': '李四',
                'date': '2024-02-20',
            },
            'score': 0.85,
        },
    ]
    
    print("测试答案生成器（回退模式）:")
    result = generator.generate("什么是Python？", test_chunks)
    
    print(f"\n答案:\n{result['answer']}")
    print(f"\n来源数量: {len(result['sources'])}")
    print(f"使用LLM: {result['has_llm']}")
