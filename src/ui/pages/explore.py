from __future__ import annotations

import datetime

import streamlit as st

from src.pipeline.normalize import _extract_hardcover_authors, _extract_hardcover_genres, normalize_hardcover_book
from src.storage.db import import_to_working_shelf, session_scope
from src.ui.common import get_config, get_hardcover_client, get_session_factory

st.title("Explore Public Libraries")

hardcover = get_hardcover_client()
if hardcover is None:
    st.error("Hardcover is not configured (missing HARDCOVER_API_TOKEN). Explore requires Hardcover.")
    st.stop()

config = get_config()

category = st.radio("Search by", ["Title", "Author", "Genre"], horizontal=True)

min_rating = None
min_ratings_count = None
if category == "Genre":
    query = st.text_input("Genre", placeholder="e.g. Science Fiction")
    col1, col2 = st.columns(2)
    with col1:
        min_rating = st.slider("Minimum rating", 0.0, 5.0, config.filters.min_rating, 0.1)
    with col2:
        min_ratings_count = st.number_input(
            "Minimum number of ratings", min_value=0, value=config.filters.reader_absolute_floor, step=100
        )
else:
    query = st.text_input(category)

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Enter a search term first.")
    else:
        with st.spinner("Searching Hardcover..."):
            if category == "Genre":
                candidates = hardcover.fetch_top_rated_books(
                    min_rating=min_rating, min_ratings_count=int(min_ratings_count), limit=100
                )
                results = [
                    c
                    for c in candidates
                    if any(query.casefold() in g.casefold() for g in _extract_hardcover_genres(c))
                ]
            else:
                results = hardcover.search_books(query, per_page=25)
        st.session_state["explore_results"] = results
        st.session_state["explore_selected"] = set()
        if not results:
            st.info("No matches - try broadening your search.")

results = st.session_state.get("explore_results", [])

if results:
    st.write(f"{len(results)} result(s)")
    selected = st.session_state.setdefault("explore_selected", set())

    for i, raw in enumerate(results):
        genres = _extract_hardcover_genres(raw)
        cols = st.columns([0.06, 0.94])
        with cols[0]:
            checked = st.checkbox(
                "Select", value=i in selected, key=f"explore_check_{i}", label_visibility="collapsed"
            )
            if checked:
                selected.add(i)
            else:
                selected.discard(i)
        with cols[1]:
            authors = ", ".join(_extract_hardcover_authors(raw))
            st.markdown(f"**{raw.get('title', '(untitled)')}** — {authors}")

            rating = raw.get("rating")
            caption_parts = []
            if rating is not None:
                caption_parts.append(f"Rating: {rating:.2f} ({raw.get('ratings_count')} ratings)")
            else:
                caption_parts.append("No rating data")
            if genres:
                caption_parts.append(f"Genres: {', '.join(genres[:5])}")
            st.caption(" | ".join(caption_parts))

            description = raw.get("description")
            if description:
                st.caption(description[:280] + ("..." if len(description) > 280 else ""))
        st.divider()

    if st.button(f"Import {len(selected)} selected to working shelf", disabled=not selected):
        session_factory = get_session_factory()
        now = datetime.datetime.now(datetime.timezone.utc)
        created_count = 0
        with session_scope(session_factory) as session:
            for i in selected:
                record = normalize_hardcover_book(results[i], now)
                _, created = import_to_working_shelf(session, record)
                if created:
                    created_count += 1
            session.commit()
        st.success(f"Imported {created_count} new book(s) to the working shelf.")
        st.session_state["explore_selected"] = set()
        st.rerun()
else:
    st.info("No results yet — try a search above.")
