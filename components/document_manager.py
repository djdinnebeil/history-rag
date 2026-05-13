import streamlit as st
from core.database import list_all_documents, delete_document
from core.vector_store import get_qdrant_client
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from pathlib import Path
import json
from utils.document_sync_utils import get_document_sync_status

COLUMNS = [
    "id", "path", "citation", "source_type", "source_id",
    "date", "num_chunks", "content_hash", "status", "added_at"
]

@st.dialog("File Modal Window")
def file_modal_content(content, doc_key):
    st.write(content)
    st.session_state[f"show_modal_{doc_key}"] = False

def debug_vector_metadata(client, collection_name):
    """Debug function to show vector metadata structure"""
    try:
        if client.collection_exists(collection_name):
            points = client.scroll(
                collection_name=collection_name,
                limit=5,  # Just get a few points for debugging
                with_payload=True,
                with_vectors=False
            )
            
            if points[0]:
                st.write("**Vector Metadata Structure (Sample):**")
                for i, point in enumerate(points[0][:3]):  # Show first 3 points
                    st.write(f"**Point {i+1}:**")
                    st.json(point.payload)
                    st.write("---")
            else:
                st.info("No vectors found in collection")
        else:
            st.warning("Collection does not exist")
    except Exception as e:
        st.error(f"Error debugging vector metadata: {str(e)}")



