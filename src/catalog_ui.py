from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Reading Catalog", layout="wide")

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 190px !important;
        min-width: 190px !important;
    }
    div[data-testid="stMainBlockContainer"] {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMainBlockContainer"] div[data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    h1 {
        padding-top: 0rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pages = [
    st.Page("ui/pages/explore.py", title="Explore", icon="🔍"),
    st.Page("ui/pages/working_shelf.py", title="Working Shelf", icon="📚"),
    st.Page("ui/pages/curated_library.py", title="Curated Library", icon="✅"),
]
st.navigation(pages).run()
