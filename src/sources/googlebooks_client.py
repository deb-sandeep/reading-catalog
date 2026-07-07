from __future__ import annotations

"""Stub for the Google Books REST client - deferred until GOOGLE_BOOKS_API_KEY
is available. Role per spec: description text, categories, secondary rating
cross-check. Free tier is ~1000 requests/day.
"""


class GoogleBooksClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def search_volumes(self, query: str, max_results: int = 20) -> dict:
        raise NotImplementedError("Google Books client is deferred until GOOGLE_BOOKS_API_KEY is available")
