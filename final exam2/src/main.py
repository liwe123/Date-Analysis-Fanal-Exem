import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.collect_corpus import collect as collect_external_corpus
from src.embed_store import VectorStore
from src.ingest import load_text_files
from src.preprocess import process_documents
from src.qa import generate_answer
from src.query_parser import parse_query
from src.utils import get_logger, init_env

init_env()
logger = get_logger("main")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


def build_index(data_dir: Path, chunk_size: int, overlap: int):
    logger.info("文档目录: %s", data_dir)
    documents = load_text_files(data_dir)
    logger.info("读取到 %d 个原始文档。", len(documents))

    if not documents:
        logger.warning("没有读取到任何 txt 或 md 文件。")
        return

    processed_docs = process_documents(documents, chunk_size=chunk_size, overlap=overlap)
    logger.info("处理后得到 %d 个文本块。", len(processed_docs))

    if not processed_docs:
        logger.warning("文本处理后为空，无法建立索引。")
        return

    store = VectorStore()
    store.add_documents(processed_docs)
    logger.info("已建立索引，向量库当前总块数：%d。", store.count())


def collect_corpus():
    success, failed = collect_external_corpus()
    logger.info("自动采集完成：成功 %d，失败 %d", len(success), len(failed))


def ask_once(question: str, top_k: int):
    store = VectorStore()

    logger.info("正在解析查询意图...")
    parsed = parse_query(question)
    search_query = parsed["search_query"]
    filters = parsed["filters"]

    if filters:
        logger.info("提取到元数据过滤条件: %s", filters)
    logger.info("提取核心语义词: '%s'", search_query)

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


def ask_loop(top_k: int):
    while True:
        question = input("\n请输入问题（输入 exit 退出）：").strip()
        if question.lower() == "exit":
            break
        if question:
            ask_once(question, top_k=top_k)


def create_parser():
    parser = argparse.ArgumentParser(description="计划二 RAG 系统入口")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="建立或更新向量索引")
    build_parser.add_argument("--data-dir", type=Path, default=RAW_DIR, help="原始数据目录")
    build_parser.add_argument("--chunk-size", type=int, default=700, help="分块大小（字符）")
    build_parser.add_argument("--overlap", type=int, default=120, help="分块重叠（字符）")

    ask_parser = subparsers.add_parser("ask", help="问答模式")
    ask_parser.add_argument("--question", type=str, default="", help="单次问题；不填则进入交互模式")
    ask_parser.add_argument("--top-k", type=int, default=3, help="检索返回条数")

    subparsers.add_parser("collect", help="自动从公开资料源采集术语与背景知识")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "build":
        build_index(args.data_dir, args.chunk_size, args.overlap)
    elif args.command == "ask":
        if args.question:
            ask_once(args.question, top_k=args.top_k)
        else:
            ask_loop(top_k=args.top_k)
    elif args.command == "collect":
        collect_corpus()


if __name__ == "__main__":
    main()
