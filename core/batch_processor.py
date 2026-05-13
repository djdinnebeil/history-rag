from core.embedder import embed_documents
from core.database import update_document_status
from typing import List, Tuple, Optional
from langchain.schema import Document

class DocumentBatchProcessor:
    """Handles batching of document chunks for vector store processing."""
    
    def __init__(self, batch_size: int, project_name: str, collection_name: str):
        self.batch_size = batch_size
        self.project_name = project_name
        self.collection_name = collection_name
        self.staging_buffer = []
        self.batch_count = 0
        self.document_chunk_counts = {}
    
    def add_document(self, chunks: List[Document], content_hash: str, chunk_count: int) -> Optional[List[Tuple[str, int]]]:
        """Add document chunks to the staging buffer.
        
        Args:
            chunks: List of Document chunks to add
            content_hash: Hash identifier for the document
            chunk_count: Number of chunks for this document
            
        Returns:
            List of (hash, chunk_count) tuples for database updates, or None if no batch was flushed
        """
        # Add content_hash to metadata for tracking
        for chunk in chunks:
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata['content_hash'] = content_hash
        
        # Store the chunk count for this document
        self.document_chunk_counts[content_hash] = chunk_count
        
        # Add chunks to staging buffer
        self.staging_buffer.extend(chunks)
        
        # Flush if buffer is full
        if len(self.staging_buffer) >= self.batch_size:
            return self.flush_batch()
        return None
    
    def flush_batch(self) -> List[Tuple[str, int]]:
        """Process the current batch and clear the buffer.
        
        Returns:
            List of (hash, chunk_count) tuples for database updates
            
        Raises:
            Exception: If batch processing fails
        """
        if not self.staging_buffer:
            return []
            
        try:
            # Process batch through vector store
            embed_documents(self.staging_buffer, self.project_name, self.collection_name)
            
            # Prepare database updates for all documents in this batch
            updates = []
            for chunk in self.staging_buffer:
                chunk_hash = chunk.metadata.get('content_hash')
                if chunk_hash and chunk_hash in self.document_chunk_counts:
                    updates.append((chunk_hash, self.document_chunk_counts[chunk_hash]))
            
            # Clear buffer and increment batch count
            self.staging_buffer.clear()
            self.batch_count += 1
            
            return updates
            
        except Exception as e:
            # Mark documents as error in case of failure
            error_updates = []
            for chunk in self.staging_buffer:
                chunk_hash = chunk.metadata.get('content_hash')
                if chunk_hash:
                    error_updates.append((chunk_hash, 0, "error"))
            
            # Clear buffer even on error
            self.staging_buffer.clear()
            raise e
    
    def finalize(self) -> List[Tuple[str, int]]:
        """Process any remaining chunks in the buffer.
        
        Returns:
            List of (hash, chunk_count) tuples for database updates, or empty list if buffer is empty
        """
        if self.staging_buffer:
            return self.flush_batch()
        return []
    
    def get_batch_count(self) -> int:
        """Get the total number of batches processed."""
        return self.batch_count
    
    def get_buffer_size(self) -> int:
        """Get the current number of chunks in the buffer."""
        return len(self.staging_buffer)
    
    def reset(self) -> None:
        """Reset the processor state."""
        self.staging_buffer.clear()
        self.batch_count = 0
        self.document_chunk_counts.clear()
