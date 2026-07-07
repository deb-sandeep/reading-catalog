from __future__ import annotations

import datetime
from urllib.parse import quote

import streamlit as st

from src.pipeline.normalize import (
    _extract_hardcover_authors,
    _extract_hardcover_genres,
    _extract_hardcover_isbn13,
    normalize_hardcover_book,
)
from src.storage.db import import_to_working_shelf, session_scope
from src.ui.common import get_config, get_hardcover_client, get_session_factory

PAGE_SIZE = 25
GENRE_POOL_SIZE = 200  # one Hasura call, cheap
SEARCH_POOL_SIZE = 100  # Hardcover's search API hard-caps per_page at 25,
# so building this pool costs 4 sequential calls - kept smaller than the
# genre pool for that reason

st.title("Explore Public Libraries")

hardcover = get_hardcover_client()
if hardcover is None:
    st.error("Hardcover is not configured (missing HARDCOVER_API_TOKEN). Explore requires Hardcover.")
    st.stop()

config = get_config()


def _result_key(raw: dict) -> str:
    if raw.get("id") is not None:
        return str(raw["id"])
    return raw.get("slug") or raw["title"]


def _hardcover_url(raw: dict) -> str | None:
    slug = raw.get("slug")
    return f"https://hardcover.app/books/{slug}" if slug else None


def _goodreads_search_url(raw: dict) -> str:
    isbn13 = _extract_hardcover_isbn13(raw)
    authors = _extract_hardcover_authors(raw)
    query = isbn13 or f"{raw.get('title', '')} {authors[0] if authors else ''}"
    return f"https://www.goodreads.com/search?q={quote(query.strip())}"


def _passes_rating_filter(raw: dict, min_rating: float, min_ratings_count: int) -> bool:
    rating = raw.get("rating")
    ratings_count = raw.get("ratings_count") or 0
    if min_rating > 0 and (rating is None or rating < min_rating):
        return False
    if min_ratings_count > 0 and ratings_count < min_ratings_count:
        return False
    return True


def _fetch_search_pool(query: str) -> list[dict]:
    """Hardcover's search() hard-caps per_page at 25 (confirmed live - asking
    for more just silently returns 25), so building a larger candidate pool
    means looping over pages ourselves."""
    all_hits: list[dict] = []
    page_num = 1
    while len(all_hits) < SEARCH_POOL_SIZE:
        hits, _ = hardcover.search_books(query, per_page=25, page=page_num)
        if not hits:
            break
        all_hits.extend(hits)
        if len(hits) < 25:
            break
        page_num += 1
    return all_hits


def _run_search(category: str, query: str, min_rating: float, min_ratings_count: int) -> list[dict]:
    """Fetches a candidate pool and applies all filters client-side, so the
    same rating/ratings-count thresholds apply uniformly regardless of
    category - Hardcover's search() API has no server-side rating filter, so
    Title/Author search is filtered exactly like Genre search."""
    if category == "Genre":
        candidates = hardcover.fetch_top_rated_books(
            min_rating=min_rating, min_ratings_count=min_ratings_count, limit=GENRE_POOL_SIZE
        )
        return [c for c in candidates if any(query.casefold() in g.casefold() for g in _extract_hardcover_genres(c))]
    else:
        hits = _fetch_search_pool(query)
        return [r for r in hits if _passes_rating_filter(r, min_rating, min_ratings_count)]


category = st.radio("Search by", ["Title", "Author", "Genre"], horizontal=True)
query = st.text_input("Genre" if category == "Genre" else category, placeholder="e.g. Science Fiction" if category == "Genre" else "")

col1, col2 = st.columns(2)
with col1:
    min_rating = st.slider("Minimum rating", 0.0, 5.0, config.filters.min_rating, 0.1)
with col2:
    min_ratings_count = st.number_input(
        "Minimum number of ratings", min_value=0, value=config.filters.reader_absolute_floor, step=100
    )

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Enter a search term first.")
    else:
        with st.spinner("Searching Hardcover..."):
            filtered = _run_search(category, query, min_rating, min_ratings_count)
        st.session_state["explore_all_filtered"] = filtered
        st.session_state["explore_total"] = len(filtered)
        st.session_state["explore_page"] = 1
        st.session_state["explore_selected"] = set()
        st.session_state["explore_book_by_key"] = {}
        if not filtered:
            st.info("No matches - try broadening your search.")

all_filtered = st.session_state.get("explore_all_filtered", [])

if all_filtered:
    total = st.session_state.get("explore_total", len(all_filtered))
    page = st.session_state.get("explore_page", 1)
    total_pages = max(1, -(-total // PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    page_results = all_filtered[start : start + PAGE_SIZE]

    selected = st.session_state.setdefault("explore_selected", set())
    book_by_key = st.session_state.setdefault("explore_book_by_key", {})

    for raw in page_results:
        key = _result_key(raw)
        book_by_key[key] = raw
        genres = _extract_hardcover_genres(raw)
        authors = ", ".join(_extract_hardcover_authors(raw))

        cols = st.columns([0.04, 0.66, 0.30])
        with cols[0]:
            checked = st.checkbox(
                "Select", value=key in selected, key=f"explore_check_{key}", label_visibility="collapsed"
            )
            if checked:
                selected.add(key)
            else:
                selected.discard(key)
        with cols[1]:
            rating = raw.get("rating")
            rating_str = f"⭐ {rating:.2f} ({raw.get('ratings_count')})" if rating is not None else "No rating"
            genre_str = f" · {', '.join(genres[:3])}" if genres else ""
            st.markdown(
                f"**{raw.get('title', '(untitled)')}** — {authors}<br>"
                f"<span style='color:gray;font-size:0.85em'>{rating_str}{genre_str}</span>",
                unsafe_allow_html=True,
            )
        with cols[2]:
            links = []
            hc_url = _hardcover_url(raw)
            if hc_url:
                links.append(f"<a href='{hc_url}' target='_blank'>Hardcover</a>")
            links.append(f"<a href='{_goodreads_search_url(raw)}' target='_blank'>Goodreads</a>")
            st.markdown(" · ".join(links), unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin: 0.3rem 0 0.8rem 0; opacity: 0.2;'>",
        unsafe_allow_html=True,
    )

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Previous", disabled=page <= 1, width="stretch"):
            st.session_state["explore_page"] = page - 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<div style='text-align:center; padding-top: 0.4rem;'>Page {page} of {total_pages} &nbsp;·&nbsp; {total} result(s)</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", disabled=page >= total_pages, width="stretch"):
            st.session_state["explore_page"] = page + 1
            st.rerun()

    if st.button(f"Import {len(selected)} selected to working shelf", disabled=not selected):
        session_factory = get_session_factory()
        now = datetime.datetime.now(datetime.timezone.utc)
        created_count = 0
        with session_scope(session_factory) as session:
            for key in selected:
                raw = book_by_key.get(key)
                if raw is None:
                    continue
                record = normalize_hardcover_book(raw, now)
                _, created = import_to_working_shelf(session, record)
                if created:
                    created_count += 1
            session.commit()
        st.success(f"Imported {created_count} new book(s) to the working shelf.")
        st.session_state["explore_selected"] = set()
        st.rerun()
else:
    st.info("No results yet — try a search above.")
