"""
LLM客户端 - 与大型语言模型交互
"""
import logging
import time
from typing import Optional, List

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.0


def retry_on_failure(func):
    """重试装饰器，处理临时性API错误"""
    def wrapper(self, *args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.warning("API调用失败 (尝试 %d/%d): %s，%0.1f秒后重试...",
                                   attempt + 1, MAX_RETRIES, e, delay)
                    time.sleep(delay)
        raise RuntimeError(f"API调用失败 (已重试{MAX_RETRIES}次): {last_error}")
    return wrapper


class LLMClient:
    """LLM客户端，支持OpenAI API和回退模式"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        """
        初始化LLM客户端
        
        Args:
            api_key: OpenAI API密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self._client = None
        self._available = False
        
        # 初始化客户端
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        if not self.api_key:
            logger.info("未提供OpenAI API密钥，将使用回退模式")
            return
        
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key)
            self._available = True
            logger.info("已初始化OpenAI客户端 (模型: %s)", self.model)
        except Exception as e:
            logger.warning("初始化OpenAI客户端失败: %s", e)
            self._available = False
    
    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return self._available
    
    @retry_on_failure
    def generate(self, prompt: str, max_tokens: int = 1000, 
                temperature: float = 0.7) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            max_tokens: 最大生成token数
            temperature: 温度参数（0-1）
            
        Returns:
            生成的文本
        """
        if not self._available:
            raise RuntimeError("LLM不可用，请提供有效的API密钥")
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个有帮助的助手，根据提供的上下文回答问题。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
    
    def generate_with_context(self, question: str, context: str, 
                             max_tokens: int = 1000) -> str:
        """
        基于上下文生成答案
        
        Args:
            question: 用户问题
            context: 上下文信息
            max_tokens: 最大生成token数
            
        Returns:
            生成的答案
        """
        prompt = f"""根据以下上下文信息回答用户的问题。
如果上下文中没有相关信息，请如实说明"根据现有文档，我无法找到相关信息"。
请在回答中标注信息来源。

上下文信息：
{context}

用户问题：{question}

请提供准确、有据可查的回答："""
        
        return self.generate(prompt, max_tokens=max_tokens)


if __name__ == "__main__":
    # 测试LLM客户端
    import os
    
    # 从环境变量获取API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        client = LLMClient(api_key=api_key)
        
        if client.is_available():
            print("测试LLM生成:")
            response = client.generate("什么是Python？请简要说明。")
            print(f"响应: {response}")
    else:
        print("未设置OPENAI_API_KEY环境变量，跳过LLM测试")
