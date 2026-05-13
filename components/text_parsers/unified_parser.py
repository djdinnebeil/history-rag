import sys
from pathlib import Path

# Allow imports when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from components.text_parsers.book_parser import parse_book
from components.text_parsers.journal_parser import parse_journal_article
from components.text_parsers.newspaper_parser import parse_newspaper_article
from components.text_parsers.report_parser import parse_report
from components.text_parsers.web_article_parser import parse_web_article
from components.text_parsers.unsorted_parser import parse_unsorted
from components.text_parsers.misc_parser import parse_misc

# Dispatch table
DISPATCH = {
    "books": parse_book,
    "journals": parse_journal_article,
    "newspapers": parse_newspaper_article,
    "reports": parse_report,
    "web_articles": parse_web_article,
    "unsorted": parse_unsorted,
    "misc": parse_misc,
}

def parse_file(file_path: str) -> dict:
    """
    Unified parser that dispatches based on top-level folder.
    Returns a dict with keys: page_content, metadata.
    """
    path = Path(file_path)
    try:
        # Find the documents folder in the path
        documents_index = None
        for i, part in enumerate(path.parts):
            if part == "documents":
                documents_index = i
                break
        
        if documents_index is None:
            raise ValueError(f"Could not find 'documents' folder in path: {file_path}")
        
        # Get the folder type (e.g., "newspapers", "web_articles") from after documents
        if documents_index + 1 >= len(path.parts):
            raise ValueError(f"Unexpected file structure: {file_path}")
        
        folder = path.parts[documents_index + 1]
        
    except IndexError:
        raise ValueError(f"Unexpected file structure: {file_path}")

    parser = DISPATCH.get(folder)
    if not parser:
        raise ValueError(f"Unknown source type: {folder} for file {file_path}")
    return parser(file_path)


if __name__ == "__main__":
    root = Path("amatol")
    all_files = root.rglob("*.txt")

    with open("amatol_parsed.txt", "w", encoding="utf-8") as f:
        for file_path in all_files:
            parsed = parse_file(file_path)
            print("=== File:", file_path, "===", file=f)
            print("Page Content:\n", parsed["page_content"], sep="", file=f)
            print("\nMetadata:", file=f)
            for k, v in parsed["metadata"].items():
                print(f"  {k}: {v}", file=f)
            print(file=f)
