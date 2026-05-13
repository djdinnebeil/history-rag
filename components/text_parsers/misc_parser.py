import json
from pathlib import Path

def parse_misc(file_path: str) -> dict:
    """Parse a misc document into structured output."""
    path = Path(file_path)
    fname = path.stem  # filename without .txt
    
    # Read the file content
    raw_text = path.read_text(encoding="utf-8").strip()
    
    # Use filename as the document title and citation
    document_title = fname.replace("_", " ").replace("-", " ").title()
    
    # Simple citation format: just the filename
    citation = document_title
    
    return {
        "page_content": raw_text,
        "metadata": {
            "source_type": "misc",
            "source_id": fname,
            "source_name": document_title,
            "title": document_title,
            "file_path": str(file_path),
            "citation": citation
        }
    }
