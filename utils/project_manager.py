#!/usr/bin/env python3
"""
Utility script for project management operations.
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import set_project_db, ensure_db
from config import PROJECTS_DIR, ensure_directories
from config import get_logger

logger = get_logger(__name__)


def create_project(project_name: str):
    """Create a new project."""
    logger.info(f"Creating project: {project_name}")
    
    # Ensure directories exist
    ensure_directories()
    
    # Set up database
    set_project_db(project_name)
    con = ensure_db()
    con.close()
    
    logger.info(f"✅ Project '{project_name}' created successfully")
    logger.info(f"   Database: {PROJECTS_DIR / project_name / f'{project_name}.sqlite'}")
    logger.info(f"   Vector store: {PROJECTS_DIR / project_name / 'qdrant'}")


def list_projects():
    """List all available projects."""
    ensure_directories()
    
    if not PROJECTS_DIR.exists():
        logger.info("No projects directory found.")
        return
    
    projects = [p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()]
    
    if not projects:
        logger.info("No projects found.")
        return
    
    logger.info("Available projects:")
    for i, project in enumerate(projects, 1):
        logger.info(f"  {i}. {project}")


def delete_project(project_name: str):
    """Delete a project (with confirmation)."""
    import shutil
    
    project_path = PROJECTS_DIR / project_name
    
    if not project_path.exists():
        logger.info(f"❌ Project '{project_name}' does not exist")
        return
    
    # Confirmation
    response = input(f"Are you sure you want to delete project '{project_name}'? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Operation cancelled.")
        return
    
    try:
        shutil.rmtree(project_path)
        logger.info(f"✅ Project '{project_name}' deleted successfully")
    except Exception as e:
        logger.info(f"❌ Error deleting project: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Project Management Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/project_manager.py create --name my_research
  python utils/project_manager.py list
  python utils/project_manager.py delete --name old_project
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new project')
    create_parser.add_argument('--name', required=True, help='Project name')
    create_parser.set_defaults(func=lambda args: create_project(args.name))
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    list_parser.set_defaults(func=lambda args: list_projects())
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a project')
    delete_parser.add_argument('--name', required=True, help='Project name')
    delete_parser.set_defaults(func=lambda args: delete_project(args.name))
    
    args = parser.parse_args()
    
    if not args.command:
        parser.logger.info_help()
        return
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
    except Exception as e:
        logger.info(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
