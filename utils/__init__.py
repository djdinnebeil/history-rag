"""
Utility scripts for Historical Research Assistant.
"""

# Document sync utilities
from .document_sync_utils import (
    get_file_hash,
    scan_documents_folder,
    get_new_files,
    get_pending_documents,
    has_new_files,
    has_pending_documents,
    get_document_sync_status
)

__all__ = [
    'get_file_hash',
    'scan_documents_folder', 
    'get_new_files',
    'get_pending_documents',
    'has_new_files',
    'has_pending_documents',
    'get_document_sync_status'
]
