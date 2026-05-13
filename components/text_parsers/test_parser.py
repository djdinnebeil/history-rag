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
    path = Path(file_path)
    try:
        folder = path.parts[1]  # e.g., "journals" from "amatol/journals/.../file.txt"
    except IndexError:
        raise ValueError(f"Unexpected file structure: {file_path}")

    parser = DISPATCH.get(folder)
    if not parser:
        raise ValueError(f"Unknown source type: {folder} for file {file_path}")
    return parser(file_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <folder_type> [file_path]")
        sys.exit(1)

    folder_type = sys.argv[1]

    if folder_type not in DISPATCH:
        print(f"Unknown folder type: {folder_type}. Options: {list(DISPATCH.keys())}")
        sys.exit(1)

    parser = DISPATCH[folder_type]

    if len(sys.argv) == 3:  # process a single file
        file_path = sys.argv[2]
        parsed = parser(file_path)
        print("\n=== File:", file_path, "===")
        print("Page Content:\n", parsed["page_content"])
        print("\nMetadata:")
        for k, v in parsed["metadata"].items():
            print(f"  {k}: {v}")
    else:  # process all files in the given folder
        root = Path("amatol") / folder_type
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