import streamlit as st
from .book_uploader import render_books_uploader
from .journal_uploader import render_journals_uploader
from .newspaper_uploader import render_newspapers_uploader
from .report_uploader import render_reports_uploader
from .web_article_uploader import render_web_articles_uploader
from .unsorted_uploader import render_unsorted_uploader
from .misc_uploader import render_misc_uploader

UPLOADERS = {
    "books": render_books_uploader,
    "journals": render_journals_uploader,
    "newspapers": render_newspapers_uploader,
    "reports": render_reports_uploader,
    "web_articles": render_web_articles_uploader,
    "unsorted": render_unsorted_uploader,
    "misc": render_misc_uploader
}

def render_uploader(proj_dir, con):
    st.header("Upload Documents")
    doc_type = st.selectbox("Select document type", list(UPLOADERS.keys()), index=None)
    if doc_type is None:
        return
    uploader = UPLOADERS[doc_type]
    uploader(proj_dir, con)