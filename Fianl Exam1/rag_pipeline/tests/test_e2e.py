"""
端到端测试 - 验证整个RAG流水线
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pipeline.indexing_pipeline import IndexingPipeline
from src.pipeline.query_pipeline import QueryPipeline
from config.settings import RAW_DATA_DIR


def main():
    """运行端到端测试"""
    print("=" * 60)
    print("RAG Pipeline 端到端测试")
    print("=" * 60)
    
    # 1. 测试索引流水线
    print("\n[1/4] 测试索引流水线")
    print("-" * 40)
    
    indexing_pipeline = IndexingPipeline(
        db_path=None,  # 使用内存模式
        collection_name="e2e_test",
        metadata_csv_path=str(project_root / "data" / "raw" / "metadata.csv")
    )
    
    result = indexing_pipeline.run(str(RAW_DATA_DIR), reset=True)
    
    print(f"  处理文件数: {result['total_files']}")
    print(f"  生成文本块数: {result['total_chunks']}")
    print(f"  集合文档总数: {result['collection_count']}")
    
    assert result['total_files'] > 0, "应该处理至少一个文件"
    assert result['total_chunks'] > 0, "应该生成至少一个文本块"
    assert result['collection_count'] > 0, "集合应该包含至少一个文档"
    
    print("  [PASS] 索引流水线测试通过")
    
    # 2. 测试查询流水线
    print("\n[2/4] 测试查询流水线")
    print("-" * 40)
    
    query_pipeline = QueryPipeline(
        chroma_manager=indexing_pipeline.chroma,
        embedder=indexing_pipeline.embedder,
        top_k=3
    )
    
    test_queries = [
        "什么是Python？",
        "如何定义函数？",
        "Pandas如何读取CSV文件？",
        "机器学习有哪些类型？",
    ]
    
    for query in test_queries:
        result = query_pipeline.run(query)
        
        assert 'answer' in result, "结果应该包含answer字段"
        assert 'sources' in result, "结果应该包含sources字段"
        assert 'has_llm' in result, "结果应该包含has_llm字段"
        
        print(f"  查询: {query}")
        print(f"    来源数: {len(result['sources'])}")
        print(f"    使用LLM: {result['has_llm']}")
    
    print("  [PASS] 查询流水线测试通过")
    
    # 3. 测试元数据过滤查询
    print("\n[3/4] 测试元数据过滤查询")
    print("-" * 40)
    
    # 按类别过滤
    result = query_pipeline.run("Python相关文档", filters={"category": "Python基础"})
    print(f"  按类别过滤 (Python基础): {len(result['sources'])} 个结果")
    
    # 按作者过滤
    result = query_pipeline.run("文档", filters={"author": "张三"})
    print(f"  按作者过滤 (张三): {len(result['sources'])} 个结果")
    
    print("  [PASS] 元数据过滤查询测试通过")
    
    # 4. 测试统计信息
    print("\n[4/4] 测试统计信息")
    print("-" * 40)
    
    stats = query_pipeline.get_stats()
    print(f"  ChromaDB统计: {stats['chroma_stats']}")
    print(f"  Top-K设置: {stats['top_k']}")
    print(f"  LLM可用: {stats['llm_available']}")
    
    print("  [PASS] 统计信息测试通过")
    
    # 测试完成
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    
    # 展示示例查询结果
    print("\n示例查询结果:")
    print("-" * 40)
    
    result = query_pipeline.run("什么是Python？")
    print(f"问题: 什么是Python？")
    print(f"回答: {result['answer'][:300]}...")
    print(f"\n参考来源:")
    for i, source in enumerate(result['sources'], 1):
        print(f"  {i}. {source['title']} (相似度: {source['score']:.2f})")


if __name__ == "__main__":
    main()
