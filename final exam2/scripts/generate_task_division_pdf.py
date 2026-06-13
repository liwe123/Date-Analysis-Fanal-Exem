# -*- coding: utf-8 -*-
"""
generate_task_division_pdf.py
============================
将团队分工与职责说明 (task_division.md) 完美编译生成为高清晰、专业排版的 PDF 文件。
"""

from __future__ import annotations

from pathlib import Path
import re

from fpdf import FPDF

# ── 路径配置 ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = Path("C:/Windows/Fonts")
OUTPUT_PDF = BASE_DIR / "report" / "task_division.pdf"

# ── Emojis 清洗工具 ───────────────────────────────────
def clean_emojis(text: str) -> str:
    """
    清洗文本中的 Emojis 符号以防止中文字体缺少 Glyphs 警告或在 PDF 中显示为空白方块。
    """
    emojis = ["👑", "🧑‍💻", "🎨", "🧪", "🎯", "📈", "🗣️", "➕", "💡", "🛡️", "🌟", "🔥", "🚀"]
    cleaned = text
    for emoji in emojis:
        cleaned = cleaned.replace(emoji, "")
    # 清洗未在列表中捕获的零宽字符或复杂组合 Emojis
    cleaned = cleaned.replace("\u200d", "") # 零宽连字符
    return cleaned

# ── 文本精细分行工具 ───────────────────────────────────
def split_text_to_lines(pdf: FPDF, text: str, max_w: float) -> list[str]:
    """
    根据 FPDF 当前字体和最大宽度，将包含中英文的文本精确切分成多行，以便在栏宽内自动换行。
    """
    clean_text = clean_emojis(text)
    tokens = re.findall(
        r"[a-zA-Z0-9_./%+\-——'\"#&*=<>():;@\[\]{}?？,，.!！]+|[\u4e00-\u9fa5]|[，。！？；：（）“”‘’《》、—]|\s+|[^a-zA-Z0-9\s]",
        clean_text
    )
    lines = []
    current_line = ""
    for token in tokens:
        if token.strip() == "":
            if current_line != "" and not current_line.endswith(" "):
                test_line = current_line + " "
                if pdf.get_string_width(test_line) <= max_w:
                    current_line = test_line
            continue
        test_line = current_line + token
        if pdf.get_string_width(test_line) > max_w:
            if current_line:
                lines.append(current_line.rstrip())
                current_line = token
            else:
                lines.append(token)
                current_line = ""
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line.rstrip())
    return lines

