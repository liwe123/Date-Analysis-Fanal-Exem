#!/usr/bin/env bash
# ==============================================================================
# setup_autodl.sh
# AutoDL 一键部署脚本：安装依赖 → 预下载模型 → 启动嵌入服务
#
# 使用方式：
#   chmod +x setup_autodl.sh
#   bash setup_autodl.sh
#
# 说明：
#   - 本脚本适用于 AutoDL 平台（推荐 RTX 4090 实例）
#   - 默认使用 HuggingFace 中国镜像加速模型下载
#   - 服务启动后监听 0.0.0.0:6008（AutoDL 自定义服务默认端口）
#   - 通过 AutoDL 控制台「自定义服务」即可公网访问
# ==============================================================================

set -e  # 任何命令失败立即退出

# ── 配置变量 ──────────────────────────────────────────────
MODEL_NAME="BAAI/bge-large-zh-v1.5"
PORT=6008
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_SCRIPT="${SCRIPT_DIR}/embedding_server.py"

# ── 设置 HuggingFace 镜像端点（国内加速下载） ────────────
export HF_ENDPOINT="https://hf-mirror.com"
echo "[INFO] 已设置 HF_ENDPOINT=${HF_ENDPOINT}"

# ── 第一步：安装 Python 依赖 ─────────────────────────────
echo ""
echo "=============================================="
echo "  第一步：安装 Python 依赖"
echo "=============================================="

pip install --upgrade pip

# fastapi       — Web 框架
# uvicorn       — ASGI 服务器
# sentence-transformers — 嵌入模型加载与编码
# torch         — 深度学习框架（GPU 推理）
pip install fastapi uvicorn sentence-transformers torch

echo "[INFO] 依赖安装完成"

# ── 第二步：预下载模型 ───────────────────────────────────
echo ""
echo "=============================================="
echo "  第二步：预下载模型 ${MODEL_NAME}"
echo "=============================================="

# 使用 Python 预下载模型到本地缓存，避免首次请求时下载导致超时
python -c "
import os
os.environ['HF_ENDPOINT'] = '${HF_ENDPOINT}'
from sentence_transformers import SentenceTransformer
print('[INFO] 正在下载模型: ${MODEL_NAME} ...')
model = SentenceTransformer('${MODEL_NAME}')
dim = model.get_sentence_embedding_dimension()
print(f'[INFO] 模型下载完成 — 嵌入维度: {dim}')
"

echo "[INFO] 模型预下载完成"

# ── 第三步：启动嵌入服务 ─────────────────────────────────
echo ""
echo "=============================================="
echo "  第三步：启动嵌入服务"
echo "  端口: ${PORT}"
echo "  模型: ${MODEL_NAME}"
echo "=============================================="
echo ""
echo "[INFO] 服务即将启动，使用 Ctrl+C 可停止"
echo "[INFO] 健康检查地址: http://0.0.0.0:${PORT}/health"
echo "[INFO] 嵌入接口地址: http://0.0.0.0:${PORT}/v1/embeddings"
echo ""

python "${SERVER_SCRIPT}" --model "${MODEL_NAME}" --port "${PORT}"
