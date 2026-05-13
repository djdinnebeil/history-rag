"""
Core module for Historical Research Assistant.

This module provides simplified imports for all core functionality.
"""

# Database operations
from .database import (
    set_project_db,
    ensure_db,
    document_exists,
    insert_document,
    update_document_status,
    delete_document,
    list_documents,
    list_all_documents,
    list_documents_by_status,
    insert_chat_entry,
    get_chat_history,
    delete_chat_entry,
    clear_chat_history,
    get_chat_history_count,
    file_sha256,
    file_sha256_from_buffer
)

# Vector store operations
from .vector_store import (
    get_qdrant_client,
    ensure_collection,
    embed_directory_batched,
    view_vector_store,
    delete_document_from_store,
    clear_qdrant_cache,
    force_clear_all_qdrant_caches,
    clear_qdrant_locks,
    check_qdrant_processes,
    main_lock_cleanup,
    adaptive_chunk_documents
)

# Retrieval and embedding
from .retriever_chain import load_chain
from .embedder import embed_documents

# Agent functionality
from .langgraph_agent import (
    get_chains,
    build_agent_graph,
    tavily_search_tool,
    historical_rag_tool
)

# Batch processing
from .batch_processor import DocumentBatchProcessor

# Re-export commonly used items
__all__ = [
    # Database
    'set_project_db', 'ensure_db', 'document_exists', 'insert_document',
    'update_document_status', 'delete_document', 'list_documents',
    'list_all_documents', 'list_documents_by_status', 'insert_chat_entry',
    'get_chat_history', 'delete_chat_entry', 'clear_chat_history',
    'get_chat_history_count', 'file_sha256', 'file_sha256_from_buffer',
    
    # Vector store
    'get_qdrant_client', 'ensure_collection', 'embed_directory_batched',
    'view_vector_store', 'delete_document_from_store', 'clear_qdrant_cache',
    'force_clear_all_qdrant_caches', 'clear_qdrant_locks', 'check_qdrant_processes',
    'main_lock_cleanup',
    
    # Retrieval and embedding
    'load_chain', 'embed_documents',
    
    # Agent
    'get_chains', 'build_agent_graph', 'tavily_search_tool', 'historical_rag_tool',
    
    # Batch processing
    'DocumentBatchProcessor'
]
