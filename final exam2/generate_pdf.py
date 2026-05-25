"""
generate_pdf.py
===============
将报告 Markdown 生成为双栏 PDF（IEEE/NeurIPS 风格）。
"""

from __future__ import annotations

import re
from pathlib import Path

from xhtml2pdf import pisa

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "report" / "report_v2.md", "r", encoding="utf-8") as f:
    md_text = f.read()


# ── Markdown → HTML 简单转换 ──────────────────────────────────

def md_to_html(text: str) -> str:
    text = text.replace("\n\n", "{{PARA}}")
    lines = text.split("\n")

    html_parts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 标题
        if line.startswith("## "):
            html_parts.append(f"<h1>{line[3:].strip()}</h1>")
        elif line.startswith("### "):
            html_parts.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("# "):
            html_parts.append(f'<div class="title-page">{line[2:].strip()}</div>')

        # 表格
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1
            html_parts.append(_render_table(table_lines))

        # 代码块
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            html_parts.append(f'<pre>{"".join(code_lines)}</pre>')

        # 分隔线
        elif line.startswith("---"):
            html_parts.append('<hr class="section-hr">')

        # 引用
        elif line.startswith("> "):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip()[2:])
                i += 1
            i -= 1
            html_parts.append(f'<blockquote>{"<br/>".join(block)}</blockquote>')

        # 列表
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            i -= 1
            content = "".join(f"<li>{item}</li>" for item in items)
            html_parts.append(f"<ul>{content}</ul>")

        # 普通段落
        else:
            para = line.replace("{{PARA}}", "<br/>")
            # 粗体
            para = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", para)
            # 斜体
            para = re.sub(r"\*(.+?)\*", r"<i>\1</i>", para)
            # 代码
            para = re.sub(r"`([^`]+)`", r"<code>\1</code>", para)
            para = para.replace("{{PARA}}", "<br/>")
            html_parts.append(f"<p>{para}</p>")

        i += 1

    return "\n".join(html_parts)


def _render_table(lines: list[str]) -> str:
    if not lines:
        return ""
    # 第一行是表头
    header_cells = [c.strip() for c in lines[0].strip("| ").split("|")]
    thead = "<tr>" + "".join(f"<th>{c}</th>" for c in header_cells) + "</tr>"

    data_rows = []
    for line in lines[1:]:
        if re.match(r"^[\|\-\:\s]+$", line.strip()):
            continue
        cells = [c.strip() for c in line.strip("| ").split("|")]
        data_rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

    rows_html = thead + "".join(data_rows)
    return f'<table>{rows_html}</table>'


body_html = md_to_html(md_text)

# ── 完整 HTML + CSS (双栏, IEEE 风格) ────────────────────────

html_content = f"""\
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 1.8cm 1.5cm 1.8cm 1.5cm;
    @frame header_frame {{
      -pdf-frame-content: header_content;
      left: 1.5cm; top: 1cm;
      width: 18cm; height: 0.8cm;
    }}
    @frame footer_frame {{
      -pdf-frame-content: footer_content;
      left: 1.5cm; bottom: 1.2cm;
      width: 18cm; height: 0.6cm;
    }}
  }}

  body {{
    font-family: "SimSun", serif;
    font-size: 9pt;
    line-height: 1.4;
    color: #111;
    column-count: 2;
    column-gap: 1.8em;
  }}

  .title-page {{
    column-span: all;
    text-align: center;
    font-size: 16pt;
    font-weight: bold;
    margin-bottom: 0.5em;
    border-bottom: 2px solid #333;
    padding-bottom: 0.3em;
  }}

  h1 {{
    font-size: 11pt;
    font-weight: bold;
    margin-top: 1em;
    margin-bottom: 0.4em;
    color: #222;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.15em;
  }}

  h2 {{
    font-size: 10pt;
    font-weight: bold;
    margin-top: 0.8em;
    margin-bottom: 0.3em;
  }}

  p {{
    margin: 0.3em 0;
    text-align: justify;
  }}

  ul, ol {{
    margin: 0.3em 0;
    padding-left: 1.2em;
  }}

  li {{
    margin: 0.15em 0;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 0.5em 0;
  }}

  th {{
    background: #eee;
    font-weight: bold;
    text-align: left;
    padding: 3px 5px;
    border: 0.5px solid #999;
  }}

  td {{
    padding: 2px 5px;
    border: 0.5px solid #ccc;
  }}

  pre {{
    font-size: 7.5pt;
    font-family: "Courier New", monospace;
    background: #f5f5f5;
    padding: 5px;
    border: 0.5px solid #ddd;
    overflow-x: auto;
  }}

  code {{
    font-family: "Courier New", monospace;
    font-size: 8pt;
    background: #f5f5f5;
    padding: 1px 3px;
  }}

  blockquote {{
    border-left: 3px solid #aaa;
    padding-left: 8px;
    margin: 0.4em 0;
    font-style: italic;
    color: #555;
    font-size: 8.5pt;
  }}

  b {{
    font-weight: bold;
  }}

  .section-hr {{
    display: none;
  }}

  .checkmark {{ color: green; }}

  hr {{ border: none; border-top: 0.5px dashed #ccc; margin: 0.5em 0; }}

</style>
</head>
<body>

<div id="header_content" style="font-size:7pt;text-align:center;color:#888;">
  RAG 知识库检索增强生成系统 — 工程设计文档 | 方向 B：智能客户支持与检索增强生成助手
</div>

<div id="footer_content" style="font-size:7pt;text-align:right;color:#888;">
  第 <pdf:pagenumber/> 页
</div>

<h1 style="column-span:all;text-align:center;font-size:16pt;border:none;">
  RAG 知识库检索增强生成系统：工程设计文档
</h1>
<p style="column-span:all;text-align:center;font-size:9pt;color:#555;margin-bottom:1em;">
  方向 B：智能客户支持与检索增强生成助手
</p>

{body_html}

</body>
</html>
"""

output_path = BASE_DIR / "report" / "report.pdf"
with open(output_path, "wb") as f_out:
    pisa.CreatePDF(html_content, dest=f_out, encoding="utf-8")

print(f"PDF 已生成: {output_path}")
print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")
