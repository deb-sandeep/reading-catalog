from __future__ import annotations

import pandas as pd
import streamlit as st

from src.pipeline.curated import CuratedBookUpdate, apply_curated_updates
from src.storage.db import session_scope
from src.storage.db_models import Book, LibraryStatus
from src.ui.common import get_session_factory

st.title("Curated Library")

session_factory = get_session_factory()

with session_scope(session_factory) as session:
    curated_books = (
        session.query(Book)
        .filter(Book.library_status == LibraryStatus.CURATED.value)
        .order_by(Book.reading_sequence.asc().nullslast(), Book.title)
        .all()
    )
    rows = [
        {
            "book_id": b.id,
            "Title": b.title,
            "Authors": ", ".join(a.name for a in b.authors),
            "Average Rating": b.average_rating,
            "My Rating": b.my_rating,
            "Have eBook": b.have_ebook,
            "Read": b.is_read,
            "Reading Sequence": b.reading_sequence,
        }
        for b in curated_books
    ]

if not rows:
    st.info("No books in the curated library yet. Promote some from the Working Shelf.")
    st.stop()

df = pd.DataFrame(rows).set_index("book_id")

edited_df = st.data_editor(
    df,
    column_config={
        "Title": st.column_config.TextColumn(disabled=True),
        "Authors": st.column_config.TextColumn(disabled=True),
        "Average Rating": st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "My Rating": st.column_config.NumberColumn(min_value=0.0, max_value=5.0, step=0.5),
        "Have eBook": st.column_config.CheckboxColumn(),
        "Read": st.column_config.CheckboxColumn(),
        "Reading Sequence": st.column_config.NumberColumn(min_value=1, step=1),
    },
    hide_index=True,
    width="stretch",
    key="curated_editor",
)

if st.button("Save changes", type="primary"):
    updates = [
        CuratedBookUpdate(
            book_id=book_id,
            have_ebook=bool(row["Have eBook"]),
            is_read=bool(row["Read"]),
            reading_sequence=int(row["Reading Sequence"]) if pd.notna(row["Reading Sequence"]) else None,
            my_rating=float(row["My Rating"]) if pd.notna(row["My Rating"]) else None,
        )
        for book_id, row in edited_df.iterrows()
    ]
    with session_scope(session_factory) as session:
        apply_curated_updates(session, updates)
        session.commit()
    st.success("Saved.")
    st.rerun()
