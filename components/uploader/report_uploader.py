import streamlit as st
import json
from pathlib import Path
from core.database import file_sha256_from_buffer, insert_document, document_exists
from components.text_parsers.unified_parser import parse_file

def render_reports_uploader(proj_dir: Path, con):
    st.subheader("📑 Upload Reports")
    reports_dir = proj_dir / "documents" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: metadata.json ---
    meta_file = reports_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"reports": {}}

    # --- Step 2: Upload report files ---
    uploaded_files = st.file_uploader(
        "Upload report file(s)",
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
            save_path = reports_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.success(f"✅ Saved {uploaded_file.name} to {reports_dir}")

            # --- Parse filename for metadata ---
            fname = uploaded_file.name.replace(".txt", "")
            parts = fname.split("__")
            if len(parts) != 4:
                st.error(f"❌ Unexpected filename format: {uploaded_file.name}")
                continue

            description, pages, section, publication_year = parts
            description_clean = description.replace("-", " ").title()

            # Load existing metadata entry if available
            entry = metadata["reports"].get(fname, {})

            # Prompt for title (default = existing title or fallback = description slug)
            title_input = st.text_input(
                f"Title for {uploaded_file.name}",
                value=entry.get("title", description_clean),
                key=f"title_{fname}"
            )

            # Save metadata button
            if st.button(f"Save metadata for {uploaded_file.name}", key=f"save_{fname}"):
                final_title = title_input.strip() if title_input.strip() else description_clean

                metadata["reports"][fname] = {
                    "title": final_title
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                st.success(f"📑 Metadata saved for {uploaded_file.name} (title: {final_title})")

                # --- Insert into DB ---
                rel_path = f"reports/{uploaded_file.name}"
                parsed = parse_file(str(save_path))
                insert_document(con, rel_path, parsed, h, num_chunks=0)
                con.commit()
                st.info(f"📥 Added {uploaded_file.name} to DB (status: pending)")