# ── FPDF 页面架构设计 ──────────────────────────────────
class TaskDivisionPdf(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(20.0, 20.0, 20.0)
        self.set_auto_page_break(True, margin=20)
        
        # 加载中文字体 SimFang (仿宋) 与 SimHei (黑体)
        self.add_font("cn", "", str(FONT_DIR / "simfang.ttf"))
        self.add_font("cn", "B", str(FONT_DIR / "simhei.ttf"))
        
        # 页面总可用宽度：210 - 20 * 2 = 170mm
        self.PW = 170.0

    def header(self):
        """绘制精美且专业的页眉。"""
        if self.page_no() == 1:
            return
        self.set_font("cn", "", 7.5)
        self.set_text_color(140, 140, 140)
        self.cell(self.PW, 4, "RAG 知识库检索增强生成系统 — 团队分工与职责说明", align="L")
        self.set_xy(20.0, self.get_y() + 4.5)
        
        # 绘制一条精致的页眉分割线
        self.set_draw_color(220, 225, 230)
        self.set_line_width(0.2)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_y(self.get_y() + 5.0)

    def footer(self):
        """绘制带页码的页脚。"""
        self.set_y(-15)
        
        # 绘制页脚分割线
        self.set_draw_color(230, 235, 240)
        self.set_line_width(0.15)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        
        self.set_y(-12)
        self.set_font("cn", "", 8.0)
        self.set_text_color(160, 160, 160)
        self.cell(self.PW, 6, f"— {self.page_no()} —", align="C")

    # ── 标题与正文样式 ──
    def main_title(self, title: str):
        """绘制主标题。"""
        self.ln(5.0)
        self.set_font("cn", "B", 18)
        self.set_text_color(30, 58, 138)  # 深蓝色 (Deep Navy Blue)
        self.cell(self.PW, 10, clean_emojis(title), align="C")
        self.ln(10.0)
        
        # 绘制精致的双重底线
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.5)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_line_width(0.15)
        self.line(20.0, self.get_y() + 1.0, 190.0, self.get_y() + 1.0)
        self.ln(6.0)

    def h1(self, text: str):
        """一级标题样式。"""
        # 如果即将触底，先强制换页
        if self.get_y() > 255:
            self.add_page()
        self.ln(6.0)
        self.set_font("cn", "B", 12)
        self.set_text_color(30, 58, 138)
        self.cell(self.PW, 6, clean_emojis(text), align="L")
        self.ln(6.5)
        
        # 下划短实线
        y = self.get_y() - 0.5
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.6)
        self.line(20.0, y, 45.0, y)
        self.set_draw_color(220, 225, 230)
        self.set_line_width(0.2)
        self.line(45.0, y, 190.0, y)
        self.ln(3.5)

    def h2(self, text: str):
        """二级标题样式。"""
        if self.get_y() > 260:
            self.add_page()
        self.ln(4.5)
        self.set_font("cn", "B", 10)
        self.set_text_color(51, 65, 85)
        self.cell(self.PW, 5, clean_emojis(text), align="L")
        self.ln(6.0)

    def paragraph(self, text: str, bold_prefix: str = ""):
        """正文段落，带自动两端对齐。"""
        if self.get_y() > 265:
            self.add_page()
        self.set_font("cn", "", 9.5)
        self.set_text_color(51, 65, 85)
        
        full_text = clean_emojis(text)
        if bold_prefix:
            clean_prefix = clean_emojis(bold_prefix)
            self.set_font("cn", "B", 9.5)
            self.write(4.8, clean_prefix)
            self.set_font("cn", "", 9.5)
            
        lines = split_text_to_lines(self, full_text, self.PW)
        for idx, line in enumerate(lines):
            # 判断是否需要两端对齐
            line_w = self.get_string_width(line)
            is_last = (idx == len(lines) - 1)
            if not is_last and line_w > 0 and len(line) > 1 and line_w < self.PW:
                extra_space = self.PW - line_w
                extra_char_spacing = extra_space / (len(line) - 1)
                if extra_char_spacing < 1.5:
                    self.set_char_spacing(extra_char_spacing)
                    self.cell(self.PW, 4.8, line)
                    self.set_char_spacing(0.0)
                    self.ln(4.8)
                    continue
            self.cell(self.PW, 4.8, line)
            self.ln(4.8)
        self.ln(1.0)

    def bullet_list(self, items: list[str]):
        """带美化圆点的无序列表。"""
        self.set_font("cn", "", 9.5)
        self.set_text_color(51, 65, 85)
        for item in items:
            if self.get_y() > 265:
                self.add_page()
            
            clean_item = clean_emojis(item)
            
            # 绘制小圆点
            self.set_fill_color(30, 58, 138)
            y_curr = self.get_y()
            self.ellipse(23.5, y_curr + 1.8, 1.2, 1.2, "F")
            
            # 折行计算文本
            w_text = self.PW - 7.0
            lines = split_text_to_lines(self, clean_item, w_text)
            for idx, line in enumerate(lines):
                self.set_x(26.0)
                # 两端对齐
                line_w = self.get_string_width(line)
                is_last = (idx == len(lines) - 1)
                if not is_last and line_w > 0 and len(line) > 1 and line_w < w_text:
                    extra_space = w_text - line_w
                    extra_char_spacing = extra_space / (len(line) - 1)
                    if extra_char_spacing < 1.5:
                        self.set_char_spacing(extra_char_spacing)
                        self.cell(w_text, 4.6, line)
                        self.set_char_spacing(0.0)
                        self.ln(4.6)
                        continue
                self.cell(w_text, 4.6, line)
                self.ln(4.6)
            self.ln(0.8)

    # ── 表格绘制系统 ──
    def draw_task_table(self, headers: list[str], rows: list[list[str]], col_widths: list[float]):
        """绘制一张高度精美、文本自动折行的表格。"""
        self.ln(2.0)
        self.set_font("cn", "B", 9.0)
        self.set_fill_color(241, 245, 249) # 浅灰蓝色
        self.set_draw_color(200, 205, 215) # 极淡网格线
        self.set_line_width(0.18)
        
        # 1. 绘制表头
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8.0, clean_emojis(header), border=1, fill=True, align="C")
        self.ln()
        
        # 2. 绘制表身
        self.set_font("cn", "", 8.2)
        self.set_text_color(51, 65, 85)
        
        for row in rows:
            # 预先计算该行折行后的最大行高
            max_lines = 1
            row_line_data = []
            for i, cell in enumerate(row):
                cw = col_widths[i]
                clean_cell = clean_emojis(str(cell))
                # 分割 cell 的换行符 \n
                cell_paragraphs = clean_cell.split("\n")
                cell_lines = []
                for p in cell_paragraphs:
                    if p.strip():
                        cell_lines.extend(split_text_to_lines(self, p, cw - 4.0)) # 留出 4mm padding
                    else:
                        cell_lines.append("")
                max_lines = max(max_lines, len(cell_lines))
                row_line_data.append(cell_lines)
            
            # 单行高度 3.6mm，外加 padding 2.5mm
            row_height = max_lines * 3.6 + 3.0
            
            # 防割裂智能换页
            if self.get_y() + row_height > 270:
                self.add_page()
                # 重新绘制表头
                self.set_font("cn", "B", 9.0)
                self.set_fill_color(241, 245, 249)
                for i, header in enumerate(headers):
                    self.cell(col_widths[i], 8.0, clean_emojis(header), border=1, fill=True, align="C")
                self.ln()
                self.set_font("cn", "", 8.2)
            
            y_curr = self.get_y()
            x_curr = self.get_x()
            
            # 逐个单元格进行精确绘制
            for i, cell_lines in enumerate(row_line_data):
                cw = col_widths[i]
                
                # 绘制单元格边框与背景
                self.set_xy(x_curr, y_curr)
                self.rect(x_curr, y_curr, cw, row_height)
                
                # 计算垂直居中的起始 y 坐标
                y_text_start = y_curr + (row_height - len(cell_lines) * 3.6) / 2
                
                # 绘制文本行
                for line_idx, line_text in enumerate(cell_lines):
                    self.set_xy(x_curr + 2.0, y_text_start + line_idx * 3.6)
                    # 区分组长突出加粗
                    if "李伟 (组长)" in line_text or "[组长]" in line_text:
                        self.set_font("cn", "B", 8.2)
                        self.cell(cw - 4.0, 3.6, line_text, border=0)
                        self.set_font("cn", "", 8.2)
                    else:
                        self.cell(cw - 4.0, 3.6, line_text, border=0)
                
                x_curr += cw
            
            # 重置坐标到行底部
            self.set_xy(20.0, y_curr + row_height)
        self.ln(4.0)

    # ── 绘制时间轴图谱 ──
    def draw_timeline(self):
        """在 PDF 中绘制一张极具设计感、学术高级感的“协作开发流水线流程”垂直时间轴图谱。"""
        if self.get_y() > 180:
            self.add_page()
        self.ln(3.0)
        self.set_font("cn", "B", 9.5)
        self.set_text_color(30, 58, 138)
        self.cell(self.PW, 5, "图 2: 团队协作开发流水线流程时间轴", align="C")
        self.ln(6.0)

        steps = [
            ("第一阶段", "李伟 (组长)", "架构规划 & 模块抽象", "进行顶层系统设计与任务划分"),
            ("第二阶段", "张杰", "数据收集与清洗工程", "开发 API 爬虫，提取纯净 Markdown 数据"),
            ("第三阶段", "张杰 & 李伟", "云端算力卸载部署", "配置 AutoDL 云显卡，启动 FastAPI 计算服务器"),
            ("第四阶段", "李伟", "核心分块算法实现", "编写四层语义分块算法，写入 HNSW 持久层"),
            ("第五阶段", "王婷", "现代 UI/UX Streamlit 设计", "采用毛玻璃卡片设计，植入 XSS 防注入网关"),
            ("第六阶段", "刘洋", "测试用例开发与文档归纳", "编写 91 个全覆盖测试用例，归纳 HNSW 容灾备份"),
            ("第七阶段", "李伟 (组长)", "冒烟测试与最终交付", "全链路整合调试，推送到 Git 远程分支交付")
        ]

        x_line = 60.0 # 垂直轴线的 X 坐标
        y_start = self.get_y()
        total_h = len(steps) * 16.0
        
        # 1. 绘制垂直轴线（深灰色）
        self.set_draw_color(180, 185, 195)
        self.set_line_width(0.4)
        self.line(x_line, y_start + 2.0, x_line, y_start + total_h - 10.0)
        
        # 2. 绘制每个阶段的时间节点与文本卡片
        for idx, (stage, owner, action, desc) in enumerate(steps):
            y_curr = y_start + idx * 16.0
            
            # 绘制时间轴圆圈
            self.set_draw_color(30, 58, 138)
            self.set_fill_color(255, 255, 255)
            self.set_line_width(1.0)
            self.ellipse(x_line - 2.0, y_curr + 1.0, 4.0, 4.0, "DF")
            
            # 绘制圆圈中心核心实心点
            self.set_fill_color(30, 58, 138)
            self.ellipse(x_line - 0.8, y_curr + 2.2, 1.6, 1.6, "F")
            
            # 左侧文字：阶段与负责人
            self.set_font("cn", "B", 8.2)
            self.set_text_color(30, 58, 138)
            self.set_xy(20.0, y_curr + 0.5)
            self.cell(35.0, 4.0, stage, align="R")
            
            self.set_font("cn", "", 7.8)
            self.set_text_color(100, 100, 100)
            self.set_xy(20.0, y_curr + 4.5)
            self.cell(35.0, 4.0, owner, align="R")
            
            # 右侧卡片背景框（淡雅灰蓝色）
            self.set_fill_color(248, 250, 252)
            self.set_draw_color(226, 232, 240)
            self.set_line_width(0.15)
            self.rect(x_line + 6.0, y_curr, 100.0, 12.0, "DF")
            
            # 右侧卡片内容：具体动作与摘要
            self.set_font("cn", "B", 8.2)
            self.set_text_color(15, 23, 42)
            self.set_xy(x_line + 8.0, y_curr + 1.2)
            self.cell(96.0, 4.0, action)
            
            self.set_font("cn", "", 7.5)
            self.set_text_color(100, 116, 139)
            self.set_xy(x_line + 8.0, y_curr + 5.8)
            self.cell(96.0, 4.0, desc)
            
        self.set_xy(20.0, y_start + total_h)
        self.ln(2.0)


