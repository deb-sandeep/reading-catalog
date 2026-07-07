from __future__ import annotations

import datetime

from src.pipeline.models import BookRecord


def isbn10_to_isbn13(isbn10: str) -> str:
    """Standard ISBN-10 -> ISBN-13 conversion (drop ISBN-10 check digit,
    prefix 978, recompute the ISBN-13 checksum)."""
    digits = isbn10.replace("-", "").strip()
    core = "978" + digits[:9]
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(core))
    check_digit = (10 - total % 10) % 10
    return core + str(check_digit)


def extract_description(work_detail: dict) -> str | None:
    """Open Library's work `description` is sometimes a plain string and
    sometimes {"type": "/type/text", "value": "..."} - both are real, observed
    shapes."""
    desc = work_detail.get("description")
    if desc is None:
        return None
    if isinstance(desc, dict):
        return desc.get("value")
    return desc


def extract_isbn13(edition_detail: dict) -> str | None:
    """Prefer a native isbn_13; fall back to converting isbn_10. Many editions
    have neither - that's an expected gap for this source, not an error."""
    isbn_13 = edition_detail.get("isbn_13")
    if isbn_13:
        return isbn_13[0]
    isbn_10 = edition_detail.get("isbn_10")
    if isbn_10:
        return isbn10_to_isbn13(isbn_10[0])
    return None


def normalize_openlibrary_entry(
    subject_name: str,
    work_stub: dict,
    work_detail: dict | None,
    edition_detail: dict | None,
    fetched_at: datetime.datetime,
) -> BookRecord:
    """Map one Open Library subject-browse work entry (plus optional work/edition
    detail fetches) to a canonical BookRecord.

    Genre is the browsed subject itself (e.g. "Fiction"), not a canonicalization
    of Open Library's ~50-100 raw per-book subject tags - that normalization is
    genre_mapper.py's job in a later slice.

    average_rating/ratings_count/source_confidence are always None here: Open
    Library doesn't track Goodreads-scale ratings, and with a single source
    there's nothing yet to reconcile a confidence score against.
    """
    authors = [a["name"] for a in work_stub.get("authors", []) if a.get("name")]

    return BookRecord(
        isbn13=extract_isbn13(edition_detail) if edition_detail else None,
        title=work_stub["title"],
        authors=authors,
        genres=[subject_name.title()] if subject_name else [],
        average_rating=None,
        ratings_count=None,
        description=extract_description(work_detail) if work_detail else None,
        publish_year=work_stub.get("first_publish_year"),
        source_confidence=None,
        last_checked_at=fetched_at,
        source_name="openlibrary",
        source_ref=work_stub.get("key"),
    )


def normalize_openlibrary_search_doc(doc: dict, fetched_at: datetime.datetime) -> BookRecord:
    """For OpenLibraryClient.search() docs - a different shape than the
    subject-browse work_stub normalize_openlibrary_entry expects (flat
    `author_name`/`isbn`/`first_publish_year` fields, no nested work/edition
    detail available). Used by the working-shelf rich-view lookup."""
    isbn13 = next((i for i in (doc.get("isbn") or []) if len(i) == 13), None)
    return BookRecord(
        isbn13=isbn13,
        title=doc["title"],
        authors=doc.get("author_name", []),
        genres=[],
        average_rating=None,
        ratings_count=None,
        description=None,
        publish_year=doc.get("first_publish_year"),
        source_confidence=None,
        last_checked_at=fetched_at,
        source_name="openlibrary",
        source_ref=doc.get("key"),
    )


def _extract_hardcover_isbn13(raw: dict) -> str | None:
    """Handles both raw shapes Hardcover can return: a flat `isbns` list
    (from HardcoverClient.search_books) or nested `editions` (from
    HardcoverClient.fetch_top_rated_books)."""
    for isbn in raw.get("isbns") or []:
        if len(isbn) == 13:
            return isbn
    for edition in raw.get("editions") or []:
        if edition.get("isbn_13"):
            return edition["isbn_13"]
    return None


def _extract_hardcover_genres(raw: dict) -> list[str]:
    """search_books hits have flat `genres`/`tags` lists; fetch_top_rated_books
    rows have a `cached_tags` dict keyed by category, with clean genre names
    under the "Genre" key."""
    if "genres" in raw:
        return list(dict.fromkeys((raw.get("genres") or []) + (raw.get("tags") or [])))
    cached_tags = raw.get("cached_tags") or {}
    return [tag["tag"] for tag in cached_tags.get("Genre", [])]


def _extract_hardcover_authors(raw: dict) -> list[str]:
    """search_books hits have a flat `author_names` list; fetch_top_rated_books
    rows have `contributions[].author.name` instead."""
    if "author_names" in raw:
        return list(raw.get("author_names") or [])
    return [c["author"]["name"] for c in raw.get("contributions") or [] if c.get("author")]


def normalize_hardcover_book(raw: dict, fetched_at: datetime.datetime) -> BookRecord:
    """Maps either a HardcoverClient.search_books hit or a
    fetch_top_rated_books row to a canonical BookRecord - see
    _extract_hardcover_isbn13/_extract_hardcover_genres for the shape
    differences between the two."""
    return BookRecord(
        isbn13=_extract_hardcover_isbn13(raw),
        title=raw["title"],
        authors=_extract_hardcover_authors(raw),
        genres=_extract_hardcover_genres(raw),
        average_rating=raw.get("rating"),
        ratings_count=raw.get("ratings_count"),
        description=raw.get("description"),
        publish_year=raw.get("release_year"),
        source_confidence=None,
        last_checked_at=fetched_at,
        source_name="hardcover",
        source_ref=str(raw["id"]) if raw.get("id") is not None else None,
    )


def _parse_year_prefix(date_str: str | None) -> int | None:
    """Google Books publishedDate is inconsistently precise ('2010',
    '2010-05', '2010-05-14') - only the leading 4-digit year is reliable."""
    if not date_str or not date_str[:4].isdigit():
        return None
    return int(date_str[:4])


def normalize_googlebooks_volume(raw: dict, fetched_at: datetime.datetime) -> BookRecord:
    info = raw.get("volumeInfo", {})
    isbn13 = None
    for ident in info.get("industryIdentifiers", []):
        if ident.get("type") == "ISBN_13":
            isbn13 = ident["identifier"]
            break
    if isbn13 is None:
        for ident in info.get("industryIdentifiers", []):
            if ident.get("type") == "ISBN_10":
                isbn13 = isbn10_to_isbn13(ident["identifier"])
                break
    return BookRecord(
        isbn13=isbn13,
        title=info["title"],
        authors=info.get("authors", []),
        genres=info.get("categories", []),
        average_rating=info.get("averageRating"),
        ratings_count=info.get("ratingsCount"),
        description=info.get("description"),
        publish_year=_parse_year_prefix(info.get("publishedDate")),
        source_confidence=None,
        last_checked_at=fetched_at,
        source_name="googlebooks",
        source_ref=raw.get("id"),
    )
