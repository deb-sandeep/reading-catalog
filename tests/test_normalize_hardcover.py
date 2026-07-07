import datetime
import json
from pathlib import Path

from src.pipeline.normalize import (
    _extract_hardcover_authors,
    _extract_hardcover_genres,
    _extract_hardcover_isbn13,
    normalize_hardcover_book,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime.datetime(2026, 1, 1)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_isbn13_from_flat_isbns_list_search_shape():
    raw = load_fixture("hardcover_search_hit.json")
    isbn13 = _extract_hardcover_isbn13(raw)
    assert isbn13 == "9780792748663"
    assert len(isbn13) == 13


def test_isbn13_from_editions_list_books_row_shape():
    raw = load_fixture("hardcover_books_row_with_cached_tags.json")
    assert _extract_hardcover_isbn13(raw) == "9780807281956"


def test_isbn13_missing_entirely():
    assert _extract_hardcover_isbn13({}) is None
    assert _extract_hardcover_isbn13({"isbns": [], "editions": []}) is None


def test_genres_from_flat_genres_and_tags_search_shape():
    raw = load_fixture("hardcover_search_hit.json")
    genres = _extract_hardcover_genres(raw)
    assert "Science Fiction" in genres
    assert "Fiction" in genres
    # de-duplicated, order-preserving
    assert len(genres) == len(set(genres))


def test_genres_from_cached_tags_books_row_shape():
    raw = load_fixture("hardcover_books_row_with_cached_tags.json")
    genres = _extract_hardcover_genres(raw)
    assert genres == ["Fantasy", "Fiction", "Young Adult", "Magic", "Adventure"]


def test_genres_missing_entirely():
    assert _extract_hardcover_genres({}) == []


def test_authors_from_flat_author_names_search_shape():
    raw = load_fixture("hardcover_search_hit.json")
    assert _extract_hardcover_authors(raw) == ["Frank Herbert", "Brian Herbert"]


def test_authors_from_contributions_books_row_shape():
    raw = load_fixture("hardcover_books_row_with_cached_tags.json")
    assert _extract_hardcover_authors(raw) == ["J.K. Rowling"]


def test_authors_missing_entirely():
    assert _extract_hardcover_authors({}) == []


def test_normalize_search_hit_shape():
    raw = load_fixture("hardcover_search_hit.json")
    record = normalize_hardcover_book(raw, NOW)
    assert record.title == "Dune"
    assert record.authors == ["Frank Herbert", "Brian Herbert"]
    assert record.isbn13 == "9780792748663"
    assert record.average_rating == raw["rating"]
    assert record.ratings_count == 5767
    assert record.publish_year == 1965
    assert record.source_name == "hardcover"
    assert record.source_ref == "312460"


def test_normalize_books_row_shape():
    raw = load_fixture("hardcover_books_row_with_cached_tags.json")
    record = normalize_hardcover_book(raw, NOW)
    assert record.title == "Harry Potter and the Philosopher's Stone"
    assert record.authors == ["J.K. Rowling"]
    assert record.isbn13 == "9780807281956"
    assert "Fantasy" in record.genres
    # This shape has no "id" and no "description" field selected - both stay None/empty
    assert record.source_ref is None
    assert record.description is None