# ── 主编译流水线 ──────────────────────────────────────
def build_task_division_pdf():
    pdf = TaskDivisionPdf()
    pdf.set_title("RAG 检索增强生成系统 — 团队分工与职责说明")
    pdf.set_author("李伟 (组长)")
    
    # 🌟 PAGE 1: 封面/标题与核心贡献表格
    pdf.add_page()
    pdf.main_title("团队分工与职责说明 (Task Division)")
    
    # 核心正文段落
    intro_text = (
        "本项目由四人团队协作开发。在研发过程中，由组长李伟统一进行技术架构设计与任务统筹，各组员分工明确、"
        "紧密配合，实现全链路的快速交付。团队四位成员均深度参与并为本项目付出了核心心血，共同促成了百万级"
        "企业级高可靠 RAG 检索系统的成功落地。"
    )
    pdf.paragraph(intro_text)
    
    # 1. 团队角色与核心贡献标题
    pdf.h1("一、 团队角色与核心贡献")
    
    # 表格结构定义
    headers = ["成员", "职责分工", "核心工作职责与输出物"]
    col_widths = [26.0, 34.0, 110.0]
    
    rows = [
        [
            "李伟 (组长)\n[组长 / 架构师]",
            "项目统筹 &\nRAG 架构师",
            "1. 系统架构设计与卸载规划：设计了本地边缘端与云端算力卸载相结合的分布式 RAG 流水线架构，实现 100 万级规模文档的批量安全建库。\n"
            "2. 核心工程实现：重构并深度优化本地向量数据库管理模块 embed_store.py；编写 preprocess.py 中的自研四层语义分块算法与极短文档兜底聚拢策略。\n"
            "3. 技术攻坚：定位并攻克 Mock 绑定路径穿透引起的单测报错隐患，将 Pytest 测试套件全面升级并顺利通过 91 个全量测试用例；统筹项目最终交付与远程代码库同步。"
        ],
        [
            "张杰 (组员)\n[数据工程师]",
            "数据工程师",
            "1. 多源语料采集：编写 collect_corpus.py、collect_stackoverflow.py、collect_csdn.py 等脚本，实现 Wikipedia、Stack Overflow 和 CSDN 的 API 离线 Markdown 提取与本地化存储。\n"
            "2. 数据清洗与高并发：设计 clean_text() 流水线过滤 HTML 与控制符；设计 32 线程并发元数据 LLM 提取及 429 频率超限指数退避重试算法。\n"
            "3. 算力卸载部署：负责 AutoDL 远程云显卡 RTX 4090 环境搭建，编写并部署云端 FastAPI 向量计算服务器 embedding_server.py 与配置脚本 setup_autodl.sh。"
        ],
        [
            "王婷 (组员)\n[前端开发工程师]",
            "前端开发工程师",
            "1. Web UI/UX 现代设计：采用 Vanilla CSS + 现代视觉规范重新设计 Streamlit 前端（app/streamlit_app.py 与 app/style.css），实现可折叠毛玻璃卡片和精美的“玻璃盒后端技术剖析”调试分析看板。\n"
            "2. 交互逻辑开发：维护多轮对话历史、Top-K 数量及相似度阈值滑块，编写核心 “数据管理” 模块，支持用户拖拽上传自定义文本入库并进行异步清洗表征。\n"
            "3. 安全注入防御：在前台数据渲染环节强引入 Python 标准 html.escape() 进行全链路字符安全过滤与实体逃逸转义，彻底阻断了由于外部语料注入而导致的 XSS 跨站脚本安全隐患。"
        ],
        [
            "刘洋 (组员)\n[测试与文档工程师]",
            "测试与文档工程师",
            "1. 单元与集成测试：使用 pytest 编写覆盖全链路的单测用例（共 23 类 91 个），包含 YAML 嵌套解析、API 降级和 System 信号穿透等极端边缘用例的断言验证。\n"
            "2. 答辩演示与文档：负责答辩 PowerPoint 制作（BigData_RAG_答辩演示.pptx）、编写演示脚本与故障应对剧本（presentation_guide.md）以及技术总报告（report.md）的撰写与行数统计维护。\n"
            "3. 极速同步容灾：负责将 4.79 GB 物理 HNSW 索引打包压缩并通过 AliyunDrive 以 14MB/s 上行速度高速同步，制定一键幂等重建的防损毁数据容灾策略。"
        ]
    ]
    
    pdf.draw_task_table(headers, rows, col_widths)
    
    # 🌟 PAGE 2: 开发流水线与组长个人版块技术汇报
    pdf.add_page()
    pdf.h1("二、 协作开发流水线流程")
    
    col_desc_text = (
        "在组长李伟的统筹指挥下，四人团队实现了高效的多任务并行，项目总计历经 81 项细节调优与安全加固，"
        "并最终在 91 个单元与集成测试中实现了 100% 成功通过 (100% Passed)，系统质量与文档质量均达到优秀的工业级交付标准。"
    )
    pdf.paragraph(col_desc_text)
    
    # 绘制时间轴图谱
    pdf.draw_timeline()
    
    pdf.h1("三、 各成员负责版块技术汇报")
    
    # 组长技术汇报
    pdf.h2("组长：李伟 — 系统架构与向量检索核心版块汇报")
    pdf.paragraph("作为项目组长和 RAG 系统架构师，我全面负责了本项目的整体顶层设计、核心算法模块编写以及疑难技术攻坚，确保项目架构的绝对鲁棒性与开发周期推进：")
    pdf.bullet_list([
        "顶层系统架构设计与资源规划：设计了本地与云端算力卸载相结合的分布式 RAG 客服架构，确保数据在 Ingest -> Preprocess -> Embed -> ChromaDB -> Query Parser -> Hybrid Search -> QA 的全生命周期中拥有清晰的流向和严格的异常边界限制。面对 100 万级规模的数据处理，主导规划了基于 AutoDL 云端显卡（NVIDIA RTX 4090）的高效算力卸载路线，移除了本地机器算力天花板限制。",
        "核心模块重构与优化 (src/embed_store.py)：重构并优化了 vector_store 向量库管理核心类。将原始的简易新增改写为支持 upsert 的幂等设计，彻底解决了大规模数据多批次重复导入引起的 DuplicateIDError 冲突。设计了高维空间余弦相似度计算与元数据 SQL where 条件端联合过滤检索算法，过滤在向量引擎层进行，有效缩减内存负荷，引入 max_distance 阈值，剔除低相关噪音文本块。",
        "语义分块算法研发 (src/preprocess.py)：编写了高内聚的四级退避分块逻辑（段落 -> 句子 -> 贪心拼接 -> 滑窗切割）。优先保护段落整体，在段落过长时使用标点符号识别并切割，并在相邻块间留有 120 字符的交叠 (Overlap)，最大限度保持上下文的连贯性。针对字数过短的散落文本设计了安全聚拢拼合机制，防止了语义被物理字数粗暴切断引起的向量语义退化。",
        "系统级中断信号防护与代码加固：针对大模型 API 遭遇网络超时或 429 限流报错，在代码中进行了优雅的多层捕获防崩。加入符合 AGENTS.md 规范的 KeyboardInterrupt 与 SystemExit 系统信号二次抛出防护，杜绝了底层模块静默吞下系统中断信号的问题，保障了终端的高敏捷交互。"
    ])
    
    # 🌟 PAGE 3: 张杰、王婷、刘洋汇报与交付总结
    pdf.add_page()
    
    # 张杰技术汇报
    pdf.h2("数据工程师：张杰 — 多源语料采集与数据清洗工程版块汇报")
    pdf.paragraph("作为数据工程师，我主要负责了本项目知识语料的动态高阶采集，超大吞吐量下的并发清洗预处理引擎，以及云端算力卸载的实际落地部署：")
    pdf.bullet_list([
        "高阶多源爬虫与转换器设计：分别针对 Wikipedia、Stack Overflow 和 CSDN 博客编写了定制化的离线数据提取脚本。使用 requests 请求数据并采用 BeautifulSoup 提取核心文章 HTML DOM 节点，精准剔成了多余的侧边栏、推荐广告、脚本和页眉页脚。配合 html2text 引擎，将不同来源 of 的超文本自动转化为格式极为纯净的 Markdown 结构。",
        "高并发 LLM 元数据生成与自适应退避 (src/preprocess.py)：开发了基于 ThreadPoolExecutor 的 32 线程并发元数据生成器，使整套原始文档元数据提取速度缩短了 90% 以上。面对高并发下 API 极其高发的 HTTP 429 Rate Limit（限流），在代码内实现了一套带有随机抖动的指数退避自适应重试机制（退避阶梯：2s -> 4s -> 8s，最多重试 3 次），大幅强化了数据预处理流水线在弱网环境下的韧性。",
        "算力卸载与云服务器部署 (scripts/)：编写了一键配置脚本 scripts/setup_autodl.sh，在 AutoDL 云服务器上快速拉起 RTX 4090（24GB VRAM）的 Python 推理环境。部署了基于 FastAPI 构建的远程高性能嵌入服务 scripts/embedding_server.py，支持多进程异步推理，使用 batch_size=256 稳定消化百万级数据，实现吞吐量 185 句/秒，耗时 2.5 小时以极其低廉的租用成本（4.70元）完成了全量高维向量表征提取。"
    ])
    
    # 王婷技术汇报
    pdf.h2("前端开发工程师：王婷 — 前端现代美学交互与安全版块汇报")
    pdf.paragraph("作为前端开发工程师，我专注于为智能客服系统构建现代、友好且具备深度交互与调试分析能力的可视化 Web 前端界面，并构筑前台数据的防注入安全屏障：")
    pdf.bullet_list([
        "Vanilla CSS 现代美学视觉重塑 (app/style.css)：基于当下主流的 Glassmorphism（毛玻璃）与流畅的深色卡片布局规范设计了全套视觉层。重新编写了全局滚动条、可展开调节面板与输入文本框的拟态拟物过渡动画，让 Streamlit 这个原本默认布局刻板的框架呈现出极富质感的交互界面。",
        "多轮对话状态机与“玻璃盒”剖析看板开发：借助 Streamlit 的 session_state 构建了支持上下文追踪的多轮对话状态机，支持用户即席选择并调整 Top-K 检索数量和相似度过滤分值（余弦距离门槛）。在主界面下方设计了能够实时一键展开的“后端技术剖析面板”，清晰展示系统检索出的各参考文档的余弦得分、文档分类、年份，方便技术人员直观分析检索精度。",
        "安全注入防御与转义网关：在接收到检索答案并向浏览器前端渲染之前，在变量输出入口强引入了 Python 标准 html.escape() 进行字符安全过滤与字符实体逃逸转义，确保外源文本（例如带有漏洞注入指令的 Wikipedia 词条）无法在前台执行恶意 XSS 挂马，保障浏览器沙箱安全。"
    ])
    
    # 刘洋技术汇报
    pdf.h2("测试与文档工程师：刘洋 — Pytest 测试套件开发与技术文档保障版块汇报")
    pdf.paragraph("作为测试与文档工程师，我全力确保本项目所有模块的工程质量达到生产环境的验收指标，并完成了全套答辩与技术文字资产的整理归纳：")
    pdf.bullet_list([
        "基于 Mock 的 Pytest 全覆盖测试设计 (tests/)：构建了涵盖所有核心组件的自动化测试包，包含 23 个独立测试类，共 91 个详尽的单元测试与端到端集成测试用例，覆盖率为团队开发之最。全面采用了 unittest.mock.patch 装饰器对外部 OpenAI 接口和 Hugging Face Embedding 下载环境实施无物理依赖的完美模拟，使得开发环境和测试管道可在无网状态下瞬时运行全套测试。",
        "总技术报告及答辩 PowerPoint 制作：撰写了深入的技术报告 report/report.md，从算法的底层角度刨析防幻觉 Prompt（如在检索无匹配时严格返回“参考资料不足”并不自行发散）的几度迭代，并在报告中更新并对齐最新的数据口径。制作了 BigData_RAG_答辩演示.pptx，以优雅的图表与极具逻辑的技术架构拆解幻灯片。",
        "物理索引打包与数据容灾策略：制定了 HNSW 数据库备份容灾策略。由于百万级建库需要 2.5 小时，将生成的 4.79 GB 物理 HNSW 数据库使用 tar.gz 极速压缩打包，通过网盘极速同步（14MB/s）同步至本地，使得团队成员本地可以实现零成本、即刻恢复运行，消除了数据丢失与重构的高昂算力开销。"
    ])
    
    # 保存为 PDF
    pdf.output(str(OUTPUT_PDF))
    print(f"SUCCESSFULLY GENERATED TASK DIVISION PDF AT: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_task_division_pdf()
