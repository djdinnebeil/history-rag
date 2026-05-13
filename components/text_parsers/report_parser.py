import re
import json
from pathlib import Path

# Load metadata.json once at startup
def load_report_metadata(file_path: Path) -> dict:
    """Load metadata.json from the reports folder containing the file."""
    meta_file = file_path.parent / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f).get("reports", {})
    return {}

def parse_report(file_path: str) -> dict:
    """Parse a report text file into structured output."""
    path = Path(file_path)
    fname = path.stem  # filename without .txt

    # Split the filename
    # ex: description+years__pages__section__publication_year
    parts = fname.split("__")
    if len(parts) != 4:
        raise ValueError(f"Unexpected filename format: {fname}")

    description = parts[0]                          # war-department-report-on-amatol-1918-1919
    pages = parts[1]                                # p3936-3937
    section = parts[2]                              # amatol-arsenal
    publication_year = parts[3]                     # 1920

    # Extract coverage years from description
    # Looks for things like 1918, 1919, 1918-1919, 1918-1920
    year_matches = re.findall(r"(?:18|19|20)\d{2}(?:-(?:18|19|20)\d{2})?", description)
    coverage_years = year_matches[-1] if year_matches else None

    # Normalize values
    description_clean = description.replace("-", " ").title()
    section_clean = section.replace("-", " ").title()

    # Load metadata.json (user-provided titles or overrides)
    REPORT_META = load_report_metadata(path)
    entry = REPORT_META.get(fname, {})

    # Title: user-supplied > fallback to description
    title = entry.get("title") or description_clean

    # Build citation
    # "Title, p/pp <pages>, <Section>"
    pp_prefix = "pp." if "-" in pages else "p."
    citation = f"{title}, {pp_prefix} {pages.lstrip('p')}, {section_clean}"

    # Read file content
    raw_text = path.read_text(encoding="utf-8").strip()

    return {
        "page_content": raw_text,
        "metadata": {
            "source_type": "report",
            "source_id": fname,
            "title": title,
            "coverage_years": coverage_years,
            "publication_year": publication_year,
            "date": publication_year,
            "pages": pages,
            "section": section_clean,
            "file_path": str(file_path),
            "citation": citation
        }
    }
