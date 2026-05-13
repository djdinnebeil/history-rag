import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Union

# Global, must be set by set_project_db()
DB_PATH: Path | None = None
# Import settings from config
from config import PROJECTS_DIR

def file_sha256_from_buffer(buffer: Union[bytes, bytearray]) -> str:
    h = hashlib.sha256()
    h.update(buffer)
    return h.hexdigest()

def file_sha256(path: Path) -> str:
    """Compute SHA256 hash for file content."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def set_project_db(project_name: str) -> None:
    """
    Set the DB_PATH based on project_name.
    Database will be stored at: projects/{project_name}/{project_name}.sqlite
    """
    global DB_PATH
    proj_dir = PROJECTS_DIR / project_name
    proj_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH = proj_dir / f"{project_name}.sqlite"

def ensure_db() -> sqlite3.Connection:
    """Ensure the database exists and has the correct schema."""
    if DB_PATH is None:
        raise RuntimeError("DB_PATH is not set. Call set_project_db() first.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        path         TEXT,
        citation     TEXT,
        source_type  TEXT,
        source_id    TEXT,
        date         TEXT,
        num_chunks   INTEGER,
        content_hash TEXT UNIQUE,
        status       TEXT DEFAULT 'pending',   -- NEW FIELD
        added_at     DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Add chat_history table
    con.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        question     TEXT NOT NULL,
        answer       TEXT NOT NULL,
        mode         TEXT NOT NULL,  -- 'Standard' or 'Advanced'
        citations    TEXT,           -- JSON array of citations
        web_sources  TEXT,           -- JSON array of web sources (for advanced mode)
        tools_used   TEXT,           -- JSON array of tools used
        timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
        project_name TEXT NOT NULL   -- For potential future multi-project queries
    )
    """)

    return con


def document_exists(con: sqlite3.Connection, content_hash: str) -> bool:
    cur = con.execute("SELECT 1 FROM documents WHERE content_hash = ?", (content_hash,))
    return cur.fetchone() is not None

def insert_document(con: sqlite3.Connection, path: Path, parsed: dict, content_hash: str, num_chunks: int) -> None:
    """Insert a new document record with its metadata + chunk count."""
    md = parsed['metadata']
    try:
        con.execute("""
        INSERT INTO documents (path, citation, source_type, source_id, date, content_hash, num_chunks, status, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(path),
            md.get('citation'),
            md.get('source_type'),
            md.get('source_id'),
            md.get('date'),
            content_hash,
            num_chunks,
            'pending',
            datetime.utcnow().isoformat()
        ))
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: documents.content_hash" in str(e):
            # Check if this is a duplicate path or content hash
            existing = con.execute("SELECT path, content_hash FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
            if existing:
                raise sqlite3.IntegrityError(f"Document with content hash {content_hash} already exists in database. Path: {existing[0]}, Attempted path: {path}")
        raise

def update_document_status(con, content_hash: str, num_chunks: int, status: str = "embedded") -> None:
    """Update chunk count and status for a document after processing."""
    con.execute(
        "UPDATE documents SET num_chunks=?, status=? WHERE content_hash=?",
        (num_chunks, status, content_hash),
    )
    con.commit()


def delete_document(con, content_hash: str) -> None:
    """Delete a document row by its content hash."""
    con.execute("DELETE FROM documents WHERE content_hash = ?", (content_hash,))
    con.commit()

def list_documents(con):
    """Return summary list of documents."""
    cur = con.execute(
        "SELECT path, citation, source_id, date, num_chunks, added_at "
        "FROM documents ORDER BY added_at DESC"
    )
    return cur.fetchall()

def list_all_documents(con):
    """Return all documents with full metadata."""
    cur = con.execute("SELECT * FROM documents ORDER BY added_at DESC")
    return cur.fetchall()

def list_documents_by_status(con, status: str):
    """Return all documents with the given status."""
    return con.execute(
        "SELECT * FROM documents WHERE status=? ORDER BY added_at DESC", 
        (status,)
    ).fetchall()


# Chat History Functions
def insert_chat_entry(con, question: str, answer: str, mode: str, citations: list = None, 
                     web_sources: list = None, tools_used: list = None, project_name: str = None) -> None:
    """Insert a new chat entry into the database."""
    import json
    
    # Convert lists to JSON strings for storage
    citations_json = json.dumps(citations) if citations else None
    web_sources_json = json.dumps(web_sources) if web_sources else None
    tools_used_json = json.dumps(tools_used) if tools_used else None
    
    con.execute("""
    INSERT INTO chat_history (question, answer, mode, citations, web_sources, tools_used, project_name, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question,
        answer,
        mode,
        citations_json,
        web_sources_json,
        tools_used_json,
        project_name,
        datetime.utcnow().isoformat()
    ))
    con.commit()


def get_chat_history(con, project_name: str = None, limit: int = None):
    """Retrieve chat history, optionally filtered by project and limited by count."""
    if project_name:
        if limit:
            cur = con.execute(
                "SELECT * FROM chat_history WHERE project_name = ? ORDER BY timestamp DESC LIMIT ?",
                (project_name, limit)
            )
        else:
            cur = con.execute(
                "SELECT * FROM chat_history WHERE project_name = ? ORDER BY timestamp DESC",
                (project_name,)
            )
    else:
        if limit:
            cur = con.execute(
                "SELECT * FROM chat_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        else:
            cur = con.execute(
                "SELECT * FROM chat_history ORDER BY timestamp DESC"
            )
    
    return cur.fetchall()


def delete_chat_entry(con, chat_id: int) -> None:
    """Delete a specific chat entry by ID."""
    con.execute("DELETE FROM chat_history WHERE id = ?", (chat_id,))
    con.commit()


def clear_chat_history(con, project_name: str = None) -> None:
    """Clear all chat history, optionally for a specific project."""
    if project_name:
        con.execute("DELETE FROM chat_history WHERE project_name = ?", (project_name,))
    else:
        con.execute("DELETE FROM chat_history")
    con.commit()


def get_chat_history_count(con, project_name: str = None) -> int:
    """Get the count of chat history entries, optionally for a specific project."""
    if project_name:
        cur = con.execute("SELECT COUNT(*) FROM chat_history WHERE project_name = ?", (project_name,))
    else:
        cur = con.execute("SELECT COUNT(*) FROM chat_history")
    
    return cur.fetchone()[0]


if __name__ == "__main__":
    set_project_db("demo_project")
    con = ensure_db()
    print(list_all_documents(con))
