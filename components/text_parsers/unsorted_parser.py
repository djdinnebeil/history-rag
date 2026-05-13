import json
from pathlib import Path

def parse_unsorted(file_path: str) -> dict:
    """Parse an unsorted document into structured output."""
    path = Path(file_path)
    fname = path.stem  # filename without .txt
    
    # Read the file content
    raw_text = path.read_text(encoding="utf-8").strip()
    
    # Use filename as the source name and citation
    source_name = fname.replace("_", " ").replace("-", " ").title()
    
    # Simple citation format: just the filename
    citation = source_name
    
    return {
        "page_content": raw_text,
        "metadata": {
            "source_type": "unsorted",
            "source_id": fname,
            "source_name": source_name,
            "title": source_name,
            "file_path": str(file_path),
            "citation": citation
        }
    }
