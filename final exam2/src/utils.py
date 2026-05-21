"""
utils.py
========
公共工具模块：环境变量读取、LLM 客户端工厂、日志配置。
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# ── 显式初始化 ────────────────────────────────────────────────────

def init_env(env_path: str | None = None) -> None:
    """显式加载 .env 文件（避免 import 时副作用，便于测试隔离）。"""
    load_dotenv(env_path)
    # 自动设置 HuggingFace 镜像（国内网络环境需要）
    if not os.environ.get("HF_ENDPOINT"):
        hf_endpoint = clean_env("HF_ENDPOINT", "https://hf-mirror.com")
        if hf_endpoint:
            os.environ["HF_ENDPOINT"] = hf_endpoint

# ── 日志 ──────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """返回带统一格式的 logger。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ── 环境变量 ──────────────────────────────────────────────────────

def clean_env(name: str, default: str | None = None) -> str | None:
    """读取环境变量并去除首尾空白与引号。"""
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip().strip("\"").strip("'")


# ── OpenAI 客户端 ─────────────────────────────────────────────────

_client_cache: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """创建并返回 OpenAI 全局单例客户端。"""
    global _client_cache
    if _client_cache is not None:
        return _client_cache
    api_key = clean_env("OPENAI_API_KEY")
    base_url = clean_env("OPENAI_BASE_URL")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 未配置，请检查 .env 文件。")
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    _client_cache = OpenAI(**kwargs)  # type: ignore[arg-type]
    return _client_cache


def get_model_name() -> str:
    """返回配置的 LLM 模型名。"""
    return clean_env("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"


def get_embedding_model_name() -> str:
    """
    返回配置的 Embedding 模型名（未配置时默认返回 'local' 表示使用本地模型）。
    注：若配置了 OPENAI_API_KEY 但未配置此项，将明确回退为使用本地模型。
    """
    return clean_env("OPENAI_EMBEDDING_MODEL", "local") or "local"

