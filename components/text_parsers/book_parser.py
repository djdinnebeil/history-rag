import json
from pathlib import Path

def format_page_label(page: str) -> str:
    """Format page label with p. or pp. depending on single vs. range."""
    if "-" in page:  # e.g., p014-018
        pages = page.removeprefix("p")  # strip only one leading 'p'
        return f"pp. {pages.replace('-', '–')}"  # en-dash for ranges
    else:
        pages = page.removeprefix("p")
        return f"p. {pages}"

def parse_book(file_path: str) -> dict:
    """Parse a book text file into structured output with metadata and citation."""
    path = Path(file_path)
    fname = path.stem  # filename without .txt
    folder = path.parent
    source_id = folder.name

    # --- Load metadata.json ---
    meta_file = folder / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "books" in data:
            entry = data["books"].get(fname, {})
        else:
            entry = data
    else:
        entry = {}

    raw_text = path.read_text(encoding="utf-8").strip()

    # --- Parse filename into pages and section ---
    parts = fname.split("__", 1)
    pages = parts[0]  # e.g., p007 or p014-018
    section = parts[1].replace("_", " ").replace("-", " ").title() if len(parts) > 1 else None

    page_label = format_page_label(pages) if pages.startswith("p") else pages

    # --- Prepend section to content if available ---
    if section:
        page_content = f"{section}\n\n{raw_text}"
    else:
        page_content = raw_text

    # --- Extract metadata ---
    source_name = entry.get("title", source_id.replace("_", " ").title())
    year = entry.get("year")
    citation_format = entry.get("citation_format")

    # --- Build citation ---
    if citation_format:
        citation = citation_format.format(
            title=source_name,
            year=year or "",
            page=page_label,
            section=section or ""
        ).strip().replace(" ,", ",").replace("  ", " ")
    else:
        parts = [source_name]
        if year: parts.append(str(year))
        parts.append(page_label)
        if section: parts.append(section)
        citation = ", ".join(parts)

    return {
        "page_content": page_content,
        "metadata": {
            "source_type": "book",
            "source_id": source_id,
            "source_name": source_name,
            "title": entry.get("title", source_name),
            "author": entry.get("author"),
            "year": year,
            "date": year,
            "pages": pages,
            "section": section,
            "file_path": str(file_path),
            "citation": citation
        }
    }
