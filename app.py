import streamlit as st
from components.sidebar import render_sidebar
from components.navigation import render_page
from components.state_manager import (
    initialize_app_state,
    handle_project_change,
    handle_navigation_change,
    set_project_state,
    render_project_info,
    debug_project_state
)
from config import initialize_app, get_logger

# Initialize logging and directories
initialize_app()
logger = get_logger(__name__)


def main():
    """Main application entry point."""
    if "initialized" not in st.session_state or not st.session_state["initialized"]:
        st.session_state["initialized"] = True
        logger.info("Starting Historical Research Assistant")

    # Initialize application state
    initialize_app_state()
    
    # Set up the main title
    st.title("📜 Historical Research Assistant")
    
    # Show initial message if not initialized
    if not st.session_state.get("initialized", False):
        st.write("To use this application, please select a project or create a new one.")
        logger.info("Application initialized, waiting for project selection")
    
    # Get project and navigation state from sidebar
    selected, proj_dir, db_client, nav_choice = render_sidebar()
    
    # Handle project state management
    handle_project_change(selected)
    set_project_state(selected)
    
    # Handle navigation changes
    handle_navigation_change(nav_choice)
    
    # Render project information
    render_project_info(selected)
    
    # Debug information
    debug_project_state(selected, proj_dir, db_client, nav_choice)
    
    # Ensure we have a valid project selected
    if selected == "-- New Project --":
        st.warning("⚠️ Please select a project or create a new one to continue.")
        st.stop()
    
    # Render the appropriate page
    if db_client:
        # Store database client in session state for components to use
        st.session_state.db_client = db_client
        collection_name = st.session_state.get("collection_name", f"{selected}_docs")
        
        render_page(nav_choice, selected, proj_dir, db_client, collection_name)


if __name__ == "__main__":
    main()
