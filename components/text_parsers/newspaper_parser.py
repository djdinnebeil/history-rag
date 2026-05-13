import re
import json
from pathlib import Path
from datetime import datetime, timedelta

def previous_date(date_str: str) -> str:
    """
    Given a date string (YYYY-MM-DD), return the previous day as a string.
    Handles month/year boundaries and leap years.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    prev_day = dt - timedelta(days=1)
    return prev_day.strftime("%Y-%m-%d")

# Load metadata.json once at startup
def load_newspaper_metadata(file_path: Path) -> dict:
    meta_file = file_path.parent.parent / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"default": {"attribution_patterns": []}}

def parse_newspaper_article(file_path: str) -> dict:
    """Parse a newspaper text file into structured output."""

    # --- Step 1: Read + normalize line endings ---
    raw_text = Path(file_path).read_text(encoding="utf-8")
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # --- Step 2: Split into header vs body ---
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    header = parts[0].strip()
    body = parts[1].strip() if len(parts) > 1 else ""

    # --- Step 3: Extract filename metadata ---
    # ex: 1919-12-18__philadelphia-inquirer__p5__auction-at-amatol.txt
    fname = Path(file_path).stem
    parts = fname.split("__")
    date_str = parts[0]               # e.g., 1919-12-18
    source_id = parts[1]              # e.g., philadelphia-inquirer
    newspaper = source_id.replace("-", " ").title()
    page = parts[2]                   # e.g., p5

    # --- Step 4: Load attribution patterns ---
    metadata = load_newspaper_metadata(Path(file_path))
    patterns = []

    # Get newspaper-specific patterns first
    if newspaper in metadata:
        patterns.extend(metadata[newspaper].get("attribution_patterns", []))

    # Add default patterns as fallback
    if "default" in metadata:
        patterns.extend(metadata["default"].get("attribution_patterns", []))

    # --- Step 5: Parse header ---
    header_lines = [l.strip() for l in header.split("\n") if l.strip()]

    title = header_lines[0].title() if header_lines else "Untitled"
    city_date = header_lines[-1] if len(header_lines) > 1 else None
    middle_lines = header_lines[1:-1] if len(header_lines) > 2 else []

    subtitles, attribution = [], None
    for line in middle_lines:
        line_norm = line.lower()
        if any(line_norm.startswith(pat) for pat in patterns):
            attribution = line
        else:
            subtitles.append(line)

    # --- Step 6: Build citation ---
    citation_title = title
    if subtitles:
        citation_title += ": " + "; ".join(subtitles)

    citation = f'{newspaper}, {date_str}, {page}, "{citation_title}"'

    # --- Step 7: Build page_content ---
    chunk_parts = [title]
    if subtitles:
        chunk_parts.extend(subtitles)
    chunk_parts.append(previous_date(date_str))
    chunk_parts.append(body)
    page_content = "\n".join([p for p in chunk_parts if p.strip()])

    # Checking the year
    try:
        year = int(date_str[:4])
    except ValueError:
        year = None


    # --- Step 8: Return structured output ---
    return {
        "page_content": page_content,
        "metadata": {
            "source_type": "newspaper",
            "source_id": source_id,   # consistent with books/journals
            "source_name": newspaper, # human-readable form
            "date": date_str,
            "year": year,
            "page": page,
            "title": title,
            "subtitles": subtitles,
            "attribution": attribution,
            "city_date": city_date,
            "file_path": str(file_path),
            "citation": citation
        }
    }
