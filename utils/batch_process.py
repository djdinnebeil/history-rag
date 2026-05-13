#!/usr/bin/env python3
"""
Utility script for batch processing documents.
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import set_project_db, embed_directory_batched
from config import BATCH_SIZE
from config import get_logger

logger = get_logger(__name__)


def process_documents(project_name: str, directory: str, batch_size: int = None):
    """Process documents in a directory."""
    if not Path(directory).exists():
        logger.info(f"❌ Directory does not exist: {directory}")
        return False
    
    if batch_size is None:
        batch_size = BATCH_SIZE
    
    logger.info(f"Processing documents in: {directory}")
    logger.info(f"Project: {project_name}")
    logger.info(f"Batch size: {batch_size}")
    
    set_project_db(project_name)
    collection_name = f"{project_name}_docs"
    
    try:
        embed_directory_batched(directory, project_name, collection_name, batch_size)
        logger.info("✅ Document processing completed successfully")
        return True
    except Exception as e:
        logger.info(f"❌ Error processing documents: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Batch Document Processing Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python utils/batch_process.py --project my_research --directory ./documents
  python utils/batch_process.py --project my_research --directory ./documents --batch-size 20
        """
    )
    
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--directory', required=True, help='Directory containing documents to process')
    parser.add_argument('--batch-size', type=int, help=f'Batch size (default: {BATCH_SIZE})')
    
    args = parser.parse_args()
    
    try:
        success = process_documents(args.project, args.directory, args.batch_size)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
