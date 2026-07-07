from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Reading Catalog", layout="wide")

pages = [
    st.Page("ui/pages/explore.py", title="Explore", icon="🔍"),
    st.Page("ui/pages/working_shelf.py", title="Working Shelf", icon="📚"),
    st.Page("ui/pages/curated_library.py", title="Curated Library", icon="✅"),
]
st.navigation(pages).run()
