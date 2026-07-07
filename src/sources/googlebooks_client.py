from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

"""Google Books REST client. Role per spec: description text, categories,
secondary rating cross-check. Free tier is ~1000 requests/day, no published
hard rate limit - a modest flat delay is used for good-citizen consistency
with the other two clients."""


class GoogleBooksClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 10,
        max_retries: int = 3,
        request_delay_seconds: float = 0.2,
    ) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._request_delay_seconds = request_delay_seconds
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    def __enter__(self) -> "GoogleBooksClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._client.close()

    def _get(self, path: str, params: dict) -> httpx.Response:
        params = {**params, "key": self._api_key}

        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        def _do_get() -> httpx.Response:
            response = self._client.get(f"{path}?{urlencode(params)}")
            if response.status_code != 404:
                response.raise_for_status()
            return response

        time.sleep(self._request_delay_seconds)
        return _do_get()

    def search_volumes(self, query: str, max_results: int = 20) -> dict:
        response = self._get("/volumes", {"q": query, "maxResults": max_results})
        if response.status_code == 404:
            return {}
        return response.json()

    def find_by_isbn13(self, isbn13: str) -> dict | None:
        result = self.search_volumes(f"isbn:{isbn13}", max_results=1)
        items = result.get("items") or []
        return items[0] if items else None

    def find_by_title_author(self, title: str, author: str | None = None) -> dict | None:
        query = f"intitle:{title}"
        if author:
            query += f"+inauthor:{author}"
        result = self.search_volumes(query, max_results=1)
        items = result.get("items") or []
        return items[0] if items else None
