from pathlib import Path
import json
import re

def load_journal_metadata(file_path: Path) -> dict:
    """Load metadata.json from the journals folder containing the file."""
    meta_file = file_path.parent / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f).get("journals", {})
    return {}

def format_page_label(pages: str) -> str:
    """Format page label with p. or pp. depending on single vs. range."""
    if not pages:
        return None
    if "-" in pages:  # e.g., "45-54"
        return f"pp. {pages.replace('-', '–')}"  # en-dash for ranges
    else:
        return f"p. {pages}"

def extract_date_from_filename(fname: str) -> str | None:
    """Extract YYYY-MM-DD from filename prefix if present."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    return match.group(1) if match else None

def parse_journal_article(file_path: str) -> dict:
    """Parse a journal article into structured output."""
    path = Path(file_path)
    fname = path.stem

    entry = load_journal_metadata(path).get(fname, {})
    raw_text = path.read_text(encoding="utf-8").strip()

    source_id = fname
    source_name = entry.get("journal", source_id.title())

    # Extract date from filename
    date = extract_date_from_filename(fname)

    # Format pages nicely
    pages = entry.get("pages")
    page_label = format_page_label(pages) if pages else None

    # Build citation
    citation = entry.get("citation")
    if not citation:
        vol = entry.get("volume")
        issue = entry.get("issue")
        season = entry.get("season")
        title = entry.get("title", fname)

        if vol and issue and season and page_label:
            citation = f"{source_name} {vol}.{issue}, {season}, {page_label}, \"{title}\""
        elif vol and issue and page_label:
            citation = f"{source_name} {vol}.{issue}, {page_label}, \"{title}\""
        else:
            citation = f"{source_name}, \"{title}\""

    return {
        "page_content": raw_text,
        "metadata": {
            "source_type": "journal",
            "source_id": source_id,
            "source_name": source_name,
            "journal": entry.get("journal"),
            "volume": entry.get("volume"),
            "issue": entry.get("issue"),
            "season": entry.get("season"),
            "date": date,
            "pages": pages,
            "title": entry.get("title", fname),
            "file_path": str(file_path),
            "citation": citation,
        }
    }
