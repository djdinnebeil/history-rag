import os
from dotenv import load_dotenv

load_dotenv()

import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from tqdm import tqdm
from qdrant_client.models import VectorParams, Distance

from components.text_parsers.unified_parser import parse_file
from core.database import *
import streamlit as st

# Import settings from config
from config import BATCH_SIZE, get_logger

logger = get_logger(__name__)

# Global client registry to track active clients
_active_clients = {}

def _get_client_key(project_name: str) -> str:
    """Generate a unique key for each project's Qdrant client."""
    return f"qdrant_client_{project_name}"

def is_client_active(project_name: str) -> bool:
    """Check if a Qdrant client is already active for a project."""
    client_key = _get_client_key(project_name)
    return client_key in _active_clients

def force_close_all_clients():
    """Force close all active Qdrant clients. Use with caution."""
    global _active_clients
    for client_key, client in list(_active_clients.items()):
        try:
            client.close()
            logger.debug(f"Closed client: {client_key}")
        except Exception as e:
            logger.error(f"Error closing client {client_key}: {e}")
        finally:
            del _active_clients[client_key]
    logger.info("All Qdrant clients closed")

def close_qdrant_client(project_name: str):
    """Close a specific Qdrant client for a project."""
    client_key = _get_client_key(project_name)
    if client_key in _active_clients:
        try:
            _active_clients[client_key].close()
            del _active_clients[client_key]
        except:
            pass

def force_clear_qdrant_locks(project_name: str):
    """Force clear Qdrant locks by removing lock files and waiting."""
    import time
    import os
    
    project_dir = Path.cwd() / "projects" / project_name
    qdrant_path = project_dir / "qdrant"
    
    if qdrant_path.exists():
        # Look for lock files and remove them
        lock_files = list(qdrant_path.glob("*.lock"))
        for lock_file in lock_files:
            try:
                os.remove(lock_file)
                logger.debug(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Could not remove lock file {lock_file}: {e}")
        
        # Wait a bit for the OS to release any remaining locks
        time.sleep(2.0)
        logger.info(f"Force cleared locks for {project_name}")

def get_qdrant_client(project_name: str) -> QdrantClient:
    """
    Return a QdrantClient for the given project.
    Stores data under: projects/{project_name}/qdrant
    """
    # Check if we already have an active client for this project
    client_key = _get_client_key(project_name)
    if client_key in _active_clients:
        try:
            # Test if the existing client is still working
            _active_clients[client_key].get_collections()
            return _active_clients[client_key]
        except:
            # Client is broken, remove it
            try:
                _active_clients[client_key].close()
            except:
                pass
            del _active_clients[client_key]
    
    # Create a new client
    project_dir = Path.cwd() / "projects" / project_name
    qdrant_path = project_dir / "qdrant"
    qdrant_path.mkdir(parents=True, exist_ok=True)
    
    try:
        client = QdrantClient(path=str(qdrant_path))
        # Store the client for reuse
        _active_clients[client_key] = client
        return client
    except Exception as e:
        # If creation fails, try to clear locks and retry once
        try:
            force_clear_qdrant_locks(project_name)
            client = QdrantClient(path=str(qdrant_path))
            _active_clients[client_key] = client
            return client
        except Exception as retry_e:
            raise RuntimeError(f"Failed to create Qdrant client for {project_name}: {retry_e}")

def clear_qdrant_cache():
    """Clear the active Qdrant clients to force fresh connections."""
    global _active_clients
    for client in _active_clients.values():
        try:
            client.close()
        except:
            pass
    _active_clients.clear()

def force_clear_all_qdrant_caches():
    """Force clear all Qdrant caches and connections. Use when switching projects."""
    # Clear active clients
    global _active_clients
    for client in _active_clients.values():
        try:
            client.close()
        except:
            pass
    _active_clients.clear()
    
    # Force garbage collection
    import gc
    gc.collect()
    
    # Small delay to ensure OS releases any file handles
    import time
    time.sleep(0.1)

# --- Step 1: Recursively find all .txt files ---
from langchain.schema import Document

def find_txt_files(root_dir: str) -> list[Path]:
    return [p for p in Path(root_dir).rglob('*.txt')]

# --- Step 2: Load ONE file and attach metadata ---
def load_one_document(path: Path, root_dir: str):
    parsed = parse_file(str(path))  # unified output
    return [Document(page_content=parsed["page_content"], metadata=parsed["metadata"])]

# --- Step 3: Chunk helper ---
def adaptive_chunk_documents(docs: list[Document], model: str = 'text-embedding-3-small') -> list[Document]:
    """Take a list of Documents, split adaptively, return list of Documents."""
    out_docs = []
    import tiktoken
    enc = tiktoken.encoding_for_model(model)

    for doc in docs:
        text = doc.page_content
        token_count = len(enc.encode(text))

        # Improved chunking strategy for better retrieval
        if token_count < 300:
            # Very small documents - keep whole but ensure minimum context
            out_docs.append(doc)
        elif token_count < 800:
            # Medium documents - use smaller chunks with more overlap
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                model_name=model, chunk_size=400, chunk_overlap=100
            )
            out_docs.extend(splitter.split_documents([doc]))
        elif token_count < 2000:
            # Large documents - use medium chunks
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                model_name=model, chunk_size=600, chunk_overlap=120
            )
            out_docs.extend(splitter.split_documents([doc]))
        else:
            # Very large documents - use larger chunks but still reasonable
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                model_name=model, chunk_size=800, chunk_overlap=150
            )
            out_docs.extend(splitter.split_documents([doc]))

    return out_docs

def embedding_dim(embeddings) -> int:
    return len(embeddings.embed_query('dim?'))

