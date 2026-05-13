"""
Navigation component to handle routing between different app sections.
"""
import streamlit as st
from components.uploader import render_uploader
from components.pending_list import render_pending_list
from components.process_pending import render_process_pending
from components.document_sync import render_document_sync
from components.vector_store_viewer import render_vector_store_viewer
from components.document_manager import render_document_manager
from components.qa_interface import render_qa_interface
from components.chat_history_viewer import render_chat_history_viewer
from components.project_manager import render_project_manager


def render_page(nav_choice: str, selected: str, proj_dir, db_client, collection_name: str):
    """
    Render the appropriate page based on navigation choice.
    
    Args:
        nav_choice: The selected navigation option
        selected: The selected project name
        proj_dir: The project directory path
        db_client: Database client tuple (con, client)
        collection_name: The collection name for vector store
    """
    if not db_client:
        st.error("Database client not available")
        return
    
    con, client = db_client
    
    # Route to appropriate component
    if nav_choice == "Upload Documents":
        render_uploader(proj_dir, con)
    elif nav_choice == "Pending Documents":
        render_pending_list(con)
    elif nav_choice == "Process Pending":
        render_process_pending(proj_dir, con, proj_dir / "qdrant", collection_name)
    elif nav_choice == "Document Sync":
        render_document_sync(proj_dir, con, collection_name)
    elif nav_choice == "Vector Store":
        render_vector_store_viewer(proj_dir, proj_dir / "qdrant", collection_name)
    elif nav_choice == "Document Manager":
        render_document_manager(proj_dir, con, collection_name, selected)
    elif nav_choice == "Ask Questions":
        render_qa_interface(selected, collection_name)
    elif nav_choice == "Chat History":
        render_chat_history_viewer(con, selected)
    elif nav_choice == "Project Management":
        render_project_manager(proj_dir, db_client, collection_name)
    else:
        st.warning(f"Unknown navigation choice: {nav_choice}")
