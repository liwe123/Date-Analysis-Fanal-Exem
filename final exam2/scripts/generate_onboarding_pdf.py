# -*- coding: utf-8 -*-
"""
generate_onboarding_pdf.py
==========================
将零基础小白组员项目架构、目录与现场操作保姆级指南 (member_onboarding_guide.md)
编译生成为排版极其专业、紧凑、质感高级的 A4 高清 PDF 指南报告。
经过深度优化，彻底修复了前缀与正文折行导致文字超出右边界的排版缺陷。
"""

from __future__ import annotations

from pathlib import Path
import re

from fpdf import FPDF

# ── 路径配置 ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = Path("C:/Windows/Fonts")
OUTPUT_PDF = BASE_DIR / "report" / "member_onboarding_guide.pdf"

# ── Emojis 清洗与符号映射工具 ─────────────────────────
def clean_emojis(text: str) -> str:
    """
    清洗文本中的 Emojis 符号以防止中文字体缺少 Glyphs 警告，映射特殊物理序号。
    """
    emojis = [
        "👑", "🧑‍💻", "🎨", "🧪", "🎯", "📈", "🗣️", "💡", "🛡️", "🌟", 
        "🔥", "🚀", "🛠️", "①", "②", "③", "④", "⑤", "⑥", "🔑", "📌",
        "📂", "⌨️", "🖥️", "💻", "📁", "🤖", "⚙️", "📝", "➕", "🐛", "🧪"
    ]
    cleaned = text
    for emoji in emojis:
        cleaned = cleaned.replace(emoji, "")
    
    cleaned = cleaned.replace("①", "1. ")
    cleaned = cleaned.replace("②", "2. ")
    cleaned = cleaned.replace("③", "3. ")
    cleaned = cleaned.replace("④", "4. ")
    cleaned = cleaned.replace("⑤", "5. ")
    cleaned = cleaned.replace("⑥", "6. ")
    
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
class OnboardingPdf(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(20.0, 14.0, 20.0) # 紧凑页边距
        self.set_auto_page_break(True, margin=14)
        
        # 加载仿宋 (simfang) 和黑体 (simhei) 字体
        self.add_font("cn", "", str(FONT_DIR / "simfang.ttf"))
        self.add_font("cn", "B", str(FONT_DIR / "simhei.ttf"))
        
        # 页面总可用宽度：170mm
        self.PW = 170.0

    def header(self):
        """专业页眉。"""
        if self.page_no() == 1:
            return
        self.set_font("cn", "", 7.2)
        self.set_text_color(120, 130, 140)
        self.cell(self.PW, 3.5, "RAG 检索增强生成系统 — 零基础小白组员架构与操作指南", align="L")
        self.set_xy(20.0, self.get_y() + 3.5)
        
        # 页眉分割线
        self.set_draw_color(225, 229, 233)
        self.set_line_width(0.15)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_y(self.get_y() + 3.5)

    def footer(self):
        """带页码的页脚。"""
        self.set_y(-12)
        
        # 页脚分割线
        self.set_draw_color(235, 238, 242)
        self.set_line_width(0.12)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        
        self.set_y(-9)
        self.set_font("cn", "", 7.2)
        self.set_text_color(160, 160, 160)
        self.cell(self.PW, 4, f"— {self.page_no()} —", align="C")

    # ── 标题与排版样式 ──
    def main_title(self, title: str):
        """绘制主标题。"""
        self.ln(1.5)
        self.set_font("cn", "B", 13.0)
        self.set_text_color(30, 41, 59)  # 深 Slate 灰
        self.cell(self.PW, 6.5, clean_emojis(title), align="C")
        self.ln(7.5)
        
        # 双重底线
        self.set_draw_color(30, 41, 59)
        self.set_line_width(0.35)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_line_width(0.1)
        self.line(20.0, self.get_y() + 0.6, 190.0, self.get_y() + 0.6)
        self.ln(3.0)

    def h1(self, text: str):
        """一级标题。"""
        if self.get_y() > 262:
            self.add_page()
        self.ln(2.0)
        self.set_font("cn", "B", 9.8)
        self.set_text_color(30, 41, 59)
        self.cell(self.PW, 4.5, clean_emojis(text), align="L")
        self.ln(4.5)
        
        # 下划短线
        y = self.get_y() - 0.5
        self.set_draw_color(30, 41, 59)
        self.set_line_width(0.4)
        self.line(20.0, y, 45.0, y)
        self.set_draw_color(228, 231, 235)
        self.set_line_width(0.12)
        self.line(45.0, y, 190.0, y)
        self.ln(1.8)

    def h2(self, text: str):
        """二级标题。"""
        if self.get_y() > 265:
            self.add_page()
        self.ln(1.8)
        self.set_font("cn", "B", 8.8)
        self.set_text_color(71, 85, 105)
        
        # 绘制背景装饰条
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(248, 250, 252)
        self.rect(20.0, y, self.PW, 4.2, "F")
        self.set_fill_color(71, 85, 105)
        self.rect(20.0, y, 1.2, 4.2, "F")
        
        self.set_xy(22.5, y + 0.3)
        self.cell(self.PW - 2.5, 3.6, clean_emojis(text), border=0)
        self.set_xy(20.0, y + 4.2)
        self.ln(1.0)

    def paragraph(self, text: str, bold_prefix: str = ""):
        """
        正文段落。
        彻底修复文字超出边界的排版问题：使用 FPDF 的 native write() 流式换行引擎，
        使其百分之百限制在 margin 设置的 170.0mm 打印范围内，绝不溢出。
        """
        if self.get_y() > 270:
            self.add_page()
        
        # 强制回到左边界 20.0mm，防止 x 坐标发生漂移
        self.set_x(20.0)
        
        # 1. 绘制粗体前缀
        if bold_prefix:
            self.set_font("cn", "B", 8.0)
            self.set_text_color(15, 23, 42)
            self.write(3.6, clean_emojis(bold_prefix))
            
        # 2. 绘制普通正文，使用 write 自动排版流式折行
        self.set_font("cn", "", 8.0)
        self.set_text_color(71, 85, 105)
        self.write(3.6, clean_emojis(text))
        
        # 3. 换行及段落后间距
        self.ln(4.2)
        self.ln(0.4)

    def bullet_list(self, items: list[str]):
        """无序列表。"""
        self.set_font("cn", "", 8.0)
        self.set_text_color(71, 85, 105)
        for item in items:
            if self.get_y() > 270:
                self.add_page()
            
            clean_item = clean_emojis(item)
            
            # 绘制小圆点
            self.set_fill_color(71, 85, 105)
            y_curr = self.get_y()
            self.ellipse(22.5, y_curr + 1.2, 0.8, 0.8, "F")
            
            w_text = self.PW - 4.5
            lines = split_text_to_lines(self, clean_item, w_text)
            for idx, line in enumerate(lines):
                self.set_x(24.5)
                line_w = self.get_string_width(line)
                is_last = (idx == len(lines) - 1)
                if not is_last and line_w > 0 and len(line) > 1 and line_w < w_text:
                    extra_space = w_text - line_w
                    extra_char_spacing = extra_space / (len(line) - 1)
                    if extra_char_spacing < 1.0:
                        self.set_char_spacing(extra_char_spacing)
                        self.cell(w_text, 3.6, line)
                        self.set_char_spacing(0.0)
                        self.ln(3.6)
                        continue
                self.cell(w_text, 3.6, line)
                self.ln(3.6)
            self.ln(0.3)

    # ── 高清 Terminal 终端命令盒子绘制 ──
    def draw_cmd_box(self, title: str, command: str, explanation: str):
        """
        绘制极其美观、紧凑、带左侧高亮边框和 Slate 深灰背景的终端操作命令卡片盒子。
        """
        self.ln(0.8)
        w_box = self.PW
        
        # 1. 预估整体的高度以判断是否需要跨页
        c_lines = split_text_to_lines(self, command, w_box - 24.0)
        e_lines = split_text_to_lines(self, clean_emojis(explanation), w_box - 24.0)
        
        # 预估高度计算 (标题一行 3.2mm，割线加间距 3.2mm)
        h_est = 3.0 + (len(c_lines) * 3.6) + (len(e_lines) * 3.4) + 7.5
        
        # 防溢出跨页保护
        if self.get_y() + h_est > 272:
            self.add_page()
            
        y_curr = self.get_y()
        
        # 2. 绘制卡片背景 (淡 Slate 灰)
        self.set_fill_color(248, 250, 252) 
        self.set_draw_color(226, 232, 240) 
        self.set_line_width(0.15)
        self.rect(20.0, y_curr, w_box, h_est, "DF")
        
        # 3. 绘制左侧 Slate 深蓝灰色亮条
        self.set_fill_color(30, 41, 59) # Slate 800
        self.rect(20.0, y_curr, 1.2, h_est, "F")
        
        # 4. 绘制 Title (黑体，深 Slate)
        self.set_font("cn", "B", 7.6)
        self.set_text_color(30, 41, 59)
        self.set_xy(22.5, y_curr + 1.5)
        self.cell(w_box - 5.0, 3.2, clean_emojis(title), border=0)
        
        # 绘制卡片内割线
        y_w = y_curr + 5.0
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.06)
        self.line(22.5, y_w, 187.5, y_w)
        y_w += 1.4
        
        # 5. 绘制 "运行命令"
        self.set_font("cn", "B", 7.5)
        self.set_text_color(194, 65, 12) # 橙红色
        self.set_xy(22.5, y_w)
        self.cell(20.0, 3.6, "运行命令：", border=0)
        
        # 代码背景灰框
        h_code = len(c_lines) * 3.6 + 1.2
        self.set_fill_color(241, 245, 249) # 代码背景 Slate 100
        self.set_draw_color(226, 232, 240)
        self.rect(37.5, y_w - 0.2, w_box - 21.5, h_code, "DF")
        
        self.set_font("cn", "B", 7.5)
        self.set_text_color(15, 23, 42) # Monospace 灰黑
        for idx, line in enumerate(c_lines):
            self.set_xy(39.0, y_w + idx * 3.6 + 0.2)
            self.cell(w_box - 24.0, 3.2, line, border=0)
        y_w += h_code + 1.6
        
        # 6. 绘制 "后台含义"
        self.set_font("cn", "B", 7.4)
        self.set_text_color(30, 41, 59)
        self.set_xy(22.5, y_w)
        self.cell(20.0, 3.4, "工程含义：", border=0)
        
        self.set_font("cn", "", 7.4)
        self.set_text_color(71, 85, 105)
        for idx, line in enumerate(e_lines):
            self.set_xy(37.5, y_w + idx * 3.4)
            # 两端对齐
            line_w = self.get_string_width(line)
            w_item = w_box - 22.0
            is_last = (idx == len(e_lines) - 1)
            if not is_last and line_w > 0 and len(line) > 1 and line_w < w_item:
                extra_space = w_item - line_w
                extra_char_spacing = extra_space / (len(line) - 1)
                if extra_char_spacing < 1.0:
                    self.set_char_spacing(extra_char_spacing)
                    self.cell(w_item, 3.4, line)
                    self.set_char_spacing(0.0)
                    continue
            self.cell(w_item, 3.4, line)
        
        # 重置坐标到卡片底部
        self.set_xy(20.0, y_curr + h_est)
        self.ln(1.2)


