from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import joinedload

from src.config import load_config
from src.scripts.fetch_openlibrary_fiction import run as fetch_openlibrary_books
from src.storage.db import init_db, make_engine, make_session_factory, session_scope
from src.storage.db_models import Author, Book, Genre

st.set_page_config(page_title="Reading Catalog", layout="wide")

config = load_config("config.yaml")
engine = make_engine(config.app.db_url)
init_db(engine)
session_factory = make_session_factory(engine)

st.title("Reading Catalog")

with st.sidebar:
    st.header("Add books")
    st.caption("Pulls from Open Library - no rating data yet, that comes from a later enrichment step.")
    subject = st.text_input("Subject", value="fiction")
    fetch_limit = st.number_input("How many", min_value=1, max_value=200, value=20)
    if st.button("Fetch books"):
        with st.spinner(f"Fetching '{subject}' from Open Library..."):
            summary = fetch_openlibrary_books(subject=subject, limit=fetch_limit, config_path="config.yaml")
        st.success(f"Added {summary['created']} new, updated {summary['updated']} existing.")
        st.rerun()

    st.divider()
    st.header("Filters")

    with session_scope(session_factory) as session:
        all_genres = sorted({g.name for g in session.query(Genre).all()})
        all_authors = sorted({a.name for a in session.query(Author).all()})

    selected_genres = st.multiselect("Genre", all_genres)
    selected_authors = st.multiselect("Author", all_authors)
    min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.1)

with session_scope(session_factory) as session:
    books = (
        session.query(Book)
        .options(joinedload(Book.authors), joinedload(Book.genres))
        .order_by(Book.title)
        .all()
    )

    rows = []
    for book in books:
        book_genres = {g.name for g in book.genres}
        book_authors = {a.name for a in book.authors}

        if selected_genres and not (book_genres & set(selected_genres)):
            continue
        if selected_authors and not (book_authors & set(selected_authors)):
            continue
        if min_rating > 0 and (book.average_rating is None or book.average_rating < min_rating):
            continue

        rows.append(
            {
                "Title": book.title,
                "Authors": ", ".join(sorted(book_authors)),
                "Genres": ", ".join(sorted(book_genres)),
                "Rating": book.average_rating,
                "Ratings Count": book.ratings_count,
                "ISBN13": book.isbn13,
                "Publish Year": book.publish_year,
            }
        )

if not rows:
    st.info("No books match the current filters. Try widening them, or fetch more books from the sidebar.")
else:
    st.write(f"{len(rows)} books")
    st.dataframe(rows, width="stretch", hide_index=True)