def ensure_collection(client: QdrantClient, name: str, embeddings) -> None:
    if not client.collection_exists(name):
        dim = embedding_dim(embeddings)
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

# --- Step 4: Batching Helpers ---
def flush_batch(buffer, vs, con):
    """Embed and insert a batch of documents into Qdrant + commit SQLite."""
    if not buffer:
        return

    vs.add_documents(buffer)
    con.commit()
    logger.info(f'Flushed {len(buffer)} chunks → Qdrant')
    buffer.clear()

# --- Step 5: Main Ingestion ---
def embed_directory_batched(root_dir: str, project_name: str, collection_name: str, batch_size: int = BATCH_SIZE) -> None:
    txt_paths = find_txt_files(root_dir)
    if not txt_paths:
        logger.warning(f'No .txt files found under {root_dir}')
        return

    # Initialize DB
    con = ensure_db()

    # Initialize embeddings + vectorstore
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small')

    client = get_qdrant_client(project_name)

    # Ensure collection exists
    ensure_collection(client, collection_name, embeddings)
    vs = QdrantVectorStore(client=client, collection_name=collection_name, embedding=embeddings)

    staging_buffer = []  # holds chunks before flushing

    logger.info(f'Indexing {len(txt_paths)} files from {root_dir} …')
    for path in tqdm(txt_paths, desc='Indexing files'):
        # Step 1: hash check
        h = file_sha256(path)
        if document_exists(con, h):
            logger.debug(f'SKIP (already indexed): {path.relative_to(root_dir)}')
            continue

        # Step 2: parse and insert doc row
        parsed = parse_file(str(path))

        # Step 3: chunk and attach doc_id
        docs = [Document(page_content=parsed['page_content'], metadata=parsed['metadata'])]
        chunks = adaptive_chunk_documents(docs)
        for ch in chunks:
            ch.metadata['doc_id'] = h

        insert_document(con, path, parsed, h, len(chunks))

        # Step 4: stage chunks
        staging_buffer.extend(chunks)
        logger.debug(f'Staged {len(chunks)} chunks from {path.relative_to(root_dir)}')

        # Step 5: flush if buffer full
        if len(staging_buffer) >= batch_size:
            flush_batch(staging_buffer, vs, con)

    # Final flush
    flush_batch(staging_buffer, vs, con)
    client.close()   # releases the file lock

def view_vector_store(client, collection_name, limit=20):
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=limit,
    )
    results = []
    for pt in points:
        meta = pt.payload.get("metadata", {})
        results.append({
            "id": pt.id,
            "doc_id": str(meta.get("doc_id", "")),
            "source": str(meta.get("source", "")),
            "date": str(meta.get("date", "")),   # force everything to string
            "page_content": (pt.payload.get("page_content") or "")[:200] + "..."
        })
    return results

from qdrant_client.models import Filter, FieldCondition, MatchValue

def delete_document_from_store(con, client, collection_name: str, doc_id: str) -> None:
    """Delete a document from SQLite and Qdrant using its doc_id."""
    # 1. Delete from Qdrant
    client.delete(
        collection_name=collection_name,
        wait=True,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="metadata.doc_id",  # always nested
                    match=MatchValue(value=str(doc_id))
                )
            ]
        ),
    )

    # 2. Delete from SQLite
    delete_document(con, doc_id)
    logger.info(f"Deleted document {doc_id} from DB and Qdrant.")


# --- Lock Management Functions (merged from clear_qdrant_locks.py) ---

def clear_qdrant_locks():
    """Clear any existing Qdrant locks and force cleanup."""
    logger.debug("🔧 Clearing Qdrant locks and connections...")
    
    try:
        # Force close all clients
        force_close_all_clients()
        
        # Clear the cache
        clear_qdrant_cache()
        
        # Force clear locks for all projects
        projects_dir = Path.cwd() / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    project_name = project_dir.name
                    logger.debug(f"🔓 Clearing locks for project: {project_name}")
                    force_clear_qdrant_locks(project_name)
        
        logger.debug("✅ Successfully cleared Qdrant locks and connections")
        return True
        
    except Exception as e:
        logger.debug(f"❌ Error clearing Qdrant locks: {e}")
        return False


def check_qdrant_processes():
    """Check if there are any Qdrant processes running."""
    logger.debug("🔍 Checking for Qdrant processes...")
    
    try:
        import psutil
        
        qdrant_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'qdrant' in proc.info['name'].lower():
                    qdrant_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if qdrant_processes:
            logger.debug(f"⚠️  Found {len(qdrant_processes)} Qdrant processes:")
            for proc in qdrant_processes:
                logger.debug(f"   PID {proc['pid']}: {proc['name']}")
            return True
        else:
            logger.debug("✅ No Qdrant processes found")
            return False
            
    except ImportError:
        logger.debug("⚠️  psutil not available, skipping process check")
        return False


def main_lock_cleanup():
    """Main function to clear Qdrant locks (for CLI usage)."""
    logger.debug("🚀 Qdrant Lock Cleanup Utility")
    logger.debug("=" * 40)
    
    # Check for processes first
    has_processes = check_qdrant_processes()
    
    # Clear locks
    success = clear_qdrant_locks()
    
    if has_processes:
        logger.debug("\n⚠️  Note: Qdrant processes were detected.")
        logger.debug("   You may need to restart your application or kill these processes manually.")
    
    if success:
        logger.debug("\n✅ Cleanup completed successfully!")
        logger.debug("   You can now try running your application again.")
    else:
        logger.debug("\n❌ Cleanup failed. You may need to:")
        logger.debug("   1. Restart your terminal/IDE")
        logger.debug("   2. Kill any remaining Qdrant processes")
        logger.debug("   3. Restart your application")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main_lock_cleanup())
