from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import sessionmaker

from src.config import Config, load_config
from src.sources.googlebooks_client import GoogleBooksClient
from src.sources.hardcover_client import HardcoverClient
from src.sources.openlibrary_client import OpenLibraryClient
from src.storage.db import init_db, make_engine, make_session_factory

CONFIG_PATH = "config.yaml"


@st.cache_resource
def get_config() -> Config:
    return load_config(CONFIG_PATH)


@st.cache_resource
def get_session_factory() -> sessionmaker:
    config = get_config()
    engine = make_engine(config.app.db_url)
    init_db(engine)
    return make_session_factory(engine)


@st.cache_resource
def get_openlibrary_client() -> OpenLibraryClient:
    c = get_config().sources.openlibrary
    return OpenLibraryClient(
        base_url=c.base_url,
        user_agent=c.user_agent,
        timeout_seconds=c.timeout_seconds,
        max_retries=c.max_retries,
        request_delay_seconds=c.request_delay_seconds,
    )


@st.cache_resource
def get_hardcover_client() -> HardcoverClient | None:
    c = get_config().sources.hardcover
    if not c.enabled or not c.api_token:
        return None
    return HardcoverClient(
        base_url=c.base_url,
        api_token=c.api_token,
        timeout_seconds=c.timeout_seconds,
        max_retries=c.max_retries,
        request_delay_seconds=c.request_delay_seconds,
    )


@st.cache_resource
def get_googlebooks_client() -> GoogleBooksClient | None:
    c = get_config().sources.googlebooks
    if not c.enabled or not c.api_key:
        return None
    return GoogleBooksClient(
        base_url=c.base_url,
        api_key=c.api_key,
        timeout_seconds=c.timeout_seconds,
        max_retries=c.max_retries,
        request_delay_seconds=c.request_delay_seconds,
    )
