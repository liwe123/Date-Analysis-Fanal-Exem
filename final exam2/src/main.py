"""
main.py
=======
CLI 入口：索引构建、问答、语料采集。
"""

from __future__ import annotations

# 1. 标准库
import argparse
import sys
from pathlib import Path

# ── 主处理流程 ───────────────────────────────────────────────────

def build_index(
    data_dir: str | Path | None = None,
    chunk_size: int = 700,
    overlap: int = 120,
    max_workers: int = 32,
) -> None:
    """
    读取原始数据目录中的文档，进行清洗、分块，并调用 LLM 提取元数据建立向量索引。

    参数：
      data_dir    : 原始文档所在目录，默认为 RAW_DIR
      chunk_size  : 语义分块的大小（字符数）
      overlap     : 相邻分块的重叠字符数
      max_workers : 元数据提取并发线程数
    """
    from src.embed_store import VectorStore
    from src.ingest import load_text_files
    from src.preprocess import process_documents
    from src.utils import get_logger

    logger = get_logger("main")
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    raw_dir = BASE_DIR / "data" / "raw"
    target_dir = Path(data_dir) if data_dir is not None else raw_dir
    logger.info("文档目录: %s", target_dir)
    documents = load_text_files(target_dir)
    logger.info("读取到 %d 个原始文档。", len(documents))

    if not documents:
        logger.warning("没有读取到任何 txt 或 md 文件。")
        return

    processed_docs = process_documents(
        documents, chunk_size=chunk_size, overlap=overlap, max_workers=max_workers,
    )
    logger.info("处理后得到 %d 个文本块。", len(processed_docs))

    if not processed_docs:
        logger.warning("文本处理后为空，无法建立索引。")
        return

    store = VectorStore()
    store.add_documents(processed_docs)
    logger.info("已建立索引，向量库当前总块数：%d。", store.count())


def collect_corpus() -> None:
    """从 Wikipedia 采集特定领域术语与背景知识语料。"""
    from src.collect_corpus import collect as collect_external_corpus
    from src.utils import get_logger

    logger = get_logger("main")
    success, failed = collect_external_corpus()
    logger.info("Wikipedia 采集完成：成功 %d，失败 %d", len(success), len(failed))


def collect_stackoverflow() -> None:
    """从 Stack Overflow 问答社区采集高质量技术问答语料。"""
    from src.collect_stackoverflow import collect as collect_so_corpus
    from src.utils import get_logger

    logger = get_logger("main")
    success, failed = collect_so_corpus()
    logger.info("Stack Overflow 采集完成：成功 %d，失败 %d", len(success), len(failed))


def collect_csdn() -> None:
    """从 CSDN 博客平台采集高质量技术文章语料。"""
    from src.collect_csdn import collect as collect_csdn_corpus
    from src.utils import get_logger

    logger = get_logger("main")
    success, failed = collect_csdn_corpus()
    logger.info("CSDN 采集完成：成功 %d，失败 %d", len(success), len(failed))


def collect_all() -> None:
    """全量采集所有渠道的数据语料（Wikipedia + Stack Overflow + CSDN）。"""
    from src.utils import get_logger

    logger = get_logger("main")
    logger.info("=== 开始全量采集 ===")
    collect_corpus()
    collect_stackoverflow()
    collect_csdn()
    logger.info("=== 全量采集完成 ===")


def ask_once(question: str, top_k: int = 3) -> None:
    """
    单次 RAG 问答：解析问题意图，进行向量及元数据过滤检索，并生成精确答案。

    参数：
      question : 用户的问答输入
      top_k    : 检索返回的文档分块数
    """
    from src.embed_store import VectorStore
    from src.qa import generate_answer
    from src.query_parser import parse_query
    from src.utils import get_logger

    logger = get_logger("main")
    store = VectorStore()

    logger.info("正在解析查询意图...")
    parsed = parse_query(question)
    search_query = parsed["search_query"]
    filters = parsed["filters"]

    if filters:
        logger.info("提取到元数据过滤条件: %s", filters)
    logger.info("提取核心语义词: \"%s\"", search_query)

    retrieved_docs = store.search(search_query, top_k=top_k, where=filters)
    if not retrieved_docs:
        logger.warning("没有检索到相关内容。")
        return

    answer = generate_answer(question, retrieved_docs)
    print("\n===== 回答 =====")
    print(answer)

    print("\n===== 检索到的来源 =====")
    for idx, item in enumerate(retrieved_docs, 1):
        score = f"{item['score']:.4f}" if item["score"] is not None else "N/A"
        print(f"{idx}. {item['source']} (distance={score})")
        print(item["text"][:200], "...\n")


def ask_loop(top_k: int = 3) -> None:
    """
    交互式循环问答模式，循环读取用户输入直至输入 'exit' 退出。

    参数：
      top_k : 检索返回的文档分块数
    """
    while True:
        question = input("\n请输入问题（输入 exit 退出）：").strip()
        if question.lower() == "exit":
            break
        if question:
            ask_once(question, top_k=top_k)


def create_parser() -> argparse.ArgumentParser:
    """
    创建并配置 CLI 命令行参数解析器。

    返回：
      配置好的 ArgumentParser 实例
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    raw_dir = BASE_DIR / "data" / "raw"

    parser = argparse.ArgumentParser(description="计划二 RAG 系统入口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="建立或更新向量索引")
    build_parser.add_argument("--data-dir", type=Path, default=raw_dir, help="原始数据目录")
    build_parser.add_argument("--chunk-size", type=int, default=700, help="分块大小（字符）")
    build_parser.add_argument("--overlap", type=int, default=120, help="分块重叠（字符）")
    build_parser.add_argument("--max-workers", type=int, default=32, help="LLM 元数据提取并发数")

    ask_parser = subparsers.add_parser("ask", help="问答模式")
    ask_parser.add_argument("--question", type=str, default="", help="单次问题；不填则进入交互模式")
    ask_parser.add_argument("--top-k", type=int, default=3, help="检索返回条数")

    subparsers.add_parser("collect", help="从 Wikipedia 采集术语与背景知识")
    subparsers.add_parser("collect-so", help="从 Stack Overflow 采集高质量问答")
    subparsers.add_parser("collect-csdn", help="从 CSDN 博客采集技术文章")
    subparsers.add_parser("collect-all", help="全量采集（Wikipedia + Stack Overflow + CSDN）")
    return parser


def main() -> None:
    """CLI 入口主函数，解析命令行参数并调度执行对应的指令。"""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "build":
        build_index(args.data_dir, args.chunk_size, args.overlap, args.max_workers)
    elif args.command == "ask":
        if args.question:
            ask_once(args.question, top_k=args.top_k)
        else:
            ask_loop(top_k=args.top_k)
    elif args.command == "collect":
        collect_corpus()
    elif args.command == "collect-so":
        collect_stackoverflow()
    elif args.command == "collect-csdn":
        collect_csdn()
    elif args.command == "collect-all":
        collect_all()


if __name__ == "__main__":
    # 动态插入项目根路径
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.utils import init_env
    init_env()
    main()
