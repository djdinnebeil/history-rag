#!/usr/bin/env python3
"""
Utility script to clear Qdrant locks and force close any existing connections.
Use this if you're getting "already accessed" errors.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.vector_store import main_lock_cleanup

if __name__ == "__main__":
    sys.exit(main_lock_cleanup())
