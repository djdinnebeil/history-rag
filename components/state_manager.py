"""
State management component to handle project state and session management.
"""
import streamlit as st
from core.vector_store import clear_qdrant_cache, force_clear_all_qdrant_caches
from config import get_logger

logger = get_logger(__name__)


def initialize_app_state():
    """Initialize the application state on first run."""
    if "qdrant_initialized" not in st.session_state:
        clear_qdrant_cache()
        st.session_state["qdrant_initialized"] = True
    
    if 'initialized' not in st.session_state:
        st.session_state["initialized"] = True


def handle_project_change(selected: str):
    """
    Handle project changes and cleanup old state.
    
    Args:
        selected: The currently selected project name
    """
    # Initialize tracking if not present
    if "last_selected_project" not in st.session_state:
        st.session_state["last_selected_project"] = selected
        st.session_state["project_change_counter"] = 0
        return
    
    # Check if project has changed
    if st.session_state["last_selected_project"] != selected:
        logger.info(f"Project change detected: {st.session_state['last_selected_project']} → {selected}")
        
        # Clear old project data
        if "db_client" in st.session_state:
            logger.debug("Clearing old db_client")
            del st.session_state["db_client"]
        
        # Clear Qdrant cache
        logger.debug("Clearing Qdrant cache")
        force_clear_all_qdrant_caches()
        
        # Update tracking
        st.session_state["last_selected_project"] = selected
        st.session_state["project_change_counter"] = st.session_state.get("project_change_counter", 0) + 1
        logger.info(f"Updated project tracking: {selected}, counter: {st.session_state['project_change_counter']}")
        
        # Force a rerun to ensure clean state
        st.rerun()
    else:
        logger.debug(f"Same project, no change needed: {selected}")


def handle_navigation_change(nav_choice: str):
    """
    Handle navigation changes and force rerun if needed.
    
    Args:
        nav_choice: The selected navigation choice
    """
    if "last_nav_choice" not in st.session_state:
        st.session_state["last_nav_choice"] = nav_choice
    elif st.session_state["last_nav_choice"] != nav_choice:
        logger.info(f"Navigation changed: {st.session_state['last_nav_choice']} → {nav_choice}")
        st.session_state["last_nav_choice"] = nav_choice
        st.rerun()


def set_project_state(selected: str):
    """
    Set the project state in session state.
    
    Args:
        selected: The selected project name
    """
    if selected != "-- New Project --":
        st.session_state["selected_project"] = selected
        st.session_state["collection_name"] = f"{selected}_docs"


def render_project_info(selected: str):
    """
    Render project information display.
    
    Args:
        selected: The selected project name
    """
    if "selected_project" in st.session_state and st.session_state["selected_project"] != "-- New Project --":
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"📁 Current Project: **{st.session_state['selected_project']}**")
        with col2:
            collection_name = st.session_state.get("collection_name", "Not set")
            st.info(f"🗂️ Collection: **{collection_name}**")
        
        # Show project change counter for debugging
        if "project_change_counter" in st.session_state:
            logger.debug(f"Project changes: {st.session_state['project_change_counter']}")


def debug_project_state(selected: str, proj_dir, db_client, nav_choice: str):
    """
    Print debug information about the current project state.
    
    Args:
        selected: The selected project name
        proj_dir: The project directory
        db_client: The database client
        nav_choice: The navigation choice
    """
    logger.debug(f"Debug: selected={selected}, last_selected_project={st.session_state.get('last_selected_project', 'None')}, db_client={db_client is not None}")
    
    if selected != "-- New Project --" and proj_dir is not None:
        logger.debug(f"Directory exists: {proj_dir.exists()}")
        logger.debug(f"Project details: {selected}")
        logger.debug(f"Navigation choice: {nav_choice}")
        logger.debug(f"DB client type: {type(db_client)}")
    elif selected == "-- New Project --":
        logger.debug("No project selected - new project creation mode")
    else:
        # logger.warning(f"Project selected but proj_dir is None: {selected}")
        pass
