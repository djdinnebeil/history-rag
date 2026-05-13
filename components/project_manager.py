import streamlit as st
import shutil
from pathlib import Path
from core import ensure_db, set_project_db, get_qdrant_client, clear_qdrant_cache

# Import settings from config
from config import PROJECTS_DIR, ARCHIVE_DIR

def ensure_archive_dir():
    """Ensure the archive directory exists"""
    if not ARCHIVE_DIR.exists():
        ARCHIVE_DIR.mkdir()

def archive_project(project_name: str, proj_dir: Path):
    """Archive a project by moving it to the archive directory"""
    ensure_archive_dir()
    
    # Create timestamped archive name to avoid conflicts
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{project_name}_{timestamp}"
    archive_path = ARCHIVE_DIR / archive_name
    
    try:
        # Move the entire project directory to archive
        shutil.move(str(proj_dir), str(archive_path))
        st.success(f"✅ Project '{project_name}' archived successfully to '{archive_name}'")
        return True
    except Exception as e:
        st.error(f"❌ Failed to archive project: {str(e)}")
        return False

def delete_project(project_name: str, proj_dir: Path):
    """Delete a project directory"""
    try:
        # Check if project is currently in use
        if st.session_state.get("selected_project") == project_name:
            # Clear Qdrant cache first
            clear_qdrant_cache()
            
            # Reset session state
            st.session_state["selected_project"] = "-- New Project --"
            st.session_state.pop("collection_name", None)
        
        # Check if project directory still exists (might have been moved to archive)
        if proj_dir.exists():
            # Remove the project directory
            shutil.rmtree(proj_dir)
            st.success(f"✅ Project '{project_name}' deleted successfully")
        else:
            st.success(f"✅ Project '{project_name}' was already archived/deleted")
        
        return True
    except Exception as e:
        st.error(f"❌ Failed to delete project: {str(e)}")
        return False

def restore_project(project_name: str, archive_path: Path, timestamp: str):
    """Restore a project from archive"""
    try:
        # Check if project already exists
        target_path = PROJECTS_DIR / project_name
        if target_path.exists():
            st.error(f"❌ Project '{project_name}' already exists! Cannot restore.")
            return False
        
        # Copy from archive to projects directory
        shutil.copytree(archive_path, target_path)
        
        # Remove the archive
        shutil.rmtree(archive_path)
        
        st.success(f"✅ Project '{project_name}' restored successfully from archive!")
        return True
    except Exception as e:
        st.error(f"❌ Failed to restore project: {str(e)}")
        return False

def render_project_manager(proj_dir: Path, db_client, collection_name: str):
    """Render the project management interface"""
    st.header("🗂️ Project Management")
    
    project_name = proj_dir.name
    # st.info(f"Managing project: **{project_name}**")
    
    # Project information
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Project Name", project_name)
        st.metric("Collection Name", collection_name)
    
    with col2:
        # Count .txt documents (including nested folders)
        docs_dir = proj_dir / "documents"
        doc_count = len(list(docs_dir.rglob("*.txt"))) if docs_dir.exists() else 0
        st.metric("Documents", doc_count)

        # Check Qdrant status
        qdrant_dir = proj_dir / "qdrant"
        qdrant_exists = qdrant_dir.exists()
        st.metric("Vector Store", "✅ Active" if qdrant_exists else "❌ Not Found")
        
        # Calculate project size
        project_size = sum(f.stat().st_size for f in proj_dir.rglob('*') if f.is_file())
        size_mb = project_size / (1024 * 1024)
        st.metric("Project Size", f"{size_mb:.1f} MB")
    
    st.divider()
    
    # Information about actions
    st.info("💡 **Note:** Archiving moves the project to the archive directory. Deletion permanently removes the project and all its data.")
    
    # Danger zone
    st.subheader("⚠️ Danger Zone")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Archive Project**")
        st.markdown("Move project to archive directory (project will be removed from active projects)")
        
        if st.button("📦 Archive Project", type="secondary"):
            st.info("📦 **Moving project to archive...**")
            
            if archive_project(project_name, proj_dir):
                # Switch to new project selection
                st.session_state["selected_project"] = "-- New Project --"
                st.rerun()
    
    with col2:
        st.markdown("**Delete Project**")
        st.markdown("⚠️ **This action cannot be undone!**")
        
        # Use session state to track delete confirmation
        if "delete_confirmation" not in st.session_state:
            st.session_state["delete_confirmation"] = False
        
        if not st.session_state["delete_confirmation"]:
            if st.button("🗑️ Delete Project", type="primary"):
                st.session_state["delete_confirmation"] = True
                st.rerun()
        else:
            st.error("⚠️ **WARNING: This will permanently delete the project!**")
            
            # Confirmation with options
            col_a, col_b, col_c = st.columns([1, 1, 1])
            
            with col_a:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state["delete_confirmation"] = False
                    st.rerun()
            
            with col_b:
                if st.button("📦 Archive Project", type="primary"):
                    if archive_project(project_name, proj_dir):
                        # Project is already moved to archive, just clean up session state
                        st.session_state["delete_confirmation"] = False
                        st.session_state["selected_project"] = "-- New Project --"
                        st.rerun()
            
            with col_c:
                if st.button("🗑️ Delete Only", type="primary"):
                    if delete_project(project_name, proj_dir):
                        st.session_state["delete_confirmation"] = False
                        st.session_state["selected_project"] = "-- New Project --"
                        st.rerun()
    
    st.divider()
    
    # Archive information
    st.subheader("📦 Archive Information")
    ensure_archive_dir()
    
    archived_projects = []
    if ARCHIVE_DIR.exists():
        for archive_path in ARCHIVE_DIR.iterdir():
            if archive_path.is_dir():
                # Extract project name and timestamp from archive name
                archive_name = archive_path.name
                if "_" in archive_name:
                    parts = archive_name.split("_")
                    if len(parts) >= 3:  # project_YYYYMMDD_HHMMSS
                        project_part = "_".join(parts[:-2])
                        timestamp = "_".join(parts[-2:])
                        archived_projects.append({
                            "name": project_part,
                            "timestamp": timestamp,
                            "path": archive_path,
                            "size": sum(f.stat().st_size for f in archive_path.rglob('*') if f.is_file())
                        })
    
    if archived_projects:
        st.markdown("**Archived Projects:**")
        for project in archived_projects:
            size_mb = project["size"] / (1024 * 1024)
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"- **{project['name']}** (archived: {project['timestamp']}) - {size_mb:.1f} MB")
            
            with col2:
                if st.button(f"🔄 Restore", key=f"restore_{project['timestamp']}", type="secondary"):
                    if restore_project(project["name"], project["path"], project["timestamp"]):
                        st.success(f"✅ Project '{project['name']}' restored successfully!")
                        st.rerun()
    else:
        st.info("No archived projects found.")
