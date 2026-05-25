"""
文本清洗器 - 清洗和标准化文本内容
"""
import re
from typing import Optional


class TextCleaner:
    """文本清洗器，用于清洗和标准化文本内容"""
    
    def __init__(self):
        """初始化文本清洗器"""
        # 编译正则表达式以提高性能
        self._html_pattern = re.compile(r'<[^>]+>')
        self._url_pattern = re.compile(r'http[s]?://\S+')
        self._email_pattern = re.compile(r'\S+@\S+\.\S+')
        self._whitespace_pattern = re.compile(r'\s+')
        self._multiple_newlines_pattern = re.compile(r'\n\s*\n')
        self._special_chars_pattern = re.compile(r'[^\w\s\u4e00-\u9fff.,!?;:()\[\]{}\-\'"]+')
        self._boilerplate_patterns = [
            re.compile(r'版权所有.*?\n', re.IGNORECASE),
            re.compile(r'Copyright.*?\n', re.IGNORECASE),
            re.compile(r'All rights reserved.*?\n', re.IGNORECASE),
            re.compile(r'保留所有权利.*?\n', re.IGNORECASE),
        ]
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ''
        
        # 1. 移除HTML标签
        text = self.remove_html_tags(text)
        
        # 2. 移除URL
        text = self.remove_urls(text)
        
        # 3. 移除邮箱
        text = self.remove_emails(text)
        
        # 4. 移除样板文本
        text = self.remove_boilerplate(text)
        
        # 5. 移除特殊字符
        text = self.remove_special_characters(text)
        
        # 6. 移除多余空行（先处理换行，保留段落结构）
        text = self.remove_multiple_newlines(text)
        
        # 7. 标准化每行内的多余空格（不影响换行符）
        text = self._normalize_inline_spaces(text)
        
        return text.strip()
    
    def remove_html_tags(self, text: str) -> str:
        """移除HTML标签"""
        return self._html_pattern.sub('', text)
    
    def remove_urls(self, text: str) -> str:
        """移除URL"""
        return self._url_pattern.sub('', text)
    
    def remove_emails(self, text: str) -> str:
        """移除邮箱地址"""
        return self._email_pattern.sub('', text)
    
    def remove_special_characters(self, text: str) -> str:
        """
        移除特殊字符
        保留：中文、英文、数字、常用标点
        """
        return self._special_chars_pattern.sub('', text)
    
    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符（多个空格合并为一个，注意会吞掉换行）"""
        return self._whitespace_pattern.sub(' ', text)
    
    def _normalize_inline_spaces(self, text: str) -> str:
        """只压缩每行内的多余空格和制表符，保留换行符"""
        lines = text.split('\n')
        return '\n'.join(re.sub(r'[ \t]+', ' ', line) for line in lines)
    
    def remove_multiple_newlines(self, text: str) -> str:
        """移除多余空行（保留最多一个空行）"""
        return self._multiple_newlines_pattern.sub('\n\n', text)
    
    def remove_boilerplate(self, text: str) -> str:
        """移除样板文本（如版权声明）"""
        for pattern in self._boilerplate_patterns:
            text = pattern.sub('', text)
        return text
    
    def fix_encoding(self, text: str) -> str:
        """
        修复常见编码问题
        """
        # 常见编码错误映射
        encoding_fixes = [
            ('â€™', "'"),
            ('â€œ', '"'),
            ('â€\x9d', '"'),
            ('Ã©', 'é'),
            ('Ã¨', 'è'),
            ('Ã¼', 'ü'),
            ('Ã¶', 'ö'),
            ('Ã¤', 'ä'),
            ('â€˜', "'"),
            ('â€"', '–'),
            ('â€"', '—'),
        ]
        
        for wrong, correct in encoding_fixes:
            text = text.replace(wrong, correct)
        
        return text
    
    def clean_for_embedding(self, text: str) -> str:
        """
        专门为嵌入向量准备清洗文本
        （更激进的清洗，移除所有非必要字符）
        """
        # 基础清洗
        text = self.clean(text)
        
        # 移除所有标点符号（保留中文和英文）
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        
        # 标准化空格
        text = self.normalize_whitespace(text)
        
        return text.strip()


if __name__ == "__main__":
    # 测试文本清洗器
    cleaner = TextCleaner()
    
    test_texts = [
        '<p>Hello, <b>World</b>!</p>',
        'Visit us at https://example.com or email us@test.com',
        'Multiple   spaces   and\n\n\nnewlines',
        'Copyright 2024 All rights reserved\nReal content here',
        'Special chars: @#$%^&*() keep this: 你好世界',
    ]
    
    for text in test_texts:
        cleaned = cleaner.clean(text)
        print(f"原文: {text}")
        print(f"清洗后: {cleaned}")
        print()
