"""
RAG Pipeline 主入口脚本
"""
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import setup_logging, ensure_directories

setup_logging()
ensure_directories()


def build_indexing_pipeline():
    """构建索引流水线"""
    from src.pipeline.indexing_pipeline import IndexingPipeline
    from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
    
    metadata_csv = project_root / "data" / "raw" / "metadata.csv"
    
    return IndexingPipeline(
        db_path=CHROMA_DB_PATH,
        collection_name=CHROMA_COLLECTION_NAME,
        metadata_csv_path=str(metadata_csv) if metadata_csv.exists() else None
    )


def build_query_pipeline():
    """构建查询流水线"""
    from src.pipeline.query_pipeline import QueryPipeline
    from src.storage import ChromaManager
    from src.embedding import Embedder
    from src.generation import LLMClient
    from config.settings import (CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, 
                                 EMBEDDING_MODEL, OPENAI_API_KEY, TOP_K)
    
    # 初始化组件
    chroma = ChromaManager(db_path=CHROMA_DB_PATH, collection_name=CHROMA_COLLECTION_NAME)
    embedder = Embedder(backend='sentence-transformers', model_name=EMBEDDING_MODEL)
    
    # 初始化LLM（如果可用）
    llm_client = None
    if OPENAI_API_KEY:
        llm_client = LLMClient(api_key=OPENAI_API_KEY)
    
    return QueryPipeline(
        chroma_manager=chroma,
        embedder=embedder,
        llm_client=llm_client,
        top_k=TOP_K
    )


def cmd_index(args):
    """执行索引"""
    from config.settings import RAW_DATA_DIR
    
    pipeline = build_indexing_pipeline()
    
    data_dir = args.data_dir if args.data_dir else str(RAW_DATA_DIR)
    reset = args.reset if hasattr(args, 'reset') else False
    
    print(f"开始索引 (目录: {data_dir}, 重置: {reset})")
    result = pipeline.run(data_dir, reset=reset)
    
    print(f"\n索引完成:")
    print(f"  处理文件数: {result['total_files']}")
    print(f"  生成文本块数: {result['total_chunks']}")
    print(f"  集合文档总数: {result['collection_count']}")


def cmd_query(args):
    """执行查询"""
    pipeline = build_query_pipeline()
    
    result = pipeline.run(args.question)
    
    print(f"\n{'='*50}")
    print(f"问题: {args.question}")
    print(f"{'='*50}")
    print(f"\n回答:\n{result['answer']}")
    
    if result['sources']:
        print(f"\n参考来源:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source['title']} (相似度: {source['score']:.2f})")


def cmd_interactive(args):
    """交互式查询"""
    pipeline = build_query_pipeline()
    
    print("="*50)
    print("RAG Pipeline 交互式查询")
    print("输入 'quit' 或 'exit' 退出")
    print("="*50)
    
    while True:
        try:
            question = input("\n请输入问题: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("再见！")
                break
            
            result = pipeline.run(question)
            
            print(f"\n回答:\n{result['answer']}")
            
            if result['sources']:
                print(f"\n参考来源:")
                for i, source in enumerate(result['sources'], 1):
                    print(f"  {i}. {source['title']} (相似度: {source['score']:.2f})")
        
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}")


def cmd_stats(args):
    """显示统计信息"""
    pipeline = build_query_pipeline()
    stats = pipeline.get_stats()
    
    print("数据库统计信息:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")


def cmd_reset(args):
    """重置数据库"""
    from src.storage import ChromaManager
    from config.settings import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME
    
    confirm = input("确定要重置数据库吗？(y/N): ").strip().lower()
    
    if confirm == 'y':
        chroma = ChromaManager(db_path=CHROMA_DB_PATH, collection_name=CHROMA_COLLECTION_NAME)
        chroma.delete_all()
        print("数据库已重置")
    else:
        print("取消重置")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline - 企业知识库检索增强生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py index                     # 执行索引
  python run.py index --reset             # 重置并重新索引
  python run.py query "什么是Python？"    # 执行查询
  python run.py interactive               # 交互式查询
  python run.py stats                     # 显示统计信息
  python run.py reset                     # 重置数据库
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # index命令
    index_parser = subparsers.add_parser('index', help='执行索引')
    index_parser.add_argument('--data-dir', help='数据目录路径')
    index_parser.add_argument('--reset', action='store_true', help='重置数据库')
    index_parser.set_defaults(func=cmd_index)
    
    # query命令
    query_parser = subparsers.add_parser('query', help='执行查询')
    query_parser.add_argument('question', help='查询问题')
    query_parser.set_defaults(func=cmd_query)
    
    # interactive命令
    interactive_parser = subparsers.add_parser('interactive', help='交互式查询')
    interactive_parser.set_defaults(func=cmd_interactive)
    
    # stats命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_parser.set_defaults(func=cmd_stats)
    
    # reset命令
    reset_parser = subparsers.add_parser('reset', help='重置数据库')
    reset_parser.set_defaults(func=cmd_reset)
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    args.func(args)


if __name__ == "__main__":
    main()
