# -*- coding: utf-8 -*-
"""
generate_defense_qa_pdf.py
==========================
将答辩与评委提问应对指南 (defense_qa_guide.md) 编译生成为极其专业、美观的 7 页高清 PDF 文档。
专为零基础小白组员定制，包含大白话比喻、生词本、文件导航图及卡片式答辩防守 Q&A。
"""

from __future__ import annotations

from pathlib import Path
import re

from fpdf import FPDF

# ── 路径配置 ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = Path("C:/Windows/Fonts")
OUTPUT_PDF = BASE_DIR / "report" / "defense_qa_guide.pdf"

# ── Emojis 清洗工具 ───────────────────────────────────
def clean_emojis(text: str) -> str:
    """
    清洗文本中的 Emojis 符号以防止中文字体缺少 Glyphs 警告。
    """
    emojis = [
        "👑", "🧑‍💻", "🎨", "🧪", "🎯", "📈", "🗣️", "加", "💡", "🛡️", "🌟", 
        "🔥", "🚀", "🛠️", "①", "②", "③", "④", "⑤", "⑥", "🔑", "📌"
    ]
    cleaned = text
    for emoji in emojis:
        cleaned = cleaned.replace(emoji, "")
    
    # 额外替换一些特殊数字序号
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
class DefenseQaPdf(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(20.0, 18.0, 20.0)
        self.set_auto_page_break(True, margin=18)
        
        # 加载仿宋 (simfang) 和黑体 (simhei) 字体
        self.add_font("cn", "", str(FONT_DIR / "simfang.ttf"))
        self.add_font("cn", "B", str(FONT_DIR / "simhei.ttf"))
        
        # 页面总可用宽度：170mm
        self.PW = 170.0

    def header(self):
        """专业页眉。"""
        if self.page_no() == 1:
            return
        self.set_font("cn", "", 7.5)
        self.set_text_color(120, 130, 140)
        self.cell(self.PW, 4, "RAG 检索增强生成系统 — 答辩与小白求生黄金指南 (Noob-Friendly Survival Manual)", align="L")
        self.set_xy(20.0, self.get_y() + 4.0)
        
        # 页眉分割线
        self.set_draw_color(220, 225, 230)
        self.set_line_width(0.2)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_y(self.get_y() + 4.5)

    def footer(self):
        """带页码的页脚。"""
        self.set_y(-14)
        
        # 页脚分割线
        self.set_draw_color(230, 235, 240)
        self.set_line_width(0.15)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        
        self.set_y(-11)
        self.set_font("cn", "", 7.5)
        self.set_text_color(150, 150, 150)
        self.cell(self.PW, 5, f"— {self.page_no()} —", align="C")

    # ── 标题与排版样式 ──
    def main_title(self, title: str):
        """绘制主标题。"""
        self.ln(2.0)
        self.set_font("cn", "B", 14.5)
        self.set_text_color(26, 54, 93)  # 经典深蓝
        self.cell(self.PW, 8, clean_emojis(title), align="C")
        self.ln(9.0)
        
        # 双重底线
        self.set_draw_color(26, 54, 93)
        self.set_line_width(0.4)
        self.line(20.0, self.get_y(), 190.0, self.get_y())
        self.set_line_width(0.12)
        self.line(20.0, self.get_y() + 0.8, 190.0, self.get_y() + 0.8)
        self.ln(4.0)

    def h1(self, text: str):
        """一级标题。"""
        if self.get_y() > 255:
            self.add_page()
        self.ln(3.5)
        self.set_font("cn", "B", 10.5)
        self.set_text_color(26, 54, 93)
        self.cell(self.PW, 5, clean_emojis(text), align="L")
        self.ln(5.5)
        
        # 下划短线
        y = self.get_y() - 0.5
        self.set_draw_color(26, 54, 93)
        self.set_line_width(0.5)
        self.line(20.0, y, 45.0, y)
        self.set_draw_color(225, 229, 233)
        self.set_line_width(0.15)
        self.line(45.0, y, 190.0, y)
        self.ln(2.5)

    def h2(self, text: str):
        """二级标题。"""
        if self.get_y() > 260:
            self.add_page()
        self.ln(2.5)
        self.set_font("cn", "B", 9.2)
        self.set_text_color(45, 55, 72)
        
        # 绘制背景装饰条
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(243, 244, 246)
        self.rect(20.0, y, self.PW, 5.0, "F")
        self.set_fill_color(26, 54, 93)
        self.rect(20.0, y, 1.6, 5.0, "F")
        
        self.set_xy(23.0, y + 0.5)
        self.cell(self.PW - 3.0, 4.0, clean_emojis(text), border=0)
        self.set_xy(20.0, y + 5.0)
        self.ln(1.5)

    def paragraph(self, text: str, bold_prefix: str = ""):
        """正文段落，可选择带粗体前缀。"""
        if self.get_y() > 268:
            self.add_page()
        self.set_font("cn", "", 8.5)
        self.set_text_color(45, 55, 72)
        
        full_text = text
        if bold_prefix:
            self.set_font("cn", "B", 8.5)
            self.set_text_color(26, 54, 93)
            self.write(4.0, clean_emojis(bold_prefix))
            self.set_font("cn", "", 8.5)
            self.set_text_color(45, 55, 72)
            
        lines = split_text_to_lines(self, full_text, self.PW)
        for idx, line in enumerate(lines):
            line_w = self.get_string_width(line)
            is_last = (idx == len(lines) - 1)
            if not is_last and line_w > 0 and len(line) > 1 and line_w < self.PW:
                extra_space = self.PW - line_w
                extra_char_spacing = extra_space / (len(line) - 1)
                if extra_char_spacing < 1.2:
                    self.set_char_spacing(extra_char_spacing)
                    self.cell(self.PW, 4.0, line)
                    self.set_char_spacing(0.0)
                    self.ln(4.0)
                    continue
            self.cell(self.PW, 4.0, line)
            self.ln(4.0)
        self.ln(0.8)

    def bullet_list(self, items: list[str]):
        """无序列表。"""
        self.set_font("cn", "", 8.5)
        self.set_text_color(45, 55, 72)
        for item in items:
            if self.get_y() > 268:
                self.add_page()
            
            clean_item = clean_emojis(item)
            
            # 绘制小圆点
            self.set_fill_color(26, 54, 93)
            y_curr = self.get_y()
            self.ellipse(23.0, y_curr + 1.4, 1.0, 1.0, "F")
            
            w_text = self.PW - 5.5
            lines = split_text_to_lines(self, clean_item, w_text)
            for idx, line in enumerate(lines):
                self.set_x(25.0)
                line_w = self.get_string_width(line)
                is_last = (idx == len(lines) - 1)
                if not is_last and line_w > 0 and len(line) > 1 and line_w < w_text:
                    extra_space = w_text - line_w
                    extra_char_spacing = extra_space / (len(line) - 1)
                    if extra_char_spacing < 1.2:
                        self.set_char_spacing(extra_char_spacing)
                        self.cell(w_text, 4.0, line)
                        self.set_char_spacing(0.0)
                        self.ln(4.0)
                        continue
                self.cell(w_text, 4.0, line)
                self.ln(4.0)
            self.ln(0.6)

    # ── 高清 Q&A 问答盒子绘制 ──
    def draw_qa_box(self, question: str, core_strategy: str, answer_template: str):
        """
        绘制极其美观、带左侧高亮边框和淡雅背景的 Q&A 问答盒子，保证排版无懈可击。
        """
        self.ln(1.5)
        w_box = self.PW
        
        # 1. 预估整体的高度以判断是否需要跨页
        q_lines = split_text_to_lines(self, clean_emojis(question), w_box - 8.0)
        c_lines = split_text_to_lines(self, clean_emojis(core_strategy), w_box - 24.0)
        a_lines = split_text_to_lines(self, clean_emojis(answer_template), w_box - 24.0)
        
        # 预估高度计算
        h_est = (len(q_lines) * 3.8) + (len(c_lines) * 3.6) + (len(a_lines) * 3.8) + 11.0
        
        # 防溢出跨页保护
        if self.get_y() + h_est > 268:
            self.add_page()
            
        y_curr = self.get_y()
        x_curr = self.get_x()
        
        # 2. 绘制高质感灰蓝色卡片背景
        self.set_fill_color(249, 250, 251) # 护眼亮灰白
        self.set_draw_color(229, 231, 235) # 极简淡灰边框
        self.set_line_width(0.18)
        self.rect(20.0, y_curr, w_box, h_est, "DF")
        
        # 3. 绘制左侧深蓝色高亮装饰实心线（极显高级感）
        self.set_fill_color(26, 54, 93)
        self.rect(20.0, y_curr, 1.5, h_est, "F")
        
        # 4. 绘制 Question (粗黑体，深蓝色)
        self.set_font("cn", "B", 8.2)
        self.set_text_color(26, 54, 93)
        
        y_w = y_curr + 2.2
        for line in q_lines:
            self.set_xy(23.0, y_w)
            self.cell(w_box - 5.0, 3.8, line, border=0)
            y_w += 3.8
            
        # 绘制一条卡片内虚割线
        self.set_draw_color(229, 231, 235)
        self.set_line_width(0.08)
        self.line(23.0, y_w + 0.8, 187.0, y_w + 0.8)
        y_w += 2.0
        
        # 5. 绘制 "应对核心" (SimHei 粗体，橙红色)
        self.set_font("cn", "B", 7.8)
        self.set_text_color(194, 65, 12) # 橙红色
        self.set_xy(23.0, y_w)
        self.cell(20.0, 3.6, "应对核心：", border=0)
        
        self.set_font("cn", "B", 7.8)
        self.set_text_color(74, 85, 104) # 深冷灰
        for line_idx, line in enumerate(c_lines):
            self.set_xy(38.0, y_w + line_idx * 3.6)
            self.cell(w_box - 24.0, 3.6, line, border=0)
        y_w += len(c_lines) * 3.6 + 1.8
        
        # 6. 绘制 "回答模版" (SimHei 粗体 + SimFang 仿宋体)
        self.set_font("cn", "B", 7.8)
        self.set_text_color(26, 54, 93)
        self.set_xy(23.0, y_w)
        self.cell(20.0, 3.8, "回答模版：", border=0)
        
        self.set_font("cn", "", 7.8)
        self.set_text_color(45, 55, 72)
        for line_idx, line in enumerate(a_lines):
            self.set_xy(38.0, y_w + line_idx * 3.8)
            # 两端对齐处理
            line_w = self.get_string_width(line)
            w_item = w_box - 23.0
            is_last = (line_idx == len(a_lines) - 1)
            if not is_last and line_w > 0 and len(line) > 1 and line_w < w_item:
                extra_space = w_item - line_w
                extra_char_spacing = extra_space / (len(line) - 1)
                if extra_char_spacing < 1.0:
                    self.set_char_spacing(extra_char_spacing)
                    self.cell(w_item, 3.8, line)
                    self.set_char_spacing(0.0)
                    continue
            self.cell(w_item, 3.8, line)
        
        # 重置坐标到盒子底部外侧
        self.set_xy(20.0, y_curr + h_est)
        self.ln(2.5)


# ── 主编译流水线 ──────────────────────────────────────
def build_defense_qa_pdf():
    pdf = DefenseQaPdf()
    pdf.set_title("RAG 检索增强生成系统 — 答辩与小白求生黄金指南")
    pdf.set_author("李伟 (组长)")
    
    # ==========================================
    # 🌟 PAGE 1: 标题与 RAG 极简入门
    # ==========================================
    pdf.add_page()
    pdf.main_title("答辩与小白求生黄金指南 (Defense Survival Guide)")
    
    intro_p1 = (
        "本指南专门针对“另外三名组员（张杰、王婷、刘洋）未实际参与项目开发、属于第一次接触本项目”的特殊背景"
        "进行了大篇幅扩增。指南采用大白话生活化比喻拆解底层原理，为每位组员建立“文件 -> 板块”的保姆级代码导航"
        "与专业生词本，并给出了万一在答辩现场被评委问懵时的标准自救求生三部曲，以保障汇报现场的高水平说服力。"
    )
    pdf.paragraph(intro_p1)
    
    pdf.h1("一、 零基础小白极速通关与全局核心心法")
    
    pdf.h2("1. 用大白话理解我们的项目：什么是 RAG？")
    p_rag = (
        "传统直接问大模型问题就像是闭卷考试。如果大模型不知道正确答案，或者它的知识库过期了，它就会开始胡说八道"
        "（产生幻觉），编造虚假信息。而我们做的 RAG（检索增强生成）相当于给大模型发了一本准确的课程参考书，"
        "让它进行开卷考试。当用户输入一个问题时，系统先去参考书里翻阅查找最相关的几页内容（向量检索），然后把"
        "这几页内容交在大模型手里，跟它说：‘请你只根据我给你的这几段话，写出一句通俗的回答，并且必须写明你是"
        "在哪一页看到的（引用标注）。’这彻底消除了大模型胡说八道的可能性，实现了 0 幻觉率与 100% 答案可追溯。"
    )
    pdf.paragraph(p_rag)
    
    pdf.h2("2. 本地大数据的“六大核心管道”数据流转生命周期")
    p_pipe = (
        "请三位组员务必记住下面这条数据流转管道主线：每一个用户问题，在系统后台都经历这六个管道的生命周期流转："
    )
    pdf.paragraph(p_pipe)
    
    pdf.bullet_list([
        "Ingest 数据读取：把原始 JSONL、Markdown、TXT 格式的文件读入内存，提取作者、年份、分类等元数据。",
        "Preprocess 清洗分块：用 BeautifulSoup 和 html2text 去掉网页里的广告和垃圾排版，过滤无用噪声；并采用四级退避语义分块算法，按句号换行符把长文本切成一段段大小合适的 Chunk，不切断中长句。",
        "Embed 向量生成：在 AutoDL 租用的 RTX 4090 显卡服务器上部署向量模型 (bge-large-zh)，本地把文本分块通过 FastAPI 并发发送到云端，将分块的“字面意思”翻译成 1024 维的特征向量数字（门牌号）。",
        "Vector DB 向量入库：把特征向量数字和对应的原始文本一起存入 ChromaDB 向量数据库，建立 HNSW 检索索引，类似于字典的拼音首字母索引，实现百万级大数据下的毫秒级检索查找。"
    ])

    # ==========================================
    # 🌟 PAGE 2: 数据流转管道 5-6 与 小白自救三部曲
    # ==========================================
    pdf.add_page()
    pdf.h2("2. 本地大数据“六大核心管道”数据流转生命周期 (续)")
    pdf.bullet_list([
        "Search 检索匹配：把用户提的问题也用云端 GPU 翻译成数字，去向量数据库里算一下，跟哪个分块的数字“距离最近”（余弦相似度最高），挑选出排名前 3 的文本块召回。",
        "QA Synthesis 答案合成：把召回的前 3 名文本块拼接成上下文喂给大模型，让大模型只根据这些事实写出带引用来源的最终回答，并在 Streamlit 前台气泡展示流式打字效果。"
    ])
    
    pdf.h2("3. 小白组员现场“三步求生自救话术”（万用兜底）")
    p_self_save = (
        "如果在答辩现场，评委老师单独点你的名，问了你一个你根本听不懂、或者极其刁钻的细节问题，千万不要慌张，"
        "更不要直接沉默！请使用以下标准自救三部曲套路进行完美过渡："
    )
    pdf.paragraph(p_self_save)
    
    pdf.bullet_list([
        "第一步：稳住气场，争取思考时间。可以微笑并从容地回答：‘老师，您问的这个细节问题非常专业且直击痛点。我们在系统设计和集成测试期间，也专门针对这部分进行过深入的工程权衡论证……’",
        "第二步：大方阐述你所属版块的核心逻辑。用大白话和背熟的话术套进去：‘我负责的这个版块，最核心的工程考量是保障系统在并发/网络/输入时的绝对鲁棒性与低成本，我们的核心做法是……’",
        "第三步：巧妙转接回组长。‘关于我刚才提到的这个做法，如何与我们系统底层的分布式架构以及 ChromaDB 向量数据库事务一致性进行更深度的全局耦合联动，请我们的组长李伟进行全局的技术补充。’"
    ])

    # ==========================================
    # 🌟 PAGE 3: 数据工程师张杰保姆指南
    # ==========================================
    pdf.add_page()
    pdf.h1("二、 成员各自版块零基础保姆级深潜 (Onboarding Cheat Sheets)")
    
    pdf.h2("数据工程师：张杰 — 语料采集与数据清洗工程版块")
    
    pdf.paragraph("1. 极速代码文件导航：如果老师让你现场打开你写的代码，请毫不犹豫地指出这几个文件：")
    pdf.bullet_list([
        "src/ingest.py：数据读取层。里面包含 load_text_files 和 load_jsonl_file 函数，负责把维基词条和 JSONL 读入内存，提取 Front-Matter 内的作者、年份等 YAML 元数据。",
        "src/preprocess.py：数据清洗与分块层。里面包含 clean_text（清洗 HTML 标签与空白符）和 chunk_text（按段落句号进行四级语义感知切片分块）。",
        "scripts/embedding_server.py 和 setup_autodl.sh：云端 GPU 特征服务与部署脚本。基于 FastAPI 框架，在租用的远程 RTX 4090 显卡上加载模型，暴露 /v1/embeddings 接口进行高吞吐向量推理。"
    ])
    
    pdf.paragraph("2. 必须记住的大白话专业名词生词本：")
    pdf.bullet_list([
        "html2text：网页上有大量侧边栏、广告牛皮癣。html2text 能过滤掉 90% 以上的非语义噪声，只留下纯净 Markdown，大幅提升检索的信噪比。",
        "FastAPI：用于编写 HTTP 接口的 Python 框架。我用它在云端 4090 上把 Embedding 模型包装成网页服务，本地程序向其 POST 请求拿特征向量。",
        "429 Rate Limit (并发限流)：频繁发网络请求时，服务器会拦截并报错。我实现了一套带有随机抖动的自适应指数退避重试算法（2s->4s->8s），保证线程不崩溃死锁。",
        "RTX 4090 (算力卸载)：本地电脑生成向量需耗时几天。我们花每小时 1.88 元租用云端 GPU，2.5 小时内以 4.70 元的超低成本搞定了全部特征提取。"
    ])
    
    pdf.paragraph("3. 张杰版块高频提问答辩防守卡片盒：")
    
    pdf.draw_qa_box(
        "Q1：语料采集直接抓取 HTML 为什么不行？html2text 的作用是什么？",
        "HTML 中的广告、侧边栏是严重噪音，转换为纯净 Markdown 能极大提升向量检索的信噪比。",
        "互联网多源网页包含大量的页眉页脚、广告推荐和脚本噪音。如果将原始 HTML 向量化，这些噪音将严重污染特征向量空间，降低召回率。我编写的采集引擎采用 BeautifulSoup 精准锁定核心内容 DOM 节点，并利用 html2text 转换为极为纯净的 Markdown 语法结构。这不仅消除了 90% 以上的无用噪音，还保留了标题层级和代码块边界，为后续的“语义感知分块”提供了高质量的数据基底。"
    )

    # ==========================================
    # 🌟 PAGE 4: 张杰 Q2-Q3 & 前端开发王婷保姆指南
    # ==========================================
    pdf.add_page()
    pdf.draw_qa_box(
        "Q2：你们 32 线程并发提取元数据时，遭遇公有云高频 API 限流（429 报错）怎么应对的？",
        "指数退避自适应重试机制加抖动因子，保证程序不直接挂掉崩溃。",
        "在高并发下大量文档同时发出元数据生成请求，极易触发 API 提供商的 HTTP 429 Rate Limit（限流防护）。我没有简单捕获报错导致任务中断，而是在代码内实现了一套带有随机抖动的自适应指数退避重试算法。当收到 429 信号时，线程会自动暂停并按 2s -> 4s -> 8s 的指数阶梯递增重试，最大重试 3 次。该策略大幅强化了预处理流水线在弱网与限流极端环境下的稳定运行能力，最终以 0.88 元的极低成本顺利完成了元数据批量提取。"
    )
    
    pdf.draw_qa_box(
        "Q3：AutoDL 远程显卡算力卸载是怎么配合本地流水线协同工作的？",
        "本地 ETL 触发 -> 远程 FastAPI 接口并发推理 -> 本地 ChromaDB 写入，实现云地协同。",
        "百万级数据的向量特征生成在普通笔记本电脑上需要消耗数十小时。我们设计了“本地触发，云端卸载”的分布式计算方案。我编写了 scripts/setup_autodl.sh 脚本一键初始化云服务器，拉起由 FastAPI 驱动的高性能向量提取服务 scripts/embedding_server.py。本地 ETL 流水线清洗切块后，以 batch_size=256 批量发送 HTTP POST 请求，利用云端 RTX 4090 GPU 进行高并发推理，最终在 2.5 小时内以 4.70 元的租用成本，完成了全量特征计算，展现了极佳的云端协同工程表现。"
    )
    
    pdf.h2("前端开发工程师：王婷 — 前端现代美学交互与安全版块")
    
    pdf.paragraph("1. 极速代码文件导航：如果老师让你现场运行前端，请大方地展示这个文件：")
    pdf.bullet_list([
        "app/streamlit_app.py：我们系统的唯一前端交互入口。里面集成了会话聊天气泡逻辑、SessionState 记忆保存、HTML 安全逃逸过滤、以及在侧边栏开关的‘开发者调试面板’。"
    ])
    
    pdf.paragraph("2. 必须记住的大白话专业名词生词本：")
    pdf.bullet_list([
        "Streamlit：用于快速搭建美观 Web 页面的 Python 前端框架。我们只需调用纯 Python API（如 st.chat_input）即可生成高逼格拟态交互界面。",
        "Session State (会话状态机)：网页每点击或输入一次，后台程序都会从头重跑一遍。我用 session_state 状态机维护了多轮对话记录，防止页面刷新时聊天历史丢失。",
        "XSS (跨站脚本攻击)：知识库中如果含有恶意 HTML 标签或 JS 脚本，直接渲染会导致浏览器被黑客控制。我用 html.escape 对全部前台变量进行了安全实体转义拦截。",
        "流式输出 (Streaming)：大模型生成一句话需要几秒，如果等写完再一次性输出会让用户误以为死机。我用 Stream 接口像打字机一样实时蹦字，消除了用户的等待感。"
    ])

    # ==========================================
    # 🌟 PAGE 5: 王婷 Q1-Q2 & 测试开发刘洋保姆指南
    # ==========================================
    pdf.add_page()
    pdf.paragraph("3. 王婷版块高频提问答辩防守卡片盒：")
    
    pdf.draw_qa_box(
        "Q1：大语言模型答复往往有十几秒的延迟，前端在 UI/UX 上做了哪些优化来提升用户体验？",
        "流式打字机字元输出、SessionState 多轮状态机维护、以及透明化开发者玻璃盒侧边栏面板。",
        "为了避免用户在长达数秒的等待中产生系统崩溃的误判，我在前端交互设计上做出了三点优化：(1) 在发起查询后立即拉起拟态的 Loading 动画，并在技术细节展示栏透明化呈现当前的意图解析中间状态（如提取出的 filters 对象）；(2) 借用 session_state 建立平滑滚动聊天气泡，保持上下文关联；(3) 设计了“开发者调试看板”，用户一键展开即可直观查看后台检索召回文本的余弦距离评分和原始文件名，将黑盒逻辑转化为透明的“玻璃盒”，极大提升了系统的可解释性与人机交互信任度。"
    )
    
    pdf.draw_qa_box(
        "Q2：知识库中如果被恶意注入指令，大模型的回答会受影响吗？前端做了哪些安全拦截？",
        "XSS 字符安全逃逸与 html.escape 转义隔离，加后端 Prompt XML 标签沙箱约束。",
        "评委老师提到的指令注入与 XSS 攻击是 RAG 系统极易被忽视的安全漏洞。若外部语料中包含恶意的浏览器脚本或特殊转义指令，直接在前台渲染可能会引发 XSS 挂马劫持。为了保障系统沙箱安全，我在 Streamlit 变量输出网关上强引入了 Python 标准 html.escape() 进行 HTML 字符安全过滤，将恶意字符实体进行逃逸转义（如 < 转为 &lt;）。同时，组长李伟在 System Prompt 中加入了强 Facts 限制，防止了指令注入穿透 LLM 的防线，构筑了前后端一体的安全过滤机制。"
    )
    
    pdf.h2("测试与保障工程师：刘洋 — 测试套件开发与技术文档保障版块")
    
    pdf.paragraph("1. 极速代码文件导航：如果老师让你现场跑测试，请大方地展示这个文件夹：")
    pdf.bullet_list([
        "tests/ 文件夹：里面包含 test_ingest.py、test_preprocess.py、test_embed_store.py、test_qa.py 等 6 个专业自动化测试用例，涵盖全套 82 个单测及集成测试用例。",
        "运行命令：在终端运行 python -m pytest tests/ -v，即可瞬间看到 82 个用例全部 PASS 的高水平表现。"
    ])
    
    pdf.paragraph("2. 必须记住的大白话专业名词生词本：")
    pdf.bullet_list([
        "Pytest：主流的 Python 自动化测试框架。我编写的 82 个用例可以在 3 秒内自动校验全部模块输入输出，极大提升了项目的软件工程规范度。",
        "Mock (虚拟模拟桩)：离线测试大模型需消耗昂贵的 API 费用。我全面使用 unittest.mock.patch 对 OpenAI 客户端和 ChromaDB 进行了虚拟化高保真模拟，实现无网、零成本测试运行。",
        "物理快照备份：ChromaDB 底层是基于 SQLite 和 Parquet 物理文件的。我主导设计了自动压缩备份 vector_store 文件夹的方案，免去灾难发生时重复 2.5 小时建库的困局。"
    ])

    # ==========================================
    # 🌟 PAGE 6: 刘洋 Q1-Q2 & 组长李伟防守指南
    # ==========================================
    pdf.add_page()
    pdf.paragraph("3. 刘洋版块高频提问答辩防守卡片盒：")
    
    pdf.draw_qa_box(
        "Q1：你们的测试套件有 82 个用例，但在没有网络和 API 密钥的测试环境下，如何保证测试顺利运行？",
        "全量 Mock 装饰器解耦外部 API 和数据库，无物理网络依赖，实现秒级高保真测试。",
        "在持续集成（CI）或离线测试环境下，网络超时或缺少私钥是阻碍自动化测试的最大痛点。为了解决这一问题，我全面采用了 Python 标准库中的 unittest.mock.patch 装饰器对外部 OpenAI/DeepSeek 接口、ChromaDB 连接以及 Hugging Face Embedding 下载环境实施了高保真度无物理依赖的 Mock 模拟。我为测试设计了固定的黄金返回数据和预期的异常抛出路径，使得全套 82 个单测与集成测试用例可以在无网环境下一键在 3 秒内飞速跑完，并实现了 100% 成功通过，彻底证明了代码的高可靠性。"
    )
    
    pdf.draw_qa_box(
        "Q2：百万级建库需要 2.5 小时，如果本地数据库损坏了，你们怎么保证灾难恢复的？",
        "ChromaDB 物理文件打包压缩、极速网盘冗余同步与一键幂等重建脚本双重保障。",
        "针对百万级数据重新建库耗时较长的问题，我们制定了双重容灾与备份恢复策略：(1) 物理打包快照：由于 ChromaDB 采用 SQLite 和 Parquet 文件持久化，我主导设计了物理持久化文件夹 vector_store/ 的自动压缩容灾方案。打包为 5.8GB 的 .tar.gz 文件，通过网盘极速上行链路同步，实现云端和本地的秒级镜像同步；(2) 一键幂等重跑：如果数据库彻底损坏且快照丢失，我们在 src/main.py 中提供了一键重建命令，结合张杰开发的 32 线程预处理与 AutoDL 显卡并发卸载，可在 2.5 小时内幂等重构一个全新且数据一致的数据库。"
    )
    
    pdf.h1("三、 组长提问应对防守方案 — 李伟（系统架构、向量库与算法核心版块）")
    
    pdf.paragraph("1. 组长李伟核心职责导航：负责系统架构、算法核心与集成度量：")
    pdf.bullet_list([
        "src/main.py：系统主控制层与核心流水线。负责 CLI 命令行交互以及 build 流程编排。",
        "src/embed_store.py：ChromaDB 向量库封装。负责 HNSW 近邻索引、幂等 upsert 逻辑、以及复合 AND 过滤器显式转换。",
        "src/query_parser.py：意图解析。通过 LLM 提取 filters 元数据过滤器和 search_query 查询词。",
        "src/qa.py：回答合成。控制 System Prompt 事实规则约束以及来源 dedup 引用拼装。"
    ])
    
    pdf.draw_qa_box(
        "Q1：你们的系统在稳态下端到端响应需要 6s，这在工业界能接受吗？瓶颈在哪？如何优化？",
        "大模型网络延迟占 96%，本地检索仅占 4%。瓶颈在 LLM 端，可采用 Redis 缓存和本地化部署优化。",
        "本系统属于知识密集型多轮问答系统，包含查询意图解析和最终答案合成两重 LLM 推理。评委老师提到的 6s 耗时，在当前公有云 API 链路上是完全合理的。我们对“延迟预算”进行了秒级定位，发现本地 GPU 向量化（50ms）与 ChromaDB 近邻检索（200ms）总耗时不足 4%，瓶颈完全在大模型公有云 API 调用上。优化路径包括：(1) 对高频意图建立 Redis 语义缓存；(2) 在线服务侧换用更轻量的本地大模型（如 Qwen1.8B-Chat）；(3) 启用 Streamlit 前端流式字元输出，消除用户感官延迟。"
    )

    # ==========================================
    # 🌟 PAGE 7: 组长李伟 Q2-Q4
    # ==========================================
    pdf.add_page()
    pdf.draw_qa_box(
        "Q2：你们的数据分块为什么不用固定长度切割？700 字符加 120 重叠是怎么得来的？",
        "固定长度截断会强行割裂中文完整中长句与代码块。自研四层递进式语义分块提升召回率 28%。",
        "固定字数切割会粗暴撕裂代码块、段落与 FAQ 的完整性。我们在自建金标测试集上实测表明，固定长度（500 字符，100 重叠）的 Recall@3 仅为 62%，极易造成 FAQ 孤儿块丢失。为此，我们开发了四级退避语义分块算法（段落 -> 句子 -> 核心拼接 -> 滑窗切割）。自适应检测标点符号与物理段落边界，并辅以 120 字符重叠度。这完美保护了代码块物理边界，Recall@3 检索命中率大幅跃升至 87.8%，语义召回完整性表现极佳。"
    )
    
    pdf.draw_qa_box(
        "Q3：当数据规模达到 100 万行时，ChromaDB 写入报错 DuplicateIDError 怎么解决的？",
        "废弃 add 方法，在 embed_store.py 中实现了全局组合 Chunk ID 的幂等 Upsert 机制。",
        "在处理 100 万行级大规模数据建库时，由于文档源及切分块数量庞大，极易因文件名或分块索引重复触发 DuplicateIDError。我们在 embed_store.py 中重构了入库函数，废弃了简易的 add 方法，全面改写为 upsert 幂等写入，并引入了全局唯一的组合 Chunk ID 设计：Chunk ID = f'{filename}_{doc_idx}_{idx}'。这不仅消除了 ID 冲突，还实现了建库流程的幂等可重入性，允许我们在意外中断后一键断点续传。"
    )
    
    pdf.draw_qa_box(
        "Q4：为什么选择本地嵌入模型 Qwen3-Embedding-0.6B，而不直接用远程 OpenAI 的 ada-002 API？",
        "基于财务成本控制与敏感数据隐私安全双重工程权衡，本地模型具备 0 特征计算成本和 100% 数据流隐私防卫。",
        "主要基于财务成本控制与敏感数据隐私安全双重权衡：第一是财务成本：本地嵌入模型在 GPU CUDA 推理加速下运行，特征计算 API 调用开销为 0；若用 OpenAI API，在大数据密集并发建库与高频多轮提问场景下将产生高额 Token 账单。第二是隐私安全：企业内部公告、教师紧急通知及内部 FAQ 含有敏感信息，直接调用境外公有云 API 会引发安全泄密隐患。本地 Qwen 模型无任何数据泄露风险，完全满足企业级私有化数据隔离部署规范。"
    )
    
    # 保存为 PDF
    pdf.output(str(OUTPUT_PDF))
    print(f"SUCCESSFULLY GENERATED DEFENSE QA PDF AT: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_defense_qa_pdf()
