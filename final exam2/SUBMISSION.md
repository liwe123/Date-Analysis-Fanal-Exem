# 最终提交与验收清单

本文档用于快速确认项目交付内容、运行方式和验证路径。

## 交付入口

- 项目说明：`README.md`
- 开发与修改规范：`AGENTS.md`
- 最终论文：`report/report_ieee.html`
- PDF 快照：`report/report_ieee.pdf`
- 报告目录索引：`report/README.md`
- 自动化测试：`tests/`
- 核心源码：`src/`
- Web 入口：`app/streamlit_app.py`
- CLI 入口：`src/main.py`

## 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

在 `.env` 中填写 `OPENAI_API_KEY`。如果使用远程 Embedding 服务，还需要配置
`OPENAI_EMBEDDING_MODEL=remote`、`OPENAI_EMBEDDING_BASE_URL` 和
`EMBEDDING_SERVER_TOKEN`。

## 运行系统

构建或更新向量库：

```bash
python -m src.main build --metadata-strategy jsonl_only
```

命令行问答：

```bash
python -m src.main ask --question "大数据学期项目的提交要求是什么？"
```

启动 Web 界面：

```bash
streamlit run app/streamlit_app.py
```

答辩辅助演示：

```bash
python scripts/demo/demo_companion.py
```

## 验证命令

自动化测试：

```bash
python -m pytest tests/ -v
```

快速测试：

```bash
python -m pytest tests/ -q
```

当前整理后已验证：`91 passed`。

## 评估与报告生成

重新运行 50 题 RAG 评估：

```bash
python scripts/reporting/evaluation.py
```

重新运行延迟分解：

```bash
python scripts/reporting/latency_benchmark.py
```

重新生成 IEEE PDF：

```bash
python scripts/reporting/generate_pdf_ieee.py
```

评估输出默认写入：

- `report/evaluation_results.json`
- `report/latency_results.json`

## 提交前检查

- `python -m pytest tests/ -q` 通过。
- `report/report_ieee.html` 可在浏览器打开。
- `report/evaluation_results.json` 和 `report/latency_results.json` 与报告中的指标一致。
- `.env` 未提交，`.env.example` 保留可复现配置说明。
- 根目录保持清爽：源码、报告、数据、脚本和测试分区明确。
