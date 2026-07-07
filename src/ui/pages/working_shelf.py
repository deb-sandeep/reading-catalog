from __future__ import annotations

import datetime

import streamlit as st
from pydantic import ValidationError

from src.pipeline.normalize import (
    normalize_googlebooks_volume,
    normalize_hardcover_book,
    normalize_openlibrary_search_doc,
)
from src.storage.db import promote_to_curated, session_scope, upsert_book
from src.storage.db_models import Book, LibraryStatus
from src.ui.common import (
    get_googlebooks_client,
    get_hardcover_client,
    get_openlibrary_client,
    get_session_factory,
)

st.title("Working Shelf")

session_factory = get_session_factory()

with session_scope(session_factory) as session:
    working_books = (
        session.query(Book)
        .filter(Book.library_status == LibraryStatus.WORKING.value)
        .order_by(Book.title)
        .all()
    )
    book_options = {f"{b.title} — {', '.join(a.name for a in b.authors)}": b.id for b in working_books}

if not book_options:
    st.info("No books on the working shelf yet. Add some from Explore.")
    st.stop()

selected_label = st.selectbox("Pick a book", list(book_options.keys()))
selected_id = book_options[selected_label]

col1, col2 = st.columns(2)
fetch_clicked = col1.button("Fetch rich view", type="primary")
promote_clicked = col2.button("Promote to curated library")

if promote_clicked:
    with session_scope(session_factory) as session:
        book = session.get(Book, selected_id)
        promote_to_curated(session, book)
        promoted_title = book.title
        session.commit()
    st.success(f"Promoted '{promoted_title}' to the curated library.")
    st.rerun()

if fetch_clicked:
    with session_scope(session_factory) as session:
        book = session.get(Book, selected_id)
        isbn13 = book.isbn13
        title = book.title
        author = book.authors[0].name if book.authors else None

    now = datetime.datetime.now(datetime.timezone.utc)
    raw_results: dict[str, dict | None] = {}

    hardcover = get_hardcover_client()
    if hardcover is None:
        st.warning("Hardcover not configured — skipped.")
    else:
        with st.spinner("Fetching from Hardcover..."):
            raw_results["hardcover"] = (
                hardcover.find_by_isbn13(isbn13) if isbn13 else hardcover.find_by_title_author(title, author)
            )

    googlebooks = get_googlebooks_client()
    if googlebooks is None:
        st.warning("Google Books not configured — skipped.")
    else:
        with st.spinner("Fetching from Google Books..."):
            raw_results["googlebooks"] = (
                googlebooks.find_by_isbn13(isbn13) if isbn13 else googlebooks.find_by_title_author(title, author)
            )

    openlibrary = get_openlibrary_client()
    with st.spinner("Fetching from Open Library..."):
        raw_results["openlibrary"] = openlibrary.search(isbn=isbn13, title=title, author=author)

    normalizers = {
        "hardcover": normalize_hardcover_book,
        "googlebooks": normalize_googlebooks_volume,
        "openlibrary": normalize_openlibrary_search_doc,
    }
    backfilled_sources = []
    with session_scope(session_factory) as session:
        for source_name, raw in raw_results.items():
            if not raw:
                continue
            try:
                record = normalizers[source_name](raw, now)
            except (ValidationError, KeyError) as e:
                st.warning(f"Couldn't normalize {source_name} result: {e}")
                continue
            upsert_book(session, record)
            backfilled_sources.append(source_name)
        session.commit()

    st.session_state["rich_view_raw"] = raw_results
    if backfilled_sources:
        st.success(f"Backfilled data from: {', '.join(backfilled_sources)}")

raw_results = st.session_state.get("rich_view_raw")
if raw_results:
    tabs = st.tabs(["Hardcover", "Google Books", "Open Library"])
    for tab, source_name in zip(tabs, ["hardcover", "googlebooks", "openlibrary"]):
        with tab:
            raw = raw_results.get(source_name)
            if raw:
                st.json(raw)
            else:
                st.caption("No data from this source.")
