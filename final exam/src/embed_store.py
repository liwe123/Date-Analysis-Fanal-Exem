"""
embed_store.py
==============
向量存储与检索模块（ChromaDB + OpenAI-compatible 或本地 HuggingFace 嵌入）。

升级内容：
  - 支持带元数据过滤的混合搜索（向量语义 + where 条件）
  - 新增 similarity_threshold 过滤（只返回相似度足够高的结果）
  - 新增 delete_collection / list_sources 工具方法
  - 批量写入时打印进度
  - 支持本地 HuggingFace 嵌入模型（无需 OpenAI Embedding API）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.utils import get_logger, get_openai_client, clean_env

logger = get_logger("embed_store")

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DIR = BASE_DIR / "vector_store"

# ── 本地嵌入模型 ──────────────────────────────────────────────────────────────

_LOCAL_EMBEDDING_MODEL: Any = None
_LOCAL_MODEL_NAME = None  # 从环境变量动态读取


def _resolve_local_model_name() -> str:
    """获取本地嵌入模型名（优先 LOCAL_EMBEDDING_MODEL 环境变量，否则默认 all-MiniLM-L6-v2）。"""
    model = clean_env("LOCAL_EMBEDDING_MODEL")
    if model and model.strip():
        return model.strip()
    return "all-MiniLM-L6-v2"


def _get_local_embedding_model():
    """懒加载本地 sentence-transformers 模型（全局单例，GPU 优先）。"""
    global _LOCAL_EMBEDDING_MODEL, _LOCAL_MODEL_NAME
    if _LOCAL_EMBEDDING_MODEL is None:
        _LOCAL_MODEL_NAME = _resolve_local_model_name()
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("正在加载本地嵌入模型 '%s'（设备: %s）…", _LOCAL_MODEL_NAME, device)
            _LOCAL_EMBEDDING_MODEL = SentenceTransformer(_LOCAL_MODEL_NAME, device=device)
            logger.info("本地嵌入模型加载完成（%d 维）。", _LOCAL_EMBEDDING_MODEL.get_sentence_embedding_dimension())
        except ImportError:
            raise RuntimeError(
                "sentence-transformers 未安装，请运行: pip install sentence-transformers"
            )
    return _LOCAL_EMBEDDING_MODEL


def use_local_embedding() -> bool:
    """判断是否使用本地嵌入（OPENAI_EMBEDDING_MODEL 未配置或为 'local' 时启用）。"""
    model = clean_env("OPENAI_EMBEDDING_MODEL")
    return model is None or model == "" or model.lower() == "local"


class VectorStore:
    def __init__(self, collection_name: str = "course_docs"):
        self.client = chromadb.PersistentClient(path=str(VECTOR_DIR))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._use_local = use_local_embedding()
        if self._use_local:
            self.embedding_model = _resolve_local_model_name()
            logger.info("使用本地嵌入模型: %s", self.embedding_model)
        else:
            self.embedding_model = clean_env("OPENAI_EMBEDDING_MODEL") or ""
            logger.info("使用远程嵌入模型: %s", self.embedding_model)

    # ── 嵌入 ──────────────────────────────────────────────────────────────────

    def _get_client(self):
        return get_openai_client()

    def get_embedding(self, text: str) -> list[float]:
        if self._use_local:
            model = _get_local_embedding_model()
            return model.encode(text, normalize_embeddings=True).tolist()
        resp = self._get_client().embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return resp.data[0].embedding

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
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

    # ── 写入 ──────────────────────────────────────────────────────────────────

    def add_documents(self, docs: list[dict], batch_size: int = 64) -> None:
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

    # ── 搜索 ──────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
        max_distance: float | None = None,
    ) -> list[dict]:
        """
        混合搜索：向量语义搜索 + 可选元数据过滤。

        参数 max_distance：余弦距离上限（0=最相似，2=完全相反），超过此值的结果被过滤。
        返回 list[dict]，每项包含 text / source / metadata / score(余弦距离) 字段。
        """
        query_embedding = self.get_embedding(query)

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        try:
            results = self.collection.query(**query_kwargs)
        except (ValueError, TypeError, RuntimeError) as exc:
            logger.warning("where 条件无匹配，回退为纯向量搜索: %s", exc)
            query_kwargs.pop("where", None)
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
                "source": meta.get("source", "unknown"),
                "metadata": meta,
                "score": dist,
            })

        return retrieved

    # ── 管理工具 ──────────────────────────────────────────────────────────────

    def count(self) -> int:
        return self.collection.count()

    def list_sources(self) -> list[str]:
        """返回向量库中所有不重复的文档来源文件名。"""
        if self.count() == 0:
            return []
        all_metas = self.collection.get(include=["metadatas"])["metadatas"]
        sources = sorted({m.get("source", "") for m in all_metas if m.get("source")})
        return sources

    def delete_collection(self, confirm: bool = False) -> None:
        """删除当前集合（需显式 confirm=True 确认，否则抛出）。"""
        if not confirm:
            raise RuntimeError(
                "delete_collection 需要 confirm=True 确认。此操作不可逆，请谨慎。"
            )
        self.client.delete_collection(self.collection.name)
        logger.info("集合 '%s' 已删除。", self.collection.name)