def render_document_manager(proj_dir, con, collection_name, project_name):
    st.subheader("📚 Document Manager")
    
    # Check for pending documents and new files
    if "db_client" in st.session_state and project_name and project_name != "-- New Project --":
        from pathlib import Path
        proj_dir = Path("projects") / project_name
        con, _ = st.session_state.db_client
        
        sync_status = get_document_sync_status(proj_dir, con)
        if sync_status['needs_sync']:
            st.warning(f"📋 **Document Sync Needed:** You have {sync_status['new_files_count']} new files and {sync_status['pending_documents_count']} pending documents to sync. Consider running the Document Sync tool to ensure all your documents are available for queries.")

    # Get all documents from database
    try:
        all_documents = list_all_documents(con)
        
        if not all_documents:
            st.info("No documents found in the database.")
            return
        
        st.write(f"**Total Documents:** {len(all_documents)}")
        
        # Count by status
        status_counts = {}
        for doc in all_documents:
            status = doc[8]  # status is at index 8
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Display status summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pending", status_counts.get("pending", 0))
        with col2:
            st.metric("Embedded", status_counts.get("embedded", 0))
        with col3:
            st.metric("Total", len(all_documents))
        
        # Filter options
        st.subheader("🔍 Filter Documents")
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.selectbox(
                "Filter by Status:",
                ["All", "pending", "embedded"],
                index=0
            )
        
        with col2:
            search_term = st.text_input("Search by path or citation:", placeholder="Enter search term...")
        
        # Apply filters
        filtered_docs = all_documents
        if status_filter != "All":
            filtered_docs = [doc for doc in filtered_docs if doc[8] == status_filter]
        
        if search_term:
            filtered_docs = [doc for doc in filtered_docs 
                           if search_term.lower() in str(doc[1]).lower() or 
                              search_term.lower() in str(doc[2]).lower()]
        
        st.write(f"**Filtered Results:** {len(filtered_docs)} documents")
        
        # Display documents
        st.subheader("📋 Document List")
        
        for i, doc in enumerate(filtered_docs):
            record = dict(zip(COLUMNS, doc))
            
            # Create a unique key for each document
            doc_key = f"doc_{record['id']}_{record['content_hash'][:8]}"
            
            # Document header with status indicator
            status_color = "🟡" if record['status'] == 'pending' else "🟢"
            header_text = f"{status_color} {Path(record['path']).name} ({record['status']})"
            
            with st.expander(header_text, expanded=False):
                # Document details
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Path:**", record['path'])
                    
                    # Show the actual file path being used
                    if Path(record['path']).is_absolute():
                        actual_path = Path(record['path'])
                    else:
                        # Try multiple possible path combinations
                        possible_paths = [
                            proj_dir / record['path'],  # Original path
                            proj_dir / "documents" / record['path'],  # Add documents/ prefix
                            proj_dir / "documents" / Path(record['path']).name  # Just filename
                        ]
                        
                        # Find the first path that exists
                        actual_path = None
                        for path in possible_paths:
                            if path.exists():
                                actual_path = path
                                break
                        
                        # If no path found, use the first one for display
                        if actual_path is None:
                            actual_path = possible_paths[0]
                    
                    st.write("**Full Path:**", str(actual_path))
                    st.write("**File Exists:**", "✅ Yes" if actual_path.exists() else "❌ No")
                    
                    # Show all attempted paths for debugging
                    if not actual_path.exists() and not Path(record['path']).is_absolute():
                        st.write("**Attempted Paths:**")
                        for i, path in enumerate(possible_paths):
                            exists = "✅" if path.exists() else "❌"
                            st.write(f"  {i+1}. {exists} {path}")
                    
                    if record['citation']:
                        st.write("**Citation:**", record['citation'])
                    if record['source_type']:
                        st.write("**Source Type:**", record['source_type'])
                    if record['source_id']:
                        st.write("**Source ID:**", record['source_id'])
                    if record['date']:
                        st.write("**Date:**", record['date'])
                    st.write("**Added:**", record['added_at'])
                    st.write("**Chunks:**", record['num_chunks'] or "N/A")
                    st.write("**Content Hash:**", record['content_hash'][:16] + "...")
                
                with col2:
                    # Action buttons
                    if st.button("View Details", key=f"view_{doc_key}"):
                        st.session_state[f"show_details_{doc_key}"] = True
                        st.session_state[f"show_modal_{doc_key}"] = True
                    
                    # TODO: Add back confirmation dialog for delete operations
                    if st.button("🗑️ Delete", key=f"delete_{doc_key}", type="secondary"):
                        try:
                            # Delete from database
                            delete_document(con, record['content_hash'])
                            
                            # If embedded, also remove from vector store
                            if record['status'] == 'embedded':
                                try:
                                    project_name = proj_dir.name
                                    client = get_qdrant_client(project_name)
                                    
                                    if client.collection_exists(collection_name):
                                        deleted_count = 0
                                        
                                        # Get all points in the collection to find matching ones
                                        try:
                                            all_points = client.scroll(
                                                collection_name=collection_name,
                                                limit=10000,  # Increased limit to catch all vectors
                                                with_payload=True,
                                                with_vectors=False
                                            )
                                            
                                            if all_points[0]:  # points are in first element
                                                matching_point_ids = []
                                                
                                                for point in all_points[0]:
                                                    payload = point.payload or {}
                                                    
                                                    # Check multiple possible metadata fields for matches
                                                    content_hash_match = payload.get('content_hash') == record['content_hash']
                                                    path_match = payload.get('path') == record['path']
                                                    filename_match = payload.get('filename') == Path(record['path']).name
                                                    
                                                    # Also check if the content_hash is in the metadata as a string
                                                    content_hash_in_metadata = (
                                                        record['content_hash'] in str(payload.get('metadata', {})) or
                                                        record['content_hash'] in str(payload.get('source', {}))
                                                    )
                                                    
                                                    if any([content_hash_match, path_match, filename_match, content_hash_in_metadata]):
                                                        matching_point_ids.append(point.id)
                                                
                                                if matching_point_ids:
                                                    # Delete all matching vectors
                                                    client.delete(
                                                        collection_name=collection_name,
                                                        points_selector=matching_point_ids
                                                    )
                                                    deleted_count = len(matching_point_ids)
                                                    st.success(f"✅ Deleted {deleted_count} vectors from vector store")
                                                    
                                                    # Log what was found for debugging
                                                    st.info(f"Found vectors by: content_hash={content_hash_match}, path={path_match}, filename={filename_match}")
                                                else:
                                                    st.warning("⚠️ No matching vectors found in vector store. This may indicate:")
                                                    st.write("- Vectors were stored with different metadata keys")
                                                    st.write("- The document wasn't properly embedded")
                                                    st.write("- Metadata structure is different than expected")
                                                    
                                                    # Show sample metadata for debugging
                                                    if all_points[0]:
                                                        sample_payload = all_points[0][0].payload
                                                        st.write("**Sample vector metadata:**")
                                                        st.json(sample_payload)
                                            
                                        except Exception as e:
                                            st.error(f"Error searching vector store: {str(e)}")
                                            st.info("You may need to manually clean up the vector store.")
                                    
                                except Exception as e:
                                    st.error(f"⚠️ Document deleted from database but failed to remove vectors: {str(e)}")
                                    st.info("You may need to manually clean up the vector store.")
                            
                            st.success(f"✅ Document '{Path(record['path']).name}' deleted successfully!")
                            
                            # Rerun to refresh the list
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Failed to delete document: {str(e)}")
                
                # Show detailed view if requested
                if st.session_state.get(f"show_details_{doc_key}", False):
                    st.subheader("📄 Full Document Details")
                    st.json(record)
                    
                    # Show file content if available
                    try:
                        # Handle both absolute and relative paths
                        if Path(record['path']).is_absolute():
                            file_path = Path(record['path'])
                        else:
                            # Try multiple possible path combinations
                            possible_paths = [
                                proj_dir / record['path'],  # Original path
                                proj_dir / "documents" / record['path'],  # Add documents/ prefix
                                proj_dir / "documents" / Path(record['path']).name  # Just filename
                            ]
                            
                            # Find the first path that exists
                            file_path = None
                            for path in possible_paths:
                                if path.exists():
                                    file_path = path
                                    break
                            
                            # If no path found, use the first one for error reporting
                            if file_path is None:
                                file_path = possible_paths[0]
                        
                        if file_path.exists():
                            st.subheader("📖 File Content Preview")
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                st.text_area("Content:", content, height=200, disabled=True)

                                if st.session_state.get(f"show_modal_{doc_key}", False):
                                    file_modal_content(content, doc_key)
                        else:
                            st.warning(f"File not found at: {file_path}")
                            st.info(f"Database path: {record['path']}")
                            st.info(f"Project directory: {proj_dir}")
                    except Exception as e:
                        st.error(f"Error reading file: {str(e)}")
                        st.info(f"Attempted path: {file_path}")
                
                # TODO: Add back confirmation dialog for delete operations with file deletion options
        
        # Bulk actions
        st.subheader("⚡ Bulk Actions")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("🔄 Refresh List"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Delete All Pending"):
                st.write("**Bulk Delete Options:**")
                delete_files_bulk = st.checkbox(
                    "🗑️ Also delete actual files from projects folder?",
                    key="delete_files_bulk",
                    help="If checked, all pending document files will be permanently removed from your computer."
                )
                
                if delete_files_bulk:
                    st.warning("⚠️ **Bulk File Deletion Warning:** All pending document files will be permanently deleted from your computer!")
                
                if st.checkbox("I understand this will delete all pending documents"):
                    pending_docs = [doc for doc in all_documents if doc[8] == "pending"]
                    if pending_docs:
                        try:
                            files_deleted = 0
                            for doc in pending_docs:
                                delete_document(con, doc[7])  # content_hash is at index 7
                                
                                # Handle file deletion if requested
                                if delete_files_bulk:
                                    try:
                                        # Determine the actual file path
                                        if Path(doc[1]).is_absolute():  # doc[1] is the path
                                            actual_file_path = Path(doc[1])
                                        else:
                                            # Try multiple possible path combinations
                                            possible_paths = [
                                                proj_dir / doc[1],  # Original path
                                                proj_dir / "documents" / doc[1],  # Add documents/ prefix
                                                proj_dir / "documents" / Path(doc[1]).name  # Just filename
                                            ]
                                            
                                            # Find the first path that exists
                                            actual_file_path = None
                                            for path in possible_paths:
                                                if path.exists():
                                                    actual_file_path = path
                                                    break
                                            
                                            # If no path found, use the first one for error reporting
                                            if actual_file_path is None:
                                                actual_file_path = possible_paths[0]
                                        
                                        # Delete the file
                                        if actual_file_path.exists():
                                            actual_file_path.unlink()  # Delete the file
                                            files_deleted += 1
                                    except Exception as e:
                                        st.warning(f"⚠️ Failed to delete file {doc[1]}: {str(e)}")
                            
                            if delete_files_bulk and files_deleted > 0:
                                st.success(f"✅ Deleted {len(pending_docs)} pending documents and {files_deleted} files from projects folder!")
                            else:
                                st.success(f"✅ Deleted {len(pending_docs)} pending documents from database (files kept in projects folder)")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to delete some documents: {str(e)}")
                    else:
                        st.info("No pending documents to delete.")
        
        with col3:
            # Check if we're in delete all mode
            if st.session_state.get("show_delete_all", False):
                st.write("**⚠️ DANGER: Delete ALL Documents**")
                st.error("**This will permanently delete ALL documents from this project!**")
                
                st.write("**What will be deleted:**")
                st.write("- All documents from the database (pending and embedded)")
                st.write("- All vectors from the vector store")
                st.write("- Optionally, all actual files from the projects folder")
                
                delete_all_files = st.checkbox(
                    "🗑️ Also delete ALL actual files from projects folder?",
                    key="delete_all_files",
                    help="If checked, ALL document files will be permanently removed from your computer."
                )
                
                if delete_all_files:
                    st.error("⚠️ **CRITICAL WARNING:** ALL document files will be permanently deleted from your computer!")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💀 Confirm Delete All", type="primary", key="delete_all_confirm"):
                        try:
                            total_docs = len(all_documents)
                            embedded_docs = [doc for doc in all_documents if doc[8] == "embedded"]
                            
                            st.write(f"**Starting deletion of {total_docs} documents...**")
                            
                            # Delete from vector store first
                            if embedded_docs:
                                try:
                                    project_name = proj_dir.name
                                    client = get_qdrant_client(project_name)
                                    
                                    if client.collection_exists(collection_name):
                                        # Delete entire collection
                                        client.delete_collection(collection_name)
                                        st.success(f"✅ Deleted vector collection '{collection_name}'")
                                        
                                    else:
                                        st.info("Vector collection did not exist")
                                except Exception as e:
                                    st.error(f"⚠️ Failed to delete vector collection: {str(e)}")
                            
                            # Delete from database
                            files_deleted = 0
                            for doc in all_documents:
                                try:
                                    delete_document(con, doc[7])  # content_hash is at index 7
                                    
                                    # Handle file deletion if requested
                                    if delete_all_files:
                                        try:
                                            # Determine the actual file path
                                            if Path(doc[1]).is_absolute():  # doc[1] is the path
                                                actual_file_path = Path(doc[1])
                                            else:
                                                # Try multiple possible path combinations
                                                possible_paths = [
                                                    proj_dir / doc[1],  # Original path
                                                    proj_dir / "documents" / doc[1],  # Add documents/ prefix
                                                    proj_dir / "documents" / Path(doc[1]).name  # Just filename
                                                ]
                                                
                                                # Find the first path that exists
                                                actual_file_path = None
                                                for path in possible_paths:
                                                    if path.exists():
                                                        actual_file_path = path
                                                        break
                                                
                                                # If no path found, use the first one for error reporting
                                                if actual_file_path is None:
                                                    actual_file_path = possible_paths[0]
                                            
                                            # Delete the file
                                            if actual_file_path.exists():
                                                actual_file_path.unlink()  # Delete the file
                                                files_deleted += 1
                                        except Exception as e:
                                            st.warning(f"⚠️ Failed to delete file {doc[1]}: {str(e)}")
                                            
                                except Exception as e:
                                    st.error(f"⚠️ Failed to delete document {doc[1]}: {str(e)}")
                            
                            # Success message
                            if delete_all_files and files_deleted > 0:
                                st.success(f"💀 **PROJECT WIPED:** Deleted {total_docs} documents, {files_deleted} files, and entire vector collection!")
                            else:
                                st.success(f"💀 **PROJECT WIPED:** Deleted {total_docs} documents and entire vector collection (files kept in projects folder)")
                            
                            # Clear session state and rerun
                            st.session_state["show_delete_all"] = False
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Failed to delete all documents: {str(e)}")
                
                with col2:
                    if st.button("❌ Cancel", key="cancel_delete_all"):
                        st.session_state["show_delete_all"] = False
                        st.rerun()
            
            else:
                # Show the initial delete all button
                if st.button("🗑️ Delete All Documents", key="show_delete_all_btn"):
                    st.session_state["show_delete_all"] = True
                    st.rerun()
        
        with col4:
            if st.button("🧹 Clean Vector Store"):
                if st.checkbox("I understand this will attempt to clean orphaned vectors"):
                    try:
                        project_name = proj_dir.name
                        client = get_qdrant_client(project_name)
                        
                        if client.collection_exists(collection_name):
                            # Get all vectors in the collection
                            all_points = client.scroll(
                                collection_name=collection_name,
                                limit=10000,
                                with_payload=True,
                                with_vectors=False
                            )
                            
                            if all_points[0]:
                                orphaned_count = 0
                                for point in all_points[0]:
                                    if point.payload:
                                        # Check if this vector has a content_hash that exists in our database
                                        content_hash = point.payload.get('content_hash')
                                        if content_hash:
                                            # Check if document still exists in database
                                            doc_exists = con.execute(
                                                "SELECT 1 FROM documents WHERE content_hash = ?", 
                                                (content_hash,)
                                            ).fetchone()
                                            
                                            if not doc_exists:
                                                # This vector is orphaned, delete it
                                                client.delete(
                                                    collection_name=collection_name,
                                                    points_selector=[point.id]
                                                )
                                                orphaned_count += 1
                                
                                if orphaned_count > 0:
                                    st.success(f"✅ Cleaned {orphaned_count} orphaned vectors from collection")
                                else:
                                    st.info("✅ No orphaned vectors found")
                            else:
                                st.info("No vectors found in collection")
                        else:
                            st.warning("Collection does not exist")
                            
                    except Exception as e:
                        st.error(f"Failed to clean vector store: {str(e)}")
        
        with col5:
            if st.button("🔍 Debug Vectors"):
                try:
                    project_name = proj_dir.name
                    client = get_qdrant_client(project_name)
                    debug_vector_metadata(client, collection_name)
                except Exception as e:
                    st.error(f"Failed to debug vectors: {str(e)}")
    
    except Exception as e:
        st.error(f"Failed to load documents: {str(e)}")
        st.info("Check your database connection and try again.")
