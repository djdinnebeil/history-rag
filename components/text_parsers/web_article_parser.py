import json
from pathlib import Path

# Load metadata.json if available
def load_web_metadata(file_path: Path) -> dict:
    """Load metadata.json from the web_articles folder containing the file."""
    meta_file = file_path.parent / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f).get("web_articles", {})
    return {}


def slug_to_title(slug: str) -> str:
    """Convert slug (e.g., amatol-nj-ghost-town) to title-cased string."""
    if not slug:
        return "Untitled"
    title = slug.replace("_", " ").replace("-", " ").title()
    # Fix common abbreviation issues
    title = title.replace(" Nj", " NJ")
    return title

def parse_web_article(file_path: str) -> dict:
    """Parse a web article into structured output."""
    path = Path(file_path)
    fname = path.stem
    parts = fname.split("__")

    date_str = parts[0]
    source_id = parts[1]
    slug = parts[2] if len(parts) > 2 else None

    # Lookup source by source_id
    WEB_META = load_web_metadata(path)
    entry = WEB_META.get(source_id, {})

    source_name = entry.get("source", source_id.replace("-", " ").title())
    raw_text = path.read_text(encoding="utf-8").strip()

    # Prefer metadata.json title, otherwise fall back to slug conversion
    citation_title = entry.get("title", slug_to_title(slug))
    citation = entry.get("citation", f'{source_name}, {date_str}, "{citation_title}"')

    return {
        "page_content": raw_text,
        "metadata": {
            "source_type": "web_article",
            "source_id": source_id,
            "source_name": source_name,
            "date": date_str,
            "slug": slug,
            "title": citation_title,
            "file_path": str(file_path),
            "citation": citation
        }
    }
