import streamlit as st
import json
from pathlib import Path
from core.database import file_sha256_from_buffer, insert_document, document_exists
from components.text_parsers.unified_parser import parse_file

def slug_to_title(slug: str) -> str:
    if not slug:
        return "Untitled"
    title = slug.replace("_", " ").replace("-", " ").title()
    return title.replace(" Nj", " NJ")

def render_web_articles_uploader(proj_dir: Path, con):
    st.subheader("🌐 Upload Web Articles")
    web_dir = proj_dir / "documents" / "web_articles"
    web_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: metadata.json ---
    meta_file = web_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"web_articles": {}}

    # --- Step 2: Upload web article files ---
    uploaded_files = st.file_uploader(
        "Upload web article file(s)",
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
            save_path = web_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.success(f"✅ Saved {uploaded_file.name} to {web_dir}")

            # --- Parse filename ---
            fname = uploaded_file.name.replace(".txt", "")
            parts = fname.split("__")
            if len(parts) < 3:
                st.error(f"❌ Unexpected filename format: {uploaded_file.name}")
                continue

            date_str, source_id, slug = parts[0], parts[1], parts[2]
            source_fallback = source_id.replace("-", " ").title()
            title_fallback = slug_to_title(slug)

            # Load existing entry if available
            entry = metadata["web_articles"].get(source_id, {})

            # Prompt for source and title
            source = st.text_input(
                f"Source name for {source_id}",
                value=entry.get("source", source_fallback),
                key=f"source_{source_id}"
            )
            title = st.text_input(
                f"Title for {uploaded_file.name}",
                value=entry.get("title", title_fallback),
                key=f"title_{fname}"
            )

            # Save metadata button
            if st.button(f"Save metadata for {uploaded_file.name}", key=f"save_{fname}"):
                final_source = source.strip() if source.strip() else source_fallback
                final_title = title.strip() if title.strip() else title_fallback

                metadata["web_articles"][source_id] = {
                    "source": final_source,
                    "title": final_title
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                st.success(f"📑 Metadata saved for {uploaded_file.name} (title: {final_title})")

                # --- Insert into DB ---
                rel_path = f"web_articles/{uploaded_file.name}"
                parsed = parse_file(str(save_path))
                insert_document(con, rel_path, parsed, h, num_chunks=0)
                con.commit()
                st.info(f"📥 Added {uploaded_file.name} to DB (status: pending)")
