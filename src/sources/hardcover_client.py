from __future__ import annotations

"""Stub for the Hardcover GraphQL client - deferred until HARDCOVER_API_TOKEN
is available.

Confirmed against Hardcover's own docs (github.com/hardcoverapp/hardcover-docs)
that catalog-wide discovery IS supported (not just `me`-scoped queries):

- `books(where: {rating: {_gte: 4.0}, ratings_count: {_gte: N}}, order_by: {...},
  limit: ...)` - a Hasura-style query over the whole books table.
- `search(query: String!, query_type: "Book", per_page, page, sort, fields,
  weights, typos)` - Typesense-backed keyword search, also global.

Constraints to design around when this is implemented: 60 requests/minute,
30s query timeout, max query depth 3, tokens expire yearly (reset Jan 1).
Endpoint: https://api.hardcover.app/v1/graphql, auth via `authorization` header
with the bearer token (no "Bearer " prefix per their docs example).
"""


class HardcoverClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        self._base_url = base_url
        self._api_token = api_token

    def search_books(self, query: str, per_page: int = 25, page: int = 1) -> dict:
        raise NotImplementedError("Hardcover client is deferred until HARDCOVER_API_TOKEN is available")

    def fetch_books(self, where: dict, order_by: dict | None = None, limit: int = 25) -> dict:
        raise NotImplementedError("Hardcover client is deferred until HARDCOVER_API_TOKEN is available")
