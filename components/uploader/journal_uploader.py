import streamlit as st
import json
from pathlib import Path
from core.database import file_sha256_from_buffer, insert_document, document_exists
from components.text_parsers.unified_parser import parse_file

def render_journals_uploader(proj_dir: Path, con):
    st.subheader("📰 Upload a Journal Article")
    journals_dir = proj_dir / "documents" / "journals"
    journals_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: load or initialize metadata.json
    meta_file = journals_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"journals": {}}

    # Step 2: Upload journal files
    uploaded_files = st.file_uploader(
        "Upload journal article(s)",
        accept_multiple_files=True,
        type=["txt"]
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Compute hash BEFORE saving to avoid duplicates
            file_bytes = uploaded_file.getbuffer()
            h = file_sha256_from_buffer(file_bytes)

            if document_exists(con, h):
                st.warning(f"⚠️ {uploaded_file.name} has already been uploaded (duplicate). Skipping.")
                continue

            # Save file only if unique
            save_path = journals_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.success(f"✅ Saved {uploaded_file.name} to {journals_dir}")

            key = uploaded_file.name.replace(".txt", "")
            entry = metadata["journals"].get(key, {})

            # Extract pages from filename (third part like p45-54)
            parts = key.split("__")
            pages = None
            if len(parts) >= 3 and parts[2].startswith("p"):
                pages = parts[2].lstrip("p").replace("-", "–")

            # Prompt user for metadata fields
            st.write(f"### Metadata for {uploaded_file.name}")
            journal = st.text_input("Journal name", value=entry.get("journal", ""), key=f"journal_{key}")
            volume = st.text_input("Volume", value=entry.get("volume", ""), key=f"volume_{key}")
            issue = st.text_input("Issue", value=entry.get("issue", ""), key=f"issue_{key}")
            season = st.text_input("Season", value=entry.get("season", ""), key=f"season_{key}")
            title = st.text_input("Article title", value=entry.get("title", ""), key=f"title_{key}")

            # Build citation string if everything is filled in
            citation = (
                f"{journal} {volume}.{issue}, {season}, pp. {pages}, \"{title}\""
                if all([journal, volume, issue, season, pages, title]) else ""
            )

            # Save metadata when confirmed
            if st.button(f"Save metadata for {uploaded_file.name}", key=f"save_{key}"):
                metadata["journals"][key] = {
                    "journal": journal,
                    "volume": volume,
                    "issue": issue,
                    "season": season,
                    "pages": pages,
                    "title": title,
                    "citation": citation
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                st.success(f"📑 Metadata updated for {uploaded_file.name}")

                # --- Insert into DB ---
                rel_path = f"journals/{uploaded_file.name}"
                parsed = parse_file(str(save_path))
                insert_document(con, rel_path, parsed, h, num_chunks=0)
                con.commit()
                st.info(f"📥 Added {uploaded_file.name} to DB (status: pending)")