# ── 主编译流水线 ──────────────────────────────────────
def build_onboarding_pdf():
    pdf = OnboardingPdf()
    pdf.set_title("RAG 检索增强生成系统 — 零基础小白组员架构与操作指南")
    pdf.set_author("李伟 (组长)")
    
    # ==========================================
    # 🌟 PAGE 1: 标题与系统大白话解密
    # ==========================================
    pdf.add_page()
    pdf.main_title("零基础小白组员项目架构与现场操作指南")
    
    intro_text = (
        "本指南专为另外三名未实际参与代码编写的组员（张杰、王婷、刘洋）定制。指南将复杂的计算机专业黑话"
        "翻译为通俗的大白话，详细解释了项目的全局图纸、代码目录中每一个文件的作用、以及每一条控制台命令"
        "在系统底层的工程含义，并为每个人负责的板块提供了傻瓜式操作指南，确保答辩演示完美成功。"
    )
    pdf.paragraph(intro_text)
    
    pdf.h1("一、 大白话项目全局图纸（我们的系统是怎么跑起来的？）")
    p_arch = (
        "我们可以把这个 RAG（检索增强生成）系统看作是一家“智能开卷考试辅助咨询公司”。整个系统由两大部分协同运行："
    )
    pdf.paragraph(p_arch)
    
    pdf.paragraph(" 这是公司精美的“接待前台”。用户在网页的聊天输入框里用最口语化的白话文输入问题。前台不负责计算，只负责把问题接过来传给后台大脑，并负责把最后生成出的文字像打字机一样蹦出来，附带高亮展示引用文件来源。", "1. Streamlit 网页前台 (app/streamlit_app.py)：")
    
    pdf.paragraph(" 这是公司的“总机和参谋部”，内部分工高度严密。当用户问了一句‘2025年的紧急通知写了什么？’，大脑会安排以下工作：", "2. Python 后端业务线 (src/)：")
    
    pdf.bullet_list([
        "意图解析师 (src/query_parser.py)：先分析这句话，提取出核心搜索词为‘紧急通知’，并剥离出限制条件‘年份是 2025 年’。",
        "特征翻译官 (scripts/embedding_server.py)：用远程 GPU 显卡（本地显卡太弱，去云端租用 4090 显卡）把问题翻译成 1024 维的数字向量（门牌号）。",
        "图书管理员 (src/embed_store.py)：拿着门牌号去向量数据库里算距离，把 2025 年标签下相似度前 3 名的原文分块捞出来。",
        "答案合成师 (src/qa.py)：把这 3 段召回的真实原文拼在一起，附带‘不许胡说八道’的硬约束，喂给大模型 API 合成出带上标引用的最终答案。"
    ])
    
    # ==========================================
    # 🌟 PAGE 2: 代码目录生词本
    # ==========================================
    pdf.h1("二、 代码目录生词本（我们这几百行代码都放在哪了？）")
    p_dir_intro = (
        "答辩时如果老师让你在文件夹里指出代码文件，请对照下面这张大白话文件定位导航生词表："
    )
    pdf.paragraph(p_dir_intro)
    
    # 绘制高质感的目录列表
    pdf.paragraph(" 网页前台展示层。精美对话界面与侧边栏调试开关的代码所在处。", "app/streamlit_app.py [前端]：")
    pdf.paragraph(" 核心大脑。包含 ingest 读取、preprocess 清洗、embed_store 向量入库、query_parser 意图解析和 qa 答案合成，职责非常清晰。", "src/ [核心后端]：")
    pdf.paragraph(" 自动化测试实验室。内含 91 个离线 Mock 模拟测试用例，校验核心组件的鲁棒性。", "tests/ [测试代码]：")
    pdf.paragraph(" 辅助工具箱。包含 AutoDL 云端部署脚本 setup_autodl.sh 和 FastAPI 向量特征服务器脚本等。", "scripts/ [辅助脚本]：")
    pdf.paragraph(" 数据档案馆。存放维基百科语料采集 wiki.jsonl 以及清洗后的 markdown 原始文本数据。", "data/ [原始数据]：")
    pdf.paragraph(" 向量数据库物理存储目录。ChromaDB 数据存在这里，由元数据 SQLite 文件和向量 Parquet 组成。", "vector_store/ [向量数据库]：")
    pdf.paragraph(" 配置文件。存放 API Key 大门钥匙和配置，决定是 local 本地特征提取还是 remote 云端显卡卸载。", ".env [钥匙配置]：")
    pdf.paragraph(" 依赖包清单。记录了项目所需的所有第三方 Python 库，用于环境一键搭建安装。", "requirements.txt [包清单]：")

    # ==========================================
    # 🌟 PAGE 3: 终端命令与运行环境速成
    # ==========================================
    pdf.add_page()
    pdf.h1("三、 终端命令（小黑窗）与运行环境速成")
    
    pdf.h2("1. 怎么在项目目录里打开小黑窗？")
    p_win_cmd = (
        "在 Windows 资源管理器中双击打开项目根目录 final exam2 文件夹，按住键盘上的 Shift 键不要松开，"
        "在空白处点击鼠标右键，在弹出的右键菜单中选择「在此处打开 PowerShell 窗口」。"
    )
    pdf.paragraph(p_win_cmd)
    
    pdf.h2("2. 一键依赖安装命令与后台含义")
    p_dep_intro = (
        "把整个项目的 Python 运行依赖库自动下载并安装到电脑上，就像按清单买齐所有佐料："
    )
    pdf.paragraph(p_dep_intro)
    
    pdf.draw_cmd_box(
        "一键 Python 库依赖快速安装",
        "pip install -r requirements.txt",
        "根据清单自动从清华或阿里国内镜像源，一键下载并安装诸如 Streamlit、ChromaDB、FPDF2、BeautifulSoup 等核心开发包。"
    )
    
    pdf.h2("3. 配置文件钥匙卡的大白话含义")
    p_env_intro = (
        "记事本打开 .env 钥匙配置文件，配置使用本地 sentence-transformers 还是云端 RTX 4090 算力卸载服务："
    )
    pdf.paragraph(p_env_intro)
    
    pdf.draw_cmd_box(
        "系统开关配置文件 .env",
        "OPENAI_API_KEY=sk-xxxx...\nOPENAI_EMBEDDING_MODEL=remote\nOPENAI_EMBEDDING_BASE_URL=https://u12345-6008.seetacloud.com/v1",
        "配置云端大模型 API 钥匙卡，启用云端嵌入 remote 模式，并提供 AutoDL 云端 RTX 4090 的公网访问端口地址。"
    )

    # ==========================================
    # 🌟 PAGE 4: 组员专区大篇章
    # ==========================================
    pdf.add_page()
    pdf.h1("四、 组员专区 — 动作步骤、运行命令与其后台工程含义")
    
    pdf.h2("数据工程师：张杰 — 语料采集、清洗与云端 GPU 算力卸载操作")
    p_zj_intro = (
        "张杰同学负责多源高质量语料的采集和数据消噪清洗，并负责在 AutoDL 上部署加载 BAAI/bge 中文特征向量模型。"
    )
    pdf.paragraph(p_zj_intro)
    
    pdf.paragraph(" 运行以下抓取清洗指令，并在浏览器或文件夹展示抓取生成的 markdown 文件。", "任务一：启动多源语料抓取与 BeautifulSoup/html2text 清洗")
    pdf.draw_cmd_box(
        "启动爬虫引擎与数据清洗",
        "python src/collect_corpus.py",
        "程序利用 requests 和 BeautifulSoup 抓取维基百科术语，并用 html2text 去除网页中 90% 以上的非语义噪点（如导航、广告），自动生成极其纯净的 Markdown 文本块并归档在 data 目录下。"
    )
    
    pdf.paragraph(" 登录租用的 RTX 4090 显卡服务器，执行一键部署脚本拉起嵌入服务。", "任务二：一键部署并拉起云端 RTX 4090 GPU 嵌入服务")
    pdf.draw_cmd_box(
        "AutoDL 端一键拉起 GPU 特征服务",
        "bash setup_autodl.sh",
        "在云服务器上安装 PyTorch 深度学习框架和依赖包，从 Hugging Face 镜像站下载 1024 维的高端 bge-large-zh模型并加载到 GPU 显存中，暴露 FastAPI 服务接口静待本地数据发送。"
    )
    
    pdf.paragraph(" 运行本地建库命令，将百万级原始文本通过 POST 发送给云端 4090 并入库本地 ChromaDB。", "任务三：百万数据一键云端算力卸载向量建库")
    pdf.draw_cmd_box(
        "百万数据云端卸载建库",
        "python -m src.main build --metadata-strategy jsonl_only",
        "读取 data 目录下 1,000,176 行大文本，切成 1,215,021 个语义 Chunk。打包通过 HTTP POST 并发发送到 AutoDL RTX 4090 云端，利用 4090 显卡算力将文本转化为特征向量（门牌号），本地拿到后 upsert 写入 ChromaDB 库。仅耗时 2.5 小时，耗费 4.70 元租用费！"
    )
    
    pdf.h2("前端交互工程师：王婷 — Streamlit UI 交互与安全网关演示操作")
    p_wt_intro = (
        "王婷同学负责一键将网页前台运行起来，并在浏览器上现场演示智能意图分类、调试看板以及输入安全拦截防御。"
    )
    pdf.paragraph(p_wt_intro)
    
    pdf.paragraph(" 运行 Streamlit 启动命令，网页会自动在默认浏览器中弹出来。", "任务一：一键启动 Streamlit 智能问答对话前台网页")
    pdf.draw_cmd_box(
        "本地一键拉起 Web 网页前台",
        ".venv\\Scripts\\python -m streamlit run app/streamlit_app.py",
        "在本地启动一个轻量网页服务器，占用端口 8501 并自动弹出带有气泡聊天、打字机流式字元输出、以及玻璃盒调试看板的现代拟物化 Web 交互界面。"
    )


    # ==========================================
    # 🌟 PAGE 5: 王婷与刘洋版块全部任务
    # ==========================================
    pdf.paragraph(" 勾选侧边栏「调试模式」，提问并现场向老师展示解析出的结构化 JSON 过滤字典。", "任务二：现场演示「打开玻璃盒」智能意图元数据过滤看板")
    pdf.draw_cmd_box(
        "开启调试侧边抽屉面板",
        "勾选网页侧边栏 [调试模式] 按钮并提问",
        "后台 query_parser.py 瞬间提取用户问题的意图，拆解为 search_query 语义词与 filters 元数据过滤条件 JSON 并在侧边栏高亮呈现，证明系统并非黑盒，而是具有高度精准的结构化过滤性能。"
    )
    
    pdf.paragraph(" 前台输入恶意 HTML 脚本或 Prompt 注入指令，现场演示系统不受攻击、转义转义安全的特性。", "任务三：演示注入恶意代码前台 HTML 安全转义网关拦截")
    pdf.draw_cmd_box(
        "前台输入恶意代码并录入知识库",
        "在增量数据录入框输入: <script>alert('黑客攻击')</script>这是一篇注入文档",
        "文档以 upsert 动态录入并由 ChromaDB 召回。王婷在前端变量渲染输出前强引入 html.escape() 安全逃逸转义。前台网页将恶意标签转为无害实体字符直接输出显示，脚本绝对无法被浏览器执行，构筑了高安全沙箱网关。"
    )
    
    pdf.h2("测试与保障工程师：刘洋 — Pytest 自动化测试与物理容灾快照操作")
    p_ly_intro = (
        "刘洋同学负责在发版前一键执行 91 个自动化测试，并负责数据库的物理快照压缩备份与故障秒级原地复活。"
    )
    pdf.paragraph(p_ly_intro)
    
    pdf.paragraph(" 一键运行全量 Pytest 测试。在控制台展示 91 个测试用例 100% 通过的绿色画面。", "任务一：一键跑通 91 个断网高保真 Mock 自动化测试用例")
    pdf.draw_cmd_box(
        "一键启动 Pytest 自动化校验实验室",
        "python -m pytest tests/ -v",
        "运行 Pytest，利用 unittest.mock.patch 对所有 OpenAI 和 ChromaDB 接口进行高保真离线 Mock 模拟，拦截网络开销，在约 3 秒内 100% 成功通过全套 91 个测试用例，证明代码拥有极高健壮性。"
    )
    
    pdf.paragraph(" 运行打包压缩命令，把 5.8GB 的数据库物理实体瞬间归档备份，免去漫长的重复建库开销。", "任务二：将 ChromaDB 本地物理数据库打包为 5.8GB 容灾快照")
    pdf.draw_cmd_box(
        "对本地 vector_store 目录进行物理压缩归档",
        "tar -czvf vector_store_backup.tar.gz vector_store/",
        "ChromaDB 底层是 SQLite 关系元数据和 Parquet 向量磁盘文件。这行命令直接对该持久化文件夹进行物理压缩，生成 vector_store_backup.tar.gz 容灾备份快照，可进行云端极速备份。"
    )
    
    pdf.paragraph(" 现场在文件夹中删除 vector_store 目录模拟数据损坏，一键解包在 1秒内满状态原地复活系统。", "任务三：模拟数据库硬盘损坏故障并执行 1秒秒级灾备复原")
    pdf.draw_cmd_box(
        "解压缩容灾快照执行秒级原地复活",
        "tar -xzvf vector_store_backup.tar.gz",
        "一旦数据库断电死锁、数据损坏或误删除，直接在命令行一键解包，在 1 秒内从物理快照镜像中原地重构完整的 vector_store/ 目录，网页刷新即可继续完美对话，无需重跑 2.5 小时！"
    )
    
    # 保存为 PDF
    pdf.output(str(OUTPUT_PDF))
    print(f"SUCCESSFULLY GENERATED MEMBER ONBOARDING PDF AT: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_onboarding_pdf()
