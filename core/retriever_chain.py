# components/retriever_chain.py
from pathlib import Path
import streamlit as st
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_cohere import CohereRerank
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from config import using_cohere, get_logger, ENABLE_DYNAMIC_RETRIEVAL_SCALING, FIXED_RETRIEVAL_K, FIXED_FINAL_K, setup_logging
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, Range
from qdrant_client.http import models as qdrant_models
from config import LLM_MODEL

# Ensure logging is set up before creating logger
setup_logging()
from core.vector_store import get_qdrant_client, ensure_collection

logger = get_logger(__name__)

prompt = PromptTemplate(
    template="""You are a helpful historical research assistant.

Use the following historical documents to answer the question as accurately and factually as possible.

{context}

Question: {question}
Answer:""",
    input_variables=["context", "question"]
)

def load_chain(project_name: str, collection_name: str, source_types: list = None, year_range: tuple = None):
    """
    Load the retriever chain with optional source type and year filtering.
    
    Args:
        project_name: Name of the project
        collection_name: Name of the collection
        source_types: List of source types to filter by (e.g., ['book', 'journal'])
        year_range: Tuple of (start_year, end_year) for filtering
    """
    embeddings = OpenAIEmbeddings()

    client = get_qdrant_client(project_name)

    # Ensure collection exists before creating vectorstore
    ensure_collection(client, collection_name, embeddings)

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings
    )
    
    # Get collection info to determine optimal retrieval parameters
    try:
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        logger.debug(f"Collection has {total_points} total points")
    except Exception as e:
        logger.warning(f"Could not get collection info: {e}")
        total_points = 0
    
    # Build filter conditions
    filter_conditions = []
    
    # Add source type filter if specified
    if source_types and len(source_types) > 0:
        filter_conditions.append(
            FieldCondition(
                key="metadata.source_type",
                match=MatchAny(any=source_types)
            )
        )
    
    if year_range:
        start_year, end_year = year_range
        logger.debug(f"Year range filter: {start_year} to {end_year}")
        filter_conditions.append(
            FieldCondition(
                key="metadata.year",
                range={"gte":start_year, "lte":end_year}
            ))

    # Dynamic retrieval scaling based on collection size
    if ENABLE_DYNAMIC_RETRIEVAL_SCALING:
        # For small collections (< 100 docs), use smaller k
        # For medium collections (100-1000 docs), use moderate k  
        # For large collections (> 1000 docs), use larger k
        # For very large collections (> 5000 docs), use even larger k
        if total_points < 100:
            base_k = 50
            final_k = 30
        elif total_points < 1000:
            base_k = 30
            final_k = 15
        elif total_points < 5000:
            base_k = 50
            final_k = 20
        else:
            base_k = 75
            final_k = 25
    else:
        # Use fixed retrieval parameters
        base_k = FIXED_RETRIEVAL_K
        final_k = FIXED_FINAL_K
    
    logger.debug(f"Using retrieval parameters: base_k={base_k}, final_k={final_k} for {total_points} total points")
    print(f"🔍 RETRIEVAL CONFIG: base_k={base_k}, final_k={final_k} for {total_points} total points")
    print(f"🔍 COHERE RERANKING: {'ENABLED' if using_cohere else 'DISABLED'}")
    print(f"🔍 DYNAMIC SCALING: {'ENABLED' if ENABLE_DYNAMIC_RETRIEVAL_SCALING else 'DISABLED'}")

    # Create retriever with or without filters
    if filter_conditions:
        qdrant_filter = Filter(must=filter_conditions)
        naive_retriever = vectorstore.as_retriever(
            search_kwargs={"k": base_k, "filter": qdrant_filter}
        )
    else:
        naive_retriever = vectorstore.as_retriever(search_kwargs={"k": base_k})
    
    # Add debugging capability to see what's being retrieved
    def debug_retrieval(query: str, retriever, retriever_name: str = "retriever"):
        """Debug function to see what documents are being retrieved"""
        try:
            docs = retriever.get_relevant_documents(query)
            # Use both logger and print to ensure visibility
            debug_msg = f"=== {retriever_name.upper()} DEBUG ==="
            logger.debug(debug_msg)
            print(debug_msg)
            
            query_msg = f"Query: '{query}'"
            logger.debug(query_msg)
            print(query_msg)
            
            count_msg = f"Retrieved {len(docs)} documents"
            logger.debug(count_msg)
            print(count_msg)
            
            for i, doc in enumerate(docs[:5]):  # Show first 5
                doc_msg = f"Doc {i+1}: {doc.page_content[:100]}..."
                logger.debug(doc_msg)
                print(doc_msg)
                
                if hasattr(doc, 'metadata') and doc.metadata:
                    meta_msg = f"  Metadata: {doc.metadata}"
                    logger.debug(meta_msg)
                    print(meta_msg)
            
            separator = "=" * 50
            logger.debug(separator)
            print(separator)
            return docs
        except Exception as e:
            error_msg = f"Error in {retriever_name} debug: {e}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return []

    # Apply contextual compression if using_cohere is True
    if using_cohere:
        compressor = CohereRerank(model="rerank-v3.5")
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=naive_retriever, top_k=final_k
        )
        final_retriever = compression_retriever
    else:
        final_retriever = naive_retriever

    llm = ChatOpenAI(model_name=LLM_MODEL, temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=final_retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )
    # Create a wrapper class for debugging capabilities
    class DebugRetrievalQA:
        def __init__(self, qa_chain, naive_retriever, compression_retriever, vectorstore):
            self.qa_chain = qa_chain
            self.naive_retriever = naive_retriever
            self.compression_retriever = compression_retriever
            self.vectorstore = vectorstore
        
        def invoke(self, *args, **kwargs):
            """Delegate to the actual QA chain"""
            return self.qa_chain.invoke(*args, **kwargs)
        
        def test_retrieval(self, query: str):
            """Test function to debug retrieval issues"""
            test_msg = f"Testing retrieval for query: '{query}'"
            logger.debug(test_msg)
            print(f"DEBUG: {test_msg}")
            
            # Test naive retriever
            naive_docs = debug_retrieval(query, self.naive_retriever, "naive_retriever")
            
            # Test final retriever if different
            if using_cohere:
                final_docs = debug_retrieval(query, self.compression_retriever, "compression_retriever")
                return naive_docs, final_docs
            else:
                return naive_docs, naive_docs
        
        def test_retrieval_strategies(self, query: str):
            """Test different retrieval strategies to find the best one"""
            logger.debug(f"Testing different retrieval strategies for query: '{query}'")
            
            strategies = []
            
            # Test 1: Direct similarity search with different k values
            for k in [10, 20, 30, 50]:
                try:
                    docs = self.vectorstore.similarity_search(query, k=k)
                    strategies.append({
                        'name': f'direct_similarity_k{k}',
                        'docs': docs,
                        'count': len(docs)
                    })
                except Exception as e:
                    logger.error(f"Error testing direct similarity k={k}: {e}")
            
            # Test 2: Similarity search with scores
            try:
                docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=20)
                strategies.append({
                    'name': 'similarity_with_scores',
                    'docs': [doc for doc, score in docs_with_scores],
                    'scores': [score for doc, score in docs_with_scores],
                    'count': len(docs_with_scores)
                })
            except Exception as e:
                logger.error(f"Error testing similarity with scores: {e}")
            
            # Test 3: MMR (Maximum Marginal Relevance) search
            try:
                mmr_docs = self.vectorstore.max_marginal_relevance_search(query, k=20, fetch_k=50)
                strategies.append({
                    'name': 'mmr_search',
                    'docs': mmr_docs,
                    'count': len(mmr_docs)
                })
            except Exception as e:
                logger.error(f"Error testing MMR search: {e}")
            
            # Log results for each strategy
            for strategy in strategies:
                logger.debug(f"Strategy {strategy['name']}: {strategy['count']} docs")
                for i, doc in enumerate(strategy['docs'][:3]):
                    logger.debug(f"  {i+1}. {doc.page_content[:100]}...")
            
            return strategies
    
    # Create the debug wrapper
    if using_cohere:
        debug_qa_chain = DebugRetrievalQA(qa_chain, naive_retriever, compression_retriever, vectorstore)
    else:
        debug_qa_chain = DebugRetrievalQA(qa_chain, naive_retriever, naive_retriever, vectorstore)
    
    # Log successful chain creation
    logger.debug(f"Successfully created retriever chain for project: {project_name}, collection: {collection_name}")
    print(f"✅ RETRIEVER CHAIN CREATED: {project_name}/{collection_name}")
    print(f"✅ DEBUG FUNCTIONS AVAILABLE: test_retrieval, test_retrieval_strategies")

    if using_cohere:
        return debug_qa_chain, naive_retriever, compression_retriever
    else:
        return debug_qa_chain, naive_retriever