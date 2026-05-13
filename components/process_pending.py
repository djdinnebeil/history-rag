import streamlit as st
from core import list_documents_by_status, update_document_status, get_qdrant_client, adaptive_chunk_documents, embed_documents
from components.text_parsers.unified_parser import parse_file
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.schema import Document
from pathlib import Path
from components.pending_list import render_pending_list
from core import DocumentBatchProcessor
from config import get_logger

logger = get_logger(__name__)

def render_process_pending(proj_dir, con, qdrant_path, collection_name):
    st.subheader("⚙️ Process Pending Documents")

    # Debug information
    logger.debug("🔍 Debug Information")
    logger.debug(f"Project directory: {proj_dir}")
    logger.debug(f"Database connection: {con}")
    logger.debug(f"Database path: {getattr(con, 'path', 'Unknown')}")
    
    # Check if the database file actually exists
    if hasattr(con, 'path'):
        db_file = Path(con.path)
        st.write(f"Database file exists: {db_file.exists()}")
        st.write(f"Database file size: {db_file.stat().st_size if db_file.exists() else 'N/A'} bytes")
    
    # Check project database path
    project_name = Path(proj_dir).name
    expected_db_path = proj_dir / f"{project_name}.sqlite"
    logger.debug(f"Expected DB path: {expected_db_path}")
    logger.debug(f"Expected DB exists: {expected_db_path.exists()}")
    
    rows = list_documents_by_status(con, "pending")
    if not rows:
        st.info("No pending documents to process.")
        return

    st.write(f"Found {len(rows)} pending document(s).")
    
    render_pending_list(con)

    # Show initial database state
    st.subheader("📊 Initial Database State")
    initial_pending = list_documents_by_status(con, "pending")
    initial_embedded = list_documents_by_status(con, "embedded")
    st.write(f"Pending documents: {len(initial_pending)}")
    st.write(f"Embedded documents: {len(initial_embedded)}")
    
    
    # Add a test button to verify database updates work
    # if st.button("🧪 Test Database Update"):
    #     if initial_pending:
    #         test_row = initial_pending[0]
    #         test_hash = test_row[7]  # content_hash is at index 7
    #         test_path = test_row[1]  # path is at index 1
            
    #         st.info(f"Testing update on: {test_path}")
    #         st.info(f"Content hash: {test_hash}")
            
    #         # Try to update just this one document
    #         try:
    #             # First, check current status
    #             current_status = con.execute("SELECT status, num_chunks FROM documents WHERE content_hash = ?", (test_hash,)).fetchone()
    #             st.write(f"Current status: {current_status}")
                
    #             # Try manual update
    #             st.write("Attempting manual database update...")
    #             con.execute("UPDATE documents SET status = 'test_status', num_chunks = 999 WHERE content_hash = ?", (test_hash,))
    #             con.commit()
    #             st.write("Manual update executed and committed")
                
    #             # Check if it worked
    #             updated_docs = list_documents_by_status(con, "test_status")
    #             if updated_docs:
    #                 st.success(f"✅ Test update successful! Document now has status: test_status")
                    
    #                 # Revert the test change
    #                 update_document_status(con, test_hash, 0, "pending")
    #                 con.commit()
    #                 st.info("🔄 Test change reverted")
    #             else:
    #                 st.error("❌ Test update failed - document not found with test_status")
    #         except Exception as e:
    #             st.error(f"❌ Test update error: {e}")
    #             import traceback
    #             st.error(f"Full error: {traceback.format_exc()}")
    #     else:
    #         st.warning("No pending documents to test with")
    
    # # Add a button to manually check database state
    # if st.button("🔍 Check Database State"):
    #     st.subheader("Raw Database Queries")
        
    #     # Check pending documents
    #     pending_query = con.execute("SELECT COUNT(*) FROM documents WHERE status = 'pending'").fetchone()
    #     st.write(f"Pending count (raw SQL): {pending_query[0]}")
        
    #     # Check embedded documents
    #     embedded_query = con.execute("SELECT COUNT(*) FROM documents WHERE status = 'embedded'").fetchone()
    #     st.write(f"Embedded count (raw SQL): {embedded_query[0]}")
        
    #     # Show all documents with their status
    #     all_docs = con.execute("SELECT path, status, num_chunks FROM documents ORDER BY status").fetchall()
    #     st.write("All documents:")
    #     for doc in all_docs:
    #         st.write(f"- {doc[0]}: status={doc[1]}, chunks={doc[2]}")
    
    # # Add a button to show raw row structure
    # if st.button("📋 Show Raw Row Structure"):
    #     if initial_pending:
    #         st.subheader("Raw Row Structure for First Pending Document")
    #         test_row = initial_pending[0]
    #         st.write(f"Row length: {len(test_row)}")
    #         st.write("Row contents:")
    #         for i, value in enumerate(test_row):
    #             st.write(f"  [{i}]: {value}")
            
    #         # Show the expected mapping
    #         st.write("\nExpected mapping:")
    #         st.write(f"  [0]: id = {test_row[0]}")
    #         st.write(f"  [1]: path = {test_row[1]}")
    #         st.write(f"  [2]: citation = {test_row[2]}")
    #         st.write(f"  [3]: source_type = {test_row[3]}")
    #         st.write(f"  [4]: source_id = {test_row[4]}")
    #         st.write(f"  [5]: date = {test_row[5]}")
    #         st.write(f"  [6]: num_chunks = {test_row[6]}")
    #         st.write(f"  [7]: content_hash = {test_row[7]}")
    #         st.write(f"  [8]: status = {test_row[8]}")
    #         st.write(f"  [9]: added_at = {test_row[9]}")
    #     else:
    #         st.warning("No pending documents to examine")
    
    # Add a progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    if st.button("🚀 Process All Pending"):
        project_name = Path(proj_dir).name
        client = get_qdrant_client(project_name)

        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        processed_count = 0
        failed_count = 0
        
        # Initialize batch processor
        from core.vector_store import BATCH_SIZE
        batch_processor = DocumentBatchProcessor(BATCH_SIZE, project_name, collection_name)
        
        st.info(f"📦 Using batch processing with batch size: {BATCH_SIZE}")
        
        for i, row in enumerate(rows):
            # Fix the row indexing - content_hash is at index 6, not 5
            path, citation, source_type, source_id, date, num_chunks, content_hash, status, added_at = row[1:10]
            
            # Update progress
            progress = (i + 1) / len(rows)
            progress_bar.progress(progress)
            status_text.text(f"Processing {i + 1}/{len(rows)}: {path}")

            try:
                # Debug: Show the exact content hash we're working with
                st.write(f"🔍 Processing document: {path}")
                st.write(f"  Content hash: {content_hash}")
                st.write(f"  Current status: {status}")
                st.write(f"  Current chunks: {num_chunks}")
                
                # Test: Can we find this document by content hash?
                st.write(f"🔍 Testing database lookup by content hash...")
                test_lookup = con.execute("SELECT * FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
                if test_lookup:
                    st.write(f"  ✅ Document found in database: {test_lookup[1]} (path), status: {test_lookup[8]}")
                else:
                    st.error(f"  ❌ Document NOT found in database by content hash: {content_hash}")
                    # Try to find it by path instead
                    path_lookup = con.execute("SELECT * FROM documents WHERE path = ?", (path,)).fetchone()
                    if path_lookup:
                        st.write(f"  ℹ️ Document found by path: {path_lookup[7]} (hash), status: {path_lookup[8]}")
                        st.write(f"  ⚠️ Content hash mismatch! Expected: {content_hash}, Found: {path_lookup[7]}")
                    else:
                        st.error(f"  ❌ Document not found by path either: {path}")
                
                # Parse the file
                file_path = proj_dir / "documents" / path
                if not file_path.exists():
                    st.error(f"❌ File not found: {file_path}")
                    failed_count += 1
                    continue
                
                parsed = parse_file(str(file_path))
                doc = Document(page_content=parsed["page_content"], metadata=parsed["metadata"])
                docs = adaptive_chunk_documents([doc])
                
                # Add document chunks to batch processor
                updates = batch_processor.add_document(docs, content_hash, len(docs))
                st.write(f"  📄 Added {len(docs)} chunks to batch (total: {batch_processor.get_buffer_size()})")
                
                # Process any database updates if batch was flushed
                if updates:
                    st.write(f"  🚀 Batch flushed with {len(updates)} document updates")
                    try:
                        for chunk_hash, chunk_count in updates:
                            update_document_status(con, chunk_hash, chunk_count, "embedded")
                        con.commit()
                        st.success(f"  ✅ Batch {batch_processor.get_batch_count()} processed successfully")
                    except Exception as e:
                        st.error(f"  ❌ Database update failed: {e}")
                        # Mark documents as error
                        for chunk_hash, chunk_count in updates:
                            update_document_status(con, chunk_hash, 0, "error")
                
                processed_count += 1
                
            except Exception as e:
                st.error(f"❌ Failed {path}: {str(e)}")
                import traceback
                st.error(f"Full error: {traceback.format_exc()}")
                failed_count += 1
        
        # Final flush of remaining chunks
        final_updates = batch_processor.finalize()
        if final_updates:
            st.write(f"  🚀 Flushing final batch with {len(final_updates)} document updates...")
            try:
                for chunk_hash, chunk_count in final_updates:
                    update_document_status(con, chunk_hash, chunk_count, "embedded")
                con.commit()
                st.success(f"  ✅ Final batch processed successfully")
            except Exception as e:
                st.error(f"  ❌ Final batch processing failed: {e}")
                # Mark documents as error
                for chunk_hash, chunk_count in final_updates:
                    update_document_status(con, chunk_hash, 0, "error")

        # Final status
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        if failed_count == 0:
            st.success(f"🎉 All {processed_count} pending documents processed successfully in {batch_processor.get_batch_count()} batch(es)!")
        else:
            st.warning(f"⚠️ Processing complete: {processed_count} successful, {failed_count} failed in {batch_processor.get_batch_count()} batch(es)")
            
        # Show final database state
        st.subheader("📊 Final Database Status")
        final_pending = list_documents_by_status(con, "pending")
        final_embedded = list_documents_by_status(con, "embedded")
        
        st.write(f"Pending documents: {len(final_pending)}")
        st.write(f"Embedded documents: {len(final_embedded)}")
        
        if final_pending:
            st.write("**Remaining pending documents:**")
            for row in final_pending:
                path = row[1]
                st.write(f"- {path}")
        
        # Force a final commit to ensure all changes are saved
        con.commit()
        
        # Show detailed comparison
        st.subheader("🔍 Database Change Summary")
        st.write(f"Documents processed: {processed_count}")
        st.write(f"Documents failed: {failed_count}")
        st.write(f"Batches processed: {batch_processor.get_batch_count()}")
        st.write(f"Pending before: {len(initial_pending)}, after: {len(final_pending)}")
        st.write(f"Embedded before: {len(initial_embedded)}, after: {len(final_embedded)}")
        
        if len(final_pending) == 0 and processed_count > 0:
            st.success("🎯 All pending documents successfully moved to embedded status!")
        elif len(final_pending) > 0:
            st.warning(f"⚠️ {len(final_pending)} documents still show as pending")
