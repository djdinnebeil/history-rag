import streamlit as st
from pathlib import Path
from core.database import file_sha256_from_buffer, insert_document, document_exists
from components.text_parsers.unified_parser import parse_file

def render_misc_uploader(proj_dir: Path, con):
    st.subheader("📁 Upload Misc Documents")
    misc_dir = proj_dir / "documents" / "misc"
    misc_dir.mkdir(parents=True, exist_ok=True)

    st.info("📋 Upload any miscellaneous document that doesn't fit the other categories. The filename will be used as the document title.")

    # Upload misc files
    uploaded_files = st.file_uploader(
        "Upload misc document(s)",
        accept_multiple_files=True,
        type=["txt"]
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Compute hash first
            file_bytes = uploaded_file.getbuffer()
            h = file_sha256_from_buffer(file_bytes)

            if document_exists(con, h):
                st.warning(f"⚠️ {uploaded_file.name} already uploaded (duplicate). Skipping.")
                continue

            # Save file
            save_path = misc_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.success(f"✅ Saved {uploaded_file.name} to {misc_dir}")

            # Insert into DB
            rel_path = f"misc/{uploaded_file.name}"
            parsed = parse_file(str(save_path))
            insert_document(con, rel_path, parsed, h, num_chunks=0)
            con.commit()
            st.info(f"📥 Added {uploaded_file.name} to DB (status: pending)")
