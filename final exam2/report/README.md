# report 目录索引

本目录存放最终论文、答辩材料、评估证据和历史草稿。提交或展示时优先使用“最终交付文件”一节中的内容。

## 最终交付文件

- `report_ieee.html`：推荐提交和打印的最终论文版本，可直接用浏览器打开并导出 PDF。
- `report_ieee.pdf`：与最终论文对应的 PDF 快照，适合离线提交或快速预览。
- `task_division.md` / `task_division.pdf`：团队成员任务分工说明。
- `defense_qa_guide.md` / `defense_qa_guide.pdf`：答辩常见问题与回答要点。
- `member_onboarding_guide.md` / `member_onboarding_guide.pdf`：项目结构、运行命令和演示流程说明。
- `presentation_guide.md`：15 分钟现场演示节奏与讲解词。

## 评估证据

- `evaluation_results.json`：50 题 RAG 评估结果，包含 Recall@3、越界问题、幻觉次数和平均延迟。
- `latency_results.json`：查询解析、检索、生成和端到端延迟分解。
- `failure_analysis.md`：失败案例、边界行为和改进方向复盘。

这些文件是报告中指标叙述的证据来源。修改报告指标前，应先重新运行对应评估脚本并确认数据一致。

## 历史草稿

- `report.md`：较完整的技术报告草稿。
- `report_v2.md`：历史修订草稿，可能存在旧指标口径。
- `report_ieee.tex`：LaTeX 版论文源文件，当前最终交付优先使用 `report_ieee.html`。
- `architecture_diagram.md`：架构图说明材料。
- `resume_project.md`：早期项目简历式总结。

历史草稿用于追溯写作过程，不作为最终指标口径来源。

## 重新生成

```bash
python scripts/reporting/evaluation.py
python scripts/reporting/latency_benchmark.py
python scripts/reporting/generate_pdf_ieee.py
python scripts/generate_task_division_pdf.py
python scripts/generate_defense_qa_pdf.py
python scripts/generate_onboarding_pdf.py
```
