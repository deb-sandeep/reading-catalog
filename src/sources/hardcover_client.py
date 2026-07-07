from __future__ import annotations

import json
import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

"""Hardcover GraphQL client.

Live-verified query shapes (against a real token, during planning):

- `search(query: String!, query_type: "Book", per_page, page) { results }` -
  Typesense-backed, catalog-wide. Response envelope is
  `data.search.results.hits[].document`, with fields including `id` (string),
  `title`, `rating`, `ratings_count`, `isbns` (list, mixed ISBN-10/13),
  `genres`, `tags`, `release_year`, `description`, `author_names`. Used for
  Author/Title search - default searched fields already cover both.
  NOTE: overriding `fields` to search against `genres`/`tags` instead of the
  default fields does NOT work - it was tested live and Typesense returns
  `results: null`. Do not reintroduce a `fields` override here.

- `books(where: {rating: {_gte}, ratings_count: {_gte}}, order_by: {...},
  limit) { ... cached_tags editions(limit) { isbn_13 isbn_10 } }` - Hasura-
  style, catalog-wide (not `me`-scoped). `cached_tags` is a JSON object keyed
  by category, e.g. `{"Genre": [{"tag": "Science Fiction", ...}], "Tag": [...],
  "Mood": [...], "Content Warning": [...]}` - clean genre names live under the
  `"Genre"` key. This is the query genre-based search should use (filter by
  rating/ratings_count server-side, then match cached_tags.Genre client-side).

Constraints: 60 requests/minute, 30s query timeout, max query depth 3, tokens
expire yearly (reset Jan 1). Auth: `authorization` header, token used
verbatim (the stored token already contains a literal "Bearer " prefix - do
not add another one).
"""


class HardcoverAPIError(RuntimeError):
    pass


def _graphql_string_literal(value: str) -> str:
    """JSON string escaping produces a valid GraphQL string literal."""
    return json.dumps(value)


class HardcoverClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout_seconds: float = 30,
        max_retries: int = 3,
        request_delay_seconds: float = 1.0,
    ) -> None:
        self._base_url = base_url
        self._max_retries = max_retries
        self._request_delay_seconds = request_delay_seconds
        self._client = httpx.Client(
            headers={
                "authorization": api_token,
                "content-type": "application/json",
                "user-agent": "reading-catalog/0.1",
            },
            timeout=timeout_seconds,
        )

    def __enter__(self) -> "HardcoverClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self._client.close()

    def _post_graphql(self, query: str) -> dict:
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        def _do_post() -> dict:
            response = self._client.post(self._base_url, json={"query": query})
            response.raise_for_status()
            return response.json()

        time.sleep(self._request_delay_seconds)
        body = _do_post()
        if body.get("errors"):
            raise HardcoverAPIError(str(body["errors"]))
        return body["data"]

    def search_books(self, query: str, per_page: int = 25, page: int = 1) -> list[dict]:
        graphql_query = (
            f"query {{ search(query: {_graphql_string_literal(query)}, "
            f'query_type: "Book", per_page: {per_page}, page: {page}) {{ results }} }}'
        )
        data = self._post_graphql(graphql_query)
        results = data["search"]["results"]
        if not results:
            return []
        return [hit["document"] for hit in results.get("hits", [])]

    def fetch_top_rated_books(self, min_rating: float, min_ratings_count: int, limit: int = 100) -> list[dict]:
        graphql_query = (
            "query { books("
            f"where: {{rating: {{_gte: {min_rating}}}, ratings_count: {{_gte: {min_ratings_count}}}}}, "
            f"order_by: {{ratings_count: desc}}, limit: {limit}"
            ") { title rating ratings_count release_year cached_tags "
            "contributions { author { name } } editions(limit: 3) { isbn_13 isbn_10 } } }"
        )
        data = self._post_graphql(graphql_query)
        return data["books"]

    def find_by_isbn13(self, isbn13: str) -> dict | None:
        hits = self.search_books(isbn13, per_page=1)
        return hits[0] if hits else None

    def find_by_title_author(self, title: str, author: str | None = None) -> dict | None:
        query = f"{title} {author}" if author else title
        hits = self.search_books(query, per_page=1)
        return hits[0] if hits else None
