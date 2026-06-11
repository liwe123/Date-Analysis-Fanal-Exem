# scripts 目录说明

本目录收纳项目运行之外的辅助脚本，避免根目录混杂评估、报告生成和演示工具。

## reporting

- `reporting/evaluation.py`：运行 50 题 RAG 评估，默认输出到 `report/evaluation_results.json`。
- `reporting/latency_benchmark.py`：运行端到端延迟分解，默认输出到 `report/latency_results.json`。
- `reporting/generate_pdf_ieee.py`：从内置排版内容生成 `report/report_ieee.pdf`。

## demo

- `demo/demo_companion.py`：答辩现场辅助演示脚本，用于展示查询生命周期、问题复盘和成本估算。

## deployment

- `embedding_server.py`：远程 Embedding FastAPI 服务。
- `setup_autodl.sh`：AutoDL 环境初始化脚本。

## report assets

- `generate_task_division_pdf.py`：生成团队分工 PDF。
- `generate_onboarding_pdf.py`：生成成员上手指南 PDF。
- `generate_defense_qa_pdf.py`：生成答辩问答指南 PDF。
