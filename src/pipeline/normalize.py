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
