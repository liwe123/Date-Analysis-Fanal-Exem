"""
RAG Pipeline Streamlit演示界面
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from src.pipeline.indexing_pipeline import IndexingPipeline
from src.pipeline.query_pipeline import QueryPipeline
from src.storage import ChromaManager
from src.embedding import Embedder
from src.generation import LLMClient
from config.settings import (CHROMA_DB_PATH, CHROMA_COLLECTION_NAME,
                             EMBEDDING_MODEL, OPENAI_API_KEY, TOP_K,
                             RAW_DATA_DIR)


@st.cache_resource
def get_chroma_manager():
    """获取ChromaDB管理器（缓存）"""
    return ChromaManager(db_path=CHROMA_DB_PATH, collection_name=CHROMA_COLLECTION_NAME)


@st.cache_resource
def get_embedder():
    """获取嵌入生成器（缓存）"""
    return Embedder(backend='sentence-transformers', model_name=EMBEDDING_MODEL)


@st.cache_resource
def get_llm_client():
    """获取LLM客户端（缓存）"""
    if OPENAI_API_KEY:
        return LLMClient(api_key=OPENAI_API_KEY)
    return None


@st.cache_resource
def get_indexing_pipeline():
    """获取索引流水线（缓存）"""
    metadata_csv = project_root / "data" / "raw" / "metadata.csv"
    return IndexingPipeline(
        db_path=CHROMA_DB_PATH,
        collection_name=CHROMA_COLLECTION_NAME,
        metadata_csv_path=str(metadata_csv) if metadata_csv.exists() else None
    )


@st.cache_resource
def get_query_pipeline():
    """获取查询流水线（缓存）"""
    chroma = get_chroma_manager()
    embedder = get_embedder()
    llm_client = get_llm_client()
    
    return QueryPipeline(
        chroma_manager=chroma,
        embedder=embedder,
        llm_client=llm_client,
        top_k=TOP_K
    )


def main():
    """主函数"""
    st.set_page_config(
        page_title="RAG Pipeline - 企业知识库",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 RAG Pipeline - 企业知识库检索增强生成系统")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 管理")
        
        # 索引按钮
        st.subheader("文档索引")
        if st.button("📥 执行索引", use_container_width=True):
            with st.spinner("正在索引文档..."):
                try:
                    pipeline = get_indexing_pipeline()
                    result = pipeline.run(str(RAW_DATA_DIR), reset=True)
                    st.success(f"索引完成！共处理 {result['total_chunks']} 个文档块")
                except Exception as e:
                    st.error(f"索引失败: {e}")
        
        # 统计信息
        st.subheader("📊 数据库统计")
        try:
            chroma = get_chroma_manager()
            stats = chroma.get_stats()
            st.metric("文档数量", stats.get('total_documents', 0))
        except Exception as e:
            st.warning(f"无法获取统计信息: {e}")
        
        # 设置
        st.subheader("🔧 设置")
        top_k = st.slider("返回结果数", 1, 10, TOP_K)
        
        # LLM状态
        st.subheader("🤖 LLM状态")
        llm_client = get_llm_client()
        if llm_client and llm_client.is_available():
            st.success("OpenAI API 可用")
        else:
            st.info("使用回退模式（无LLM）")
    
    # 主区域
    tab1, tab2 = st.tabs(["💬 查询", "📖 文档浏览"])
    
    with tab1:
        # 查询输入
        question = st.text_input(
            "请输入您的问题：",
            placeholder="例如：什么是Python？如何定义函数？",
            key="query_input"
        )
        
        if question:
            with st.spinner("正在检索和生成答案..."):
                try:
                    pipeline = get_query_pipeline()
                    result = pipeline.run(question, top_k=top_k)
                    
                    # 显示答案
                    st.header("💡 回答")
                    st.write(result['answer'])
                    
                    # 显示来源
                    if result['sources']:
                        st.header("📚 参考来源")
                        
                        for i, source in enumerate(result['sources'], 1):
                            with st.expander(
                                f"📄 {source.get('title', '未知')} "
                                f"(相似度: {source.get('score', 0):.2f})"
                            ):
                                col1, col2 = st.columns([1, 2])
                                
                                with col1:
                                    st.write(f"**文件**: {source.get('file', '未知')}")
                                    st.write(f"**作者**: {source.get('author', '未知')}")
                                    st.write(f"**日期**: {source.get('date', '未知')}")
                                    st.write(f"**类别**: {source.get('category', '未知')}")
                                
                                with col2:
                                    st.write("**内容预览**:")
                                    st.text(source.get('text_preview', ''))
                
                except Exception as e:
                    st.error(f"查询失败: {e}")
    
    with tab2:
        st.header("📖 文档浏览")
        
        try:
            chroma = get_chroma_manager()
            
            # 获取所有文档
            all_docs = chroma.get()
            
            if all_docs['ids']:
                # 按文件分组
                files = {}
                for i, metadata in enumerate(all_docs.get('metadatas', [])):
                    file_name = metadata.get('file_name', '未知')
                    if file_name not in files:
                        files[file_name] = {
                            'title': metadata.get('title', '未知'),
                            'author': metadata.get('author', '未知'),
                            'date': metadata.get('date', '未知'),
                            'category': metadata.get('category', '未知'),
                            'chunks': 0,
                        }
                    files[file_name]['chunks'] += 1
                
                # 显示文件列表
                for file_name, info in files.items():
                    with st.expander(f"📄 {info['title']} ({file_name})"):
                        st.write(f"**作者**: {info['author']}")
                        st.write(f"**日期**: {info['date']}")
                        st.write(f"**类别**: {info['category']}")
                        st.write(f"**文档块数**: {info['chunks']}")
            else:
                st.info("数据库为空，请先执行索引")
        
        except Exception as e:
            st.error(f"加载文档失败: {e}")


if __name__ == "__main__":
    main()
