"""
embed_store.py
==============
向量存储与检索模块（ChromaDB + OpenAI-compatible 或本地 HuggingFace 嵌入）。

功能：
  - 支持本地与远程模型嵌入
  - 支持语义向量搜索、元数据过滤及关键词过滤（混合检索）
  - 支持数据去重写入（upsert）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from openai import OpenAI

from src.utils import (
    clean_env,
    get_embedding_model_name,
    get_logger,
    get_openai_client,
)

logger = get_logger("embed_store")

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "vector_store"

# ── 本地嵌入模型 ──────────────────────────────────────────────────

_LOCAL_EMBEDDING_MODEL: Any = None
_LOCAL_MODEL_NAME: str | None = None  # 从环境变量动态读取


def _resolve_local_model_name() -> str:
    """获取本地嵌入模型名（优先 LOCAL_EMBEDDING_MODEL 环境变量，否则默认 Qwen/Qwen3-Embedding-0.6B）。"""
    model = clean_env("LOCAL_EMBEDDING_MODEL")
    if model and model.strip():
        return model.strip()
    return "Qwen/Qwen3-Embedding-0.6B"


def _get_local_embedding_model() -> Any:
    """懒加载本地 sentence-transformers 模型（全局单例，GPU 优先）。"""
    global _LOCAL_EMBEDDING_MODEL, _LOCAL_MODEL_NAME
    if _LOCAL_EMBEDDING_MODEL is None:
        _LOCAL_MODEL_NAME = _resolve_local_model_name()
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("正在加载本地嵌入模型 \"%s\"（设备: %s）…", _LOCAL_MODEL_NAME, device)
            _LOCAL_EMBEDDING_MODEL = SentenceTransformer(_LOCAL_MODEL_NAME, device=device)
            logger.info("本地嵌入模型加载完成（%d 维）。", _LOCAL_EMBEDDING_MODEL.get_embedding_dimension())
        except ImportError:
            raise RuntimeError(
                "sentence-transformers 未安装，请运行: pip install sentence-transformers"
            )
    return _LOCAL_EMBEDDING_MODEL


def use_local_embedding() -> bool:
    """判断是否使用本地嵌入（OPENAI_EMBEDDING_MODEL 为 'local' 或未配置时启用）。"""
    model = get_embedding_model_name()
    return model.lower() == "local"


# ── 向量数据库存储类 ─────────────────────────────────────────────

class VectorStore:
    def __init__(
        self,
        collection_name: str = "course_docs",
        persist_directory: Path | str | None = None,
    ) -> None:
        """
        初始化向量数据库。

        参数：
          collection_name: 向量库集合名称。
          persist_directory: 持久化存储目录。默认从系统 BASE_DIR 自动推导。
        """
        if persist_directory is None:
            persist_directory = VECTOR_DIR
        else:
            persist_directory = Path(persist_directory)

        self.client = chromadb.PersistentClient(path=str(persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._use_local = use_local_embedding()
        if self._use_local:
            self.embedding_model = _resolve_local_model_name()
            logger.info("使用本地嵌入模型: %s", self.embedding_model)
        else:
            self.embedding_model = get_embedding_model_name()
            logger.info("使用远程嵌入模型: %s", self.embedding_model)

    # ── 嵌入 ──────────────────────────────────────────────────────

    def _get_client(self) -> OpenAI:
        """获取并返回 OpenAI 客户端。"""
        return get_openai_client()

    def get_embedding(self, text: str) -> list[float]:
        """
        生成单条文本的向量嵌入。

        参数：
          text: 输入的文本内容。

        返回值：
          一个代表该文本的浮点数向量列表。
        """
        if self._use_local:
            model = _get_local_embedding_model()
            return model.encode(text, normalize_embeddings=True).tolist()
        resp = self._get_client().embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return resp.data[0].embedding

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成文本的向量嵌入。

        参数：
          texts: 输入的文本列表。

        返回值：
          每一项代表对应文本向量的嵌套浮点数列表。
        """
        if self._use_local:
            model = _get_local_embedding_model()
            logger.info("正在本地编码 %d 段文本（较大模型需要时间，请耐心等待）…", len(texts))
            vecs = model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=True,
            )
            logger.info("本地编码完成。")
            return [v.tolist() for v in vecs]
        resp = self._get_client().embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in resp.data]

    # ── 写入 ──────────────────────────────────────────────────────

    def add_documents(self, docs: list[dict], batch_size: int = 64) -> None:
        """
        向向量数据库添加或更新（upsert）清洗后的文档块列表。

        参数：
          docs: 待摄入的文档字典列表。
          batch_size: 每次请求写入数据库的分批条数。
        """
        if not docs:
            logger.warning("没有可写入向量库的文档。")
            return

        total = len(docs)
        for i in range(0, total, batch_size):
            batch = docs[i : i + batch_size]
            ids = [d["id"] for d in batch]
            texts = [d["text"] for d in batch]
            metadatas = [d["metadata"] for d in batch]

            end = min(i + batch_size, total)
            logger.info("编码 %d/%d 文本块…", end, total)
            embeddings = self.get_embeddings(texts)

            self.collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            logger.info("已写入 %d/%d 块。", end, total)

    # ── 搜索 ──────────────────────────────────────────────────────

    def hybrid_search(
        self,
        query: str,
        keyword: str | None = None,
        top_k: int = 5,
        where: dict | None = None,
        max_distance: float | None = None,
    ) -> list[dict]:
        """
        混合搜索：向量语义搜索 + 可选元数据过滤 + 服务端关键词包含性过滤（where_document）。

        参数：
          query: 语义搜索问题。
          keyword: 用于强关键词过滤匹配的字符串（若有）。
          top_k: 返回最相似结果的数量上限。
          where: SQL 风格元数据字典过滤条件。
          max_distance: 过滤余弦距离上限（0=最相似，2=相反）。

        返回值：
          符合过滤条件且距离最接近的前 K 个文档片段字典列表。
        """
        query_embedding = self.get_embedding(query)

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where
        if keyword:
            query_kwargs["where_document"] = {"$contains": keyword}

        try:
            results = self.collection.query(**query_kwargs)
        except (ValueError, TypeError, RuntimeError) as exc:
            logger.warning("检索发生错误，回退为纯向量搜索: %s", exc)
            query_kwargs.pop("where", None)
            query_kwargs.pop("where_document", None)
            results = self.collection.query(**query_kwargs)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        retrieved: list[dict] = []
        for idx, (doc, meta) in enumerate(zip(docs, metas)):
            dist = distances[idx] if idx < len(distances) else None
            if max_distance is not None and dist is not None:
                if dist > max_distance:
                    continue
            retrieved.append({
                "text": doc,
                "source": meta.get("source", "unknown") if meta else "unknown",
                "metadata": meta,
                "score": dist,
            })

        return retrieved

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
        max_distance: float | None = None,
    ) -> list[dict]:
        """
        语义向量检索（与原接口兼容）。

        参数：
          query: 查询字符串。
          top_k: 返回结果条数。
          where: 过滤字典。
          max_distance: 余弦距离上限。

        返回值：
          最相似的前 K 条结果字典列表。
        """
        return self.hybrid_search(
            query=query,
            keyword=None,
            top_k=top_k,
            where=where,
            max_distance=max_distance,
        )

    # ── 管理工具 ──────────────────────────────────────────────────

    def count(self) -> int:
        """返回当前集合中的文档块总数。"""
        return self.collection.count()

    def list_sources(self) -> list[str]:
        """
        获取向量数据库中所有独立、不重复的文档来源文件名（分批查询优化性能）。

        返回值：
          已排序的独立文件名列表。
        """
        total = self.count()
        if total == 0:
            return []
        
        sources: set[str] = set()
        limit = 1000
        for offset in range(0, total, limit):
            batch = self.collection.get(
                include=["metadatas"],
                limit=limit,
                offset=offset,
            )
            metas = batch.get("metadatas")
            if metas:
                for m in metas:
                    if m and m.get("source"):
                        sources.add(m["source"])
        
        return sorted(list(sources))

    def delete_collection(self, confirm: bool = False) -> None:
        """
        删除整个文档集合。

        参数：
          confirm: 必须传入 True 以显式确认，否则拒绝删除。
        """
        if not confirm:
            raise RuntimeError(
                "delete_collection 需要 confirm=True 确认。此操作不可逆，请谨慎。"
            )
        self.client.delete_collection(self.collection.name)
        logger.info("集合 \"%s\" 已删除。", self.collection.name)

