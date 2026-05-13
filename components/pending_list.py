import streamlit as st
from core import list_documents_by_status

COLUMNS = [
    "id", "path", "citation", "source_type", "source_id",
    "date", "num_chunks", "content_hash", "status", "added_at"
]

def render_pending_list(con):
    if st.button("View Pending Documents"):
        rows = list_documents_by_status(con, "pending")
        if rows:
            st.write("### Pending Documents")
            for row in rows:
                record = dict(zip(COLUMNS, row))
                st.json(record)  # shows as expandable JSON-like dict
        else:
            st.info("No pending documents.")
