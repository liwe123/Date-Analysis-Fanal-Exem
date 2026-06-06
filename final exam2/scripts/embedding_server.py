"""
embedding_server.py
====================
AutoDL 远程嵌入服务：基于 FastAPI 的 OpenAI 兼容 Embedding API。

使用方式：
  python embedding_server.py --model BAAI/bge-large-zh-v1.5 --port 6008
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# ── 日志配置 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 全局变量 ─────────────────────────────────────────────
# 模型实例与元信息，在 startup 事件中初始化
_model: SentenceTransformer | None = None
_model_name: str = ""
_device: str = ""
_dimension: int = 0

# 单次请求允许的最大文本数量
MAX_BATCH_SIZE: int = 512
EMBEDDING_SERVER_TOKEN_ENV = "EMBEDDING_SERVER_TOKEN"

# ── 请求 / 响应数据模型 ──────────────────────────────────

class EmbeddingRequest(BaseModel):
    """OpenAI 兼容的嵌入请求体。"""

    input: str | list[str] = Field(..., description="待编码的文本或文本列表")
    model: str = Field(default="", description="模型名称（兼容字段，实际使用服务端加载的模型）")
    encoding_format: str = Field(default="float", description="编码格式")


class EmbeddingObject(BaseModel):
    """单条嵌入结果。"""

    object: str = "embedding"
    embedding: list[float]
    index: int


class UsageInfo(BaseModel):
    """Token 用量信息（嵌入服务不计算 token，保持兼容格式）。"""

    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingResponse(BaseModel):
    """OpenAI 兼容的嵌入响应体。"""

    object: str = "list"
    data: list[EmbeddingObject]
    model: str
    usage: UsageInfo = Field(default_factory=UsageInfo)


# ── FastAPI 应用 ─────────────────────────────────────────
app = FastAPI(
    title="Embedding Server",
    description="AutoDL 远程嵌入服务 — OpenAI 兼容 API",
    version="1.0.0",
)

# 允许跨域访问，方便前端或其他服务调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 模型加载 ─────────────────────────────────────────────

def load_model(model_name: str) -> None:
    """加载 SentenceTransformer 模型到 GPU（若可用）。"""
    global _model, _model_name, _device, _dimension

    # 设置 HuggingFace 镜像端点（国内加速下载）
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ["HF_ENDPOINT"] = hf_endpoint
    logger.info("HF_ENDPOINT = %s", hf_endpoint)

    # 选择计算设备
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("使用设备: %s", _device)

    if _device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        logger.info("GPU: %s (%.1f GB)", gpu_name, gpu_mem)

    logger.info("正在加载模型: %s ...", model_name)
    start = time.perf_counter()

    _model = SentenceTransformer(model_name, device=_device)
    _model_name = model_name

    # 获取嵌入维度：编码一个空字符串来探测
    _dimension = _model.get_sentence_embedding_dimension() or 0

    elapsed = time.perf_counter() - start
    logger.info(
        "模型加载完成 — 维度: %d, 耗时: %.2f 秒",
        _dimension,
        elapsed,
    )


# ── 路由 ─────────────────────────────────────────────────

@app.get("/health")
def health_check() -> dict[str, Any]:
    """健康检查端点，返回模型信息、设备和维度。"""
    return {
        "status": "healthy",
        "model": _model_name,
        "device": _device,
        "dimension": _dimension,
    }


def _verify_token(authorization: str | None) -> None:
    """在配置 token 时校验 Bearer 授权头。"""
    expected_token = os.environ.get(EMBEDDING_SERVER_TOKEN_ENV, "").strip()
    if not expected_token:
        return

    expected_header = f"Bearer {expected_token}"
    if authorization != expected_header:
        raise HTTPException(status_code=401, detail="远程嵌入服务授权失败")


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
def create_embeddings(
    request: EmbeddingRequest,
    authorization: str | None = Header(default=None),
) -> EmbeddingResponse:
    """
    生成文本嵌入向量，兼容 OpenAI ``/v1/embeddings`` 接口格式。

    支持单条文本（str）或批量文本（list[str]），最多 512 条。
    """
    _verify_token(authorization)

    if _model is None:
        raise HTTPException(status_code=503, detail="模型尚未加载完成，请稍后重试")

    # 统一为列表处理
    texts: list[str] = (
        [request.input] if isinstance(request.input, str) else request.input
    )

    # 校验批量大小
    if len(texts) == 0:
        raise HTTPException(status_code=400, detail="输入文本不能为空")

    if len(texts) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"单次请求最多 {MAX_BATCH_SIZE} 条文本，当前 {len(texts)} 条",
        )

    # 编码
    logger.info("收到嵌入请求 — 批量大小: %d", len(texts))
    start = time.perf_counter()

    try:
        embeddings = _model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.error("编码失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"编码失败: {exc}") from exc

    elapsed = time.perf_counter() - start
    logger.info(
        "编码完成 — 批量大小: %d, 耗时: %.4f 秒, 平均: %.4f 秒/条",
        len(texts),
        elapsed,
        elapsed / len(texts),
    )

    # 构造响应
    data = [
        EmbeddingObject(
            embedding=emb.tolist(),
            index=idx,
        )
        for idx, emb in enumerate(embeddings)
    ]

    return EmbeddingResponse(
        data=data,
        model=_model_name,
    )


# ── 入口 ─────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="AutoDL 远程嵌入服务：OpenAI 兼容 Embedding API",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="BAAI/bge-large-zh-v1.5",
        help="HuggingFace 模型名称（默认: BAAI/bge-large-zh-v1.5）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6008,
        help="服务监听端口（默认: 6008，AutoDL 自定义服务默认端口）",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 在启动 uvicorn 之前加载模型，确保模型就绪后才接受请求
    load_model(args.model)

    logger.info("启动嵌入服务 — 端口: %d", args.port)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        log_level="info",
    )
