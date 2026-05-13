"""
Document Sync Utilities

This module provides utility functions for checking document sync status.
These functions can be used across multiple components to check for pending documents
and new files that need to be synced.

Key Functions:
- get_new_files(proj_dir, con): Get list of new files that haven't been processed
- get_pending_documents(con): Get list of documents with pending status
- has_new_files(proj_dir, con): Check if there are any new files to process
- has_pending_documents(con): Check if there are any pending documents
- get_document_sync_status(proj_dir, con): Get comprehensive sync status for notifications

Example usage for query notifications:
    from utils.document_sync_utils import get_document_sync_status
    
    sync_status = get_document_sync_status(proj_dir, con)
    if sync_status['needs_sync']:
        st.warning(f"You have {sync_status['new_files_count']} new files and {sync_status['pending_documents_count']} pending documents to sync.")
"""

import streamlit as st
from pathlib import Path
import hashlib
from core import document_exists, list_documents_by_status
from typing import List, Dict, Tuple


def get_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash for file content."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def scan_documents_folder(proj_dir: Path) -> List[Dict]:
    """Scan the documents folder and return all text files with their hashes."""
    documents_dir = proj_dir / "documents"
    if not documents_dir.exists():
        return []
    
    text_files = []
    for file_path in documents_dir.rglob("*.txt"):
        try:
            file_hash = get_file_hash(file_path)
            text_files.append({
                'path': file_path,
                'hash': file_hash,
                'size': file_path.stat().st_size
            })
        except Exception as e:
            st.warning(f"Could not process {file_path}: {e}")
    
    return text_files


def get_new_files(proj_dir: Path, con) -> List[Dict]:
    """Get list of new files that haven't been processed yet."""
    text_files = scan_documents_folder(proj_dir)
    new_files = []
    
    for file_info in text_files:
        if not document_exists(con, file_info['hash']):
            new_files.append(file_info)
    
    return new_files


def get_pending_documents(con) -> List[Tuple]:
    """Get list of documents with pending status."""
    return list_documents_by_status(con, "pending")


def has_new_files(proj_dir: Path, con) -> bool:
    """Check if there are any new files to process."""
    new_files = get_new_files(proj_dir, con)
    return len(new_files) > 0


def has_pending_documents(con) -> bool:
    """Check if there are any pending documents."""
    pending_docs = get_pending_documents(con)
    return len(pending_docs) > 0


def get_document_sync_status(proj_dir: Path, con) -> Dict[str, any]:
    """Get comprehensive document sync status for query notifications."""
    new_files = get_new_files(proj_dir, con)
    pending_docs = get_pending_documents(con)
    
    return {
        'has_new_files': len(new_files) > 0,
        'has_pending_documents': len(pending_docs) > 0,
        'new_files_count': len(new_files),
        'pending_documents_count': len(pending_docs),
        'new_files': new_files,
        'pending_documents': pending_docs,
        'needs_sync': len(new_files) > 0 or len(pending_docs) > 0
    }
