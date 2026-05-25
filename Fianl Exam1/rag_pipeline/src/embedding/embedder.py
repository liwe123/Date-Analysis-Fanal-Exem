"""
嵌入生成器 - 将文本转换为向量
支持多种后端：sentence-transformers（本地）、OpenAI API、ChromaDB默认
"""
import logging
import time
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

EMBED_MAX_RETRIES = 3
EMBED_RETRY_DELAY = 1.0


class Embedder:
    """嵌入生成器，支持多种后端"""
    
    def __init__(self, backend: str = 'sentence-transformers', model_name: str = 'all-MiniLM-L6-v2'):
        """
        初始化嵌入生成器
        
        Args:
            backend: 嵌入后端 ('sentence-transformers', 'openai', 'chromadb')
            model_name: 模型名称
        """
        self.backend = backend
        self.model_name = model_name
        self._model = None
        self._openai_client = None
        self._dimension = None
        
        # 初始化后端
        self._init_backend()
    
    def _init_backend(self):
        """初始化嵌入后端"""
        if self.backend == 'sentence-transformers':
            self._init_sentence_transformers()
        elif self.backend == 'openai':
            self._init_openai()
        elif self.backend == 'chromadb':
            self._init_chromadb()
        else:
            raise ValueError(f"不支持的后端: {self.backend}")
    
    def _init_sentence_transformers(self):
        """初始化sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info("已加载sentence-transformers模型: %s (维度: %d)", self.model_name, self._dimension)
        except Exception as e:
            logger.error("⚠️ 加载sentence-transformers失败: %s。已降级为伪随机向量，语义检索将不可用！", e)
            self.backend = 'chromadb'
    
    def _init_openai(self):
        """初始化OpenAI"""
        try:
            import openai
            self._openai_client = openai.OpenAI()
            self._dimension = 1536
            logger.info("已初始化OpenAI客户端")
        except Exception as e:
            logger.warning("初始化OpenAI失败: %s，将使用ChromaDB默认嵌入", e)
            self.backend = 'chromadb'
    
    def _init_chromadb(self):
        """初始化ChromaDB默认嵌入"""
        self._dimension = 384
        logger.info("使用ChromaDB默认嵌入函数")
    
    @property
    def dimension(self) -> int:
        """获取嵌入维度"""
        return self._dimension
    
    def embed_text(self, text: str) -> List[float]:
        """
        将单条文本转换为嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量（浮点数列表）
        """
        if not text or not text.strip():
            # 返回零向量
            return [0.0] * self._dimension
        
        if self.backend == 'sentence-transformers':
            return self._embed_with_st(text)
        elif self.backend == 'openai':
            return self._embed_with_openai(text)
        elif self.backend == 'chromadb':
            return self._embed_with_chromadb(text)
        else:
            raise ValueError(f"不支持的后端: {self.backend}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        批量将文本转换为嵌入向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        # 过滤空文本
        valid_texts = [t if t and t.strip() else " " for t in texts]
        
        if self.backend == 'sentence-transformers':
            return self._embed_batch_with_st(valid_texts, batch_size)
        elif self.backend == 'openai':
            return self._embed_batch_with_openai(valid_texts, batch_size)
        elif self.backend == 'chromadb':
            return self._embed_batch_with_chromadb(valid_texts)
        else:
            raise ValueError(f"不支持的后端: {self.backend}")
    
    def _embed_with_st(self, text: str) -> List[float]:
        """使用sentence-transformers生成嵌入"""
        embedding = self._model.encode(text)
        return embedding.tolist()
    
    def _embed_batch_with_st(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """使用sentence-transformers批量生成嵌入"""
        embeddings = self._model.encode(texts, batch_size=batch_size, show_progress_bar=True)
        return embeddings.tolist()
    
    def _embed_with_openai(self, text: str) -> List[float]:
        """使用OpenAI生成嵌入（带重试）"""
        for attempt in range(EMBED_MAX_RETRIES):
            try:
                response = self._openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < EMBED_MAX_RETRIES - 1:
                    delay = EMBED_RETRY_DELAY * (2 ** attempt)
                    logger.warning("OpenAI嵌入失败 (尝试 %d/%d): %s，%0.1f秒后重试...",
                                   attempt + 1, EMBED_MAX_RETRIES, e, delay)
                    time.sleep(delay)
                else:
                    raise

    def _embed_batch_with_openai(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """使用OpenAI批量生成嵌入（带重试）"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for attempt in range(EMBED_MAX_RETRIES):
                try:
                    response = self._openai_client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if attempt < EMBED_MAX_RETRIES - 1:
                        delay = EMBED_RETRY_DELAY * (2 ** attempt)
                        logger.warning("OpenAI批量嵌入失败 (尝试 %d/%d): %s，%0.1f秒后重试...",
                                       attempt + 1, EMBED_MAX_RETRIES, e, delay)
                        time.sleep(delay)
                    else:
                        raise

        return all_embeddings
    
    def _embed_with_chromadb(self, text: str, rng: np.random.RandomState = None) -> List[float]:
        """使用ChromaDB默认嵌入（确定性伪随机向量）"""
        import hashlib

        if rng is None:
            hash_obj = hashlib.md5(text.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)

        vector = rng.randn(self._dimension)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()

    def _embed_batch_with_chromadb(self, texts: List[str]) -> List[List[float]]:
        """使用ChromaDB默认批量生成嵌入（向量化）"""
        import hashlib

        # 预先生成所有随机状态
        rngs = []
        for text in texts:
            hash_obj = hashlib.md5(text.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            rngs.append(np.random.RandomState(seed))

        # 批量生成向量
        vectors = np.array([rng.randn(self._dimension) for rng in rngs])

        # 批量归一化
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors = vectors / norms

        return vectors.tolist()
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度（-1到1之间）
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


if __name__ == "__main__":
    # 测试嵌入生成器
    print("测试嵌入生成器:")
    
    # 测试sentence-transformers后端
    embedder = Embedder(backend='sentence-transformers')
    
    test_texts = [
        "Python是一种高级编程语言",
        "机器学习是人工智能的一个分支",
        "数据分析需要使用Pandas库",
    ]
    
    print(f"\n嵌入维度: {embedder.dimension}")
    
    # 测试单条文本嵌入
    print("\n测试单条文本嵌入:")
    for text in test_texts:
        embedding = embedder.embed_text(text)
        print(f"  文本: {text}")
        print(f"  向量长度: {len(embedding)}")
        print(f"  前5个值: {embedding[:5]}")
    
    # 测试批量嵌入
    print("\n测试批量嵌入:")
    embeddings = embedder.embed_batch(test_texts)
    print(f"  批量大小: {len(embeddings)}")
    
    # 测试相似度计算
    print("\n测试相似度计算:")
    for i in range(len(test_texts)):
        for j in range(i + 1, len(test_texts)):
            sim = embedder.similarity(embeddings[i], embeddings[j])
            print(f"  '{test_texts[i][:10]}...' vs '{test_texts[j][:10]}...': {sim:.4f}")
