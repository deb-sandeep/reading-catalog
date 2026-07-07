#!/bin/bash
# Launches the Reading Catalog app. Just run: ./run_app.sh
set -e
cd "$(dirname "$0")"
./.venv/bin/streamlit run src/catalog_ui.py
