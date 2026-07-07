from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class OpenLibraryClient:
    """Thin REST client over Open Library's public, no-auth API.

    Single httpx.Client reused across calls (opened/closed as a context manager),
    a flat sleep between requests as a good-citizen crawl delay, and graceful
    404 handling on per-work/per-edition lookups (missing data is expected, not
    an error - see spec's normalize step).
    """

    def __init__(
        self,
        base_url: str,
        user_agent: str,
        timeout_seconds: float = 10,
        max_retries: int = 3,
        request_delay_seconds: float = 0.5,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_delay_seconds = request_delay_seconds
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"User-Agent": user_agent},
            timeout=timeout_seconds,
        )

    def __enter__(self) -> "OpenLibraryClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._client.close()

    def _get(self, path: str) -> httpx.Response:
        """404s are returned as-is (not retried, not raised) since a missing
        work/edition is an expected outcome the caller handles explicitly.
        Any other error status or network failure is retried."""

        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        def _do_get() -> httpx.Response:
            response = self._client.get(path)
            if response.status_code != 404:
                response.raise_for_status()
            return response

        time.sleep(self._request_delay_seconds)
        return _do_get()

    def fetch_subject(self, subject: str, limit: int, offset: int = 0) -> dict:
        response = self._get(f"/subjects/{subject}.json?limit={limit}&offset={offset}")
        return response.json()

    def fetch_work(self, work_key: str) -> dict | None:
        response = self._get(f"{work_key}.json")
        if response.status_code == 404:
            return None
        return response.json()

    def fetch_edition(self, edition_key: str) -> dict | None:
        response = self._get(f"/books/{edition_key}.json")
        if response.status_code == 404:
            return None
        return response.json()

    def search(
        self,
        isbn: str | None = None,
        title: str | None = None,
        author: str | None = None,
        limit: int = 1,
    ) -> dict | None:
        """General /search.json lookup by isbn13 and/or title/author - used
        only by the working-shelf rich-view single-book lookup, distinct from
        the subject-browse discovery flow. At least one of isbn/title must be
        given. Returns the first matching doc, or None."""
        params = {k: v for k, v in {"isbn": isbn, "title": title, "author": author}.items() if v}
        params["limit"] = limit
        response = self._get(f"/search.json?{urlencode(params)}")
        docs = response.json().get("docs") or []
        return docs[0] if docs else None
