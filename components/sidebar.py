import streamlit as st
from pathlib import Path
from core.database import ensure_db, set_project_db
from core.vector_store import get_qdrant_client, clear_qdrant_cache
from config import get_logger, developer_mode

logger = get_logger(__name__)

# Import settings from config
from config import PROJECTS_DIR

def list_projects():
    if not PROJECTS_DIR.exists():
        PROJECTS_DIR.mkdir()
    return [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()]

def clear_project_session_state():
    """Clear all project-specific session state variables"""
    keys_to_clear = [
        "db_client", "qdrant_initialized",
        "show_details_", "show_delete_all", "delete_confirmation"
    ]
    
    # Clear specific keys
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear keys that start with specific prefixes
    keys_to_remove = [k for k in st.session_state.keys() if k.startswith("show_details_")]
    for key in keys_to_remove:
        del st.session_state[key]

def render_sidebar():
    logger.debug("Starting render_sidebar function")
    projects = list_projects()
    logger.debug(f"Found projects: {projects}")

    # --- Manage session state for selected project ---
    if "selected_project" not in st.session_state:
        logger.debug("No selected_project in session state, setting to '-- New Project --'")
        st.session_state["selected_project"] = "-- New Project --"
    else:
        logger.debug(f"Current selected_project: {st.session_state['selected_project']}")
    
    # Initialize project change counter
    if "project_change_counter" not in st.session_state:
        logger.debug("No project_change_counter in session state, setting to 0")
        st.session_state["project_change_counter"] = 0
    else:
        logger.debug(f"Current project_change_counter: {st.session_state['project_change_counter']}")
    
    # Preserve navigation choice across project switches
    if "current_nav_choice" not in st.session_state:
        logger.debug("No current_nav_choice in session state, setting to 'Upload Documents'")
        st.session_state["current_nav_choice"] = "Upload Documents"
    else:
        logger.debug(f"Current current_nav_choice: {st.session_state['current_nav_choice']}")

    options = ["-- New Project --"] + projects
    logger.debug(f"Available options: {options}")
    
    selected = st.sidebar.selectbox(
        "Select a project",
        options,
        index=options.index(st.session_state["selected_project"]) 
              if st.session_state["selected_project"] in options else 0,
        key="project_select"
    )
    logger.debug(f"User selected: {selected}")
    
    # No project switching logic here - let the main app handle it
    # This prevents conflicts and race conditions
    
    # Validate that the selected project is valid
    if selected != "-- New Project --" and selected not in projects:
        logger.warning(f"Project '{selected}' no longer available!")
        st.error(f"❌ Project '{selected}' is no longer available!")
        st.session_state["selected_project"] = "-- New Project --"
        clear_project_session_state()
        st.rerun()

    # Check if selected project still exists (in case it was deleted)
    if selected != "-- New Project --" and not (PROJECTS_DIR / selected).exists():
        logger.error(f"Project '{selected}' no longer exists!")
        st.error(f"❌ Project '{selected}' no longer exists!")
        st.session_state["selected_project"] = "-- New Project --"
        clear_project_session_state()
        st.rerun()

    if selected == "-- New Project --":
        logger.debug("New project creation mode")
        new_name = st.sidebar.text_input("New project name")
        # collection_name = st.sidebar.text_input("Vector collection name", value=f"{new_name}_docs")
        collection_name = f"{new_name}_docs"

        if st.sidebar.button("Create Project"):
            logger.info(f"Creating new project: {new_name}")
            proj_dir = PROJECTS_DIR / new_name
            if proj_dir.exists():
                st.error("Project already exists!")
            else:
                (proj_dir / "qdrant").mkdir(parents=True)
                (proj_dir / "documents").mkdir(parents=True)
                set_project_db(new_name)
                ensure_db()
                st.success(f"Created project {new_name}")

                # Save collection name and update selected project
                st.session_state["collection_name"] = collection_name
                st.session_state["selected_project"] = new_name
                st.rerun()
        return None, None, None, None

    # --- Navigation menu ---
    logger.debug(f"Setting up navigation for project: {selected}")
    
    # Define navigation options
    if developer_mode:
        nav_options = ["Upload Documents", "Process Pending", "Document Sync", "Document Manager", "Vector Store", "Ask Questions", "Chat History", "Project Management"]
    else:
        nav_options = ["Upload Documents", "Document Sync", "Document Manager", "Ask Questions", "Chat History", "Project Management"]
    # Safely get the current navigation choice index
    current_nav = st.session_state.get("current_nav_choice", "Upload Documents")
    try:
        nav_index = nav_options.index(current_nav)
    except ValueError:
        # If the stored choice is invalid, default to Upload Documents
        nav_index = 0
        st.session_state["current_nav_choice"] = "Upload Documents"
    
    nav_choice = st.sidebar.radio(
        "Navigation",
        nav_options,
        index=nav_index,
        key=f"nav_radio_{selected}"  # Unique key per project to prevent conflicts
    )
    logger.debug(f"Navigation choice: {nav_choice}")
    
    # Update stored navigation choice immediately
    if nav_choice != st.session_state.get("current_nav_choice"):
        logger.info(f"Navigation changed from {st.session_state.get('current_nav_choice', 'None')} to {nav_choice}")
        st.session_state["current_nav_choice"] = nav_choice

    logger.debug(f"Processing project: {selected}")
    proj_dir = PROJECTS_DIR / selected
    logger.debug(f"Project directory: {proj_dir}")
    logger.debug(f"Project directory exists: {proj_dir.exists()}")
    
    set_project_db(selected)
    logger.debug(f"Database set for project: {selected}")
    
    con = ensure_db()
    logger.debug(f"Database connection established: {con is not None}")
    
    logger.debug(f"Getting Qdrant client for project: {selected}")
    client = get_qdrant_client(selected)
    logger.debug(f"Qdrant client obtained: {client is not None}")
    
    # st.success(f"Loaded project {selected}")
    logger.debug(f"Success message displayed for project: {selected}")
    
    # Update session state for the current project
    st.session_state["selected_project"] = selected
    st.session_state["collection_name"] = f"{selected}_docs"
    logger.debug(f"Session state updated: selected_project={selected}, collection_name={f'{selected}_docs'}")
    
    logger.debug(f"Returning values: selected={selected}, proj_dir={proj_dir}, db_client={con is not None}, nav_choice={nav_choice}")
    return selected, proj_dir, (con, client), nav_choice
