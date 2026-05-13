import streamlit as st
import json
from pathlib import Path
from core.database import file_sha256_from_buffer, insert_document, document_exists
from components.text_parsers.unified_parser import parse_file

def render_newspapers_uploader(proj_dir: Path, con):
    st.subheader("📰 Upload Newspaper Articles")
    newspapers_dir = proj_dir / "documents" / "newspapers"
    newspapers_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: metadata.json ---
    meta_file = newspapers_dir / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {"default": {"attribution_patterns": []}}

    st.write("### Newspaper Attribution Patterns")

    # --- Step 2: Edit default patterns ---
    default_patterns = st.text_area(
        "Default attribution patterns (comma-separated)",
        value=", ".join(metadata.get("default", {}).get("attribution_patterns", [])),
        key="default_patterns"
    )

    if st.button("Save default attribution patterns"):
        metadata["default"] = {
            "attribution_patterns": [p.strip() for p in default_patterns.split(",") if p.strip()]
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        st.success("✅ Default attribution patterns updated")

    # --- Step 3: Edit existing newspapers ---
    st.write("### Edit Existing Newspaper Entries")
    existing_newspapers = [k for k in metadata.keys() if k != "default"]

    if existing_newspapers:
        selected_np = st.selectbox("Select a newspaper to edit", existing_newspapers)

        current_patterns = ", ".join(metadata[selected_np].get("attribution_patterns", []))
        updated_patterns = st.text_area(
            f"Edit patterns for {selected_np} (comma-separated)",
            value=current_patterns,
            key=f"edit_{selected_np}"
        )

        if st.button(f"Save changes for {selected_np}"):
            metadata[selected_np]["attribution_patterns"] = [
                p.strip() for p in updated_patterns.split(",") if p.strip()
            ]
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            st.success(f"✅ Updated patterns for {selected_np}")

    # --- Step 4: Add a new newspaper ---
    st.write("### Add Newspaper-Specific Attribution Patterns")
    newspaper_name = st.text_input("Newspaper name (e.g., Philadelphia Inquirer)", key="new_np_name")
    newspaper_patterns = st.text_area(
        "Attribution patterns for this newspaper (comma-separated)",
        key="new_np_patterns"
    )
    if st.button("Save new newspaper patterns"):
        if newspaper_name:
            metadata[newspaper_name] = {
                "attribution_patterns": [p.strip() for p in newspaper_patterns.split(",") if p.strip()]
            }
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            st.success(f"✅ Patterns saved for {newspaper_name}")

    # --- Step 5: Upload newspaper articles ---
    uploaded_files = st.file_uploader(
        "Upload newspaper article(s)",
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

            # Always group by year
            try:
                year = uploaded_file.name.split("__")[0].split("-")[0]  # e.g. 1919-12-18 → 1919
                save_dir = newspapers_dir / year
                save_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                st.error(f"❌ Could not detect year from filename: {uploaded_file.name}")
                continue

            save_path = save_dir / uploaded_file.name

            # Save file
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.success(f"✅ Saved {uploaded_file.name} to {save_dir}")

            # Insert into DB with year in path
            rel_path = f"newspapers/{year}/{uploaded_file.name}"
            parsed = parse_file(str(save_path))
            insert_document(con, rel_path, parsed, h, num_chunks=0)
            con.commit()
            st.info(f"📥 Added {uploaded_file.name} to DB (status: pending)")
