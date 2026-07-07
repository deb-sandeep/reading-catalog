import datetime
import json
from pathlib import Path

from src.pipeline.normalize import (
    extract_description,
    extract_isbn13,
    isbn10_to_isbn13,
    normalize_openlibrary_entry,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime.datetime(2026, 1, 1)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_isbn10_to_isbn13_standard_test_vector():
    assert isbn10_to_isbn13("0-306-40615-2") == "9780306406157"
    assert isbn10_to_isbn13("0306406152") == "9780306406157"


def test_extract_description_plain_string():
    work_detail = load_fixture("work_detail_plain_desc.json")
    desc = extract_description(work_detail)
    assert isinstance(desc, str)
    assert "1984" in desc or "Orwell" in desc or len(desc) > 0


def test_extract_description_dict_shape():
    work_detail = load_fixture("work_detail_dict_desc.json")
    desc = extract_description(work_detail)
    assert isinstance(desc, str)
    assert "Ahab" in desc


def test_extract_description_missing():
    assert extract_description({}) is None


def test_extract_isbn13_present():
    edition = load_fixture("edition_with_isbn13.json")
    isbn13 = extract_isbn13(edition)
    assert isbn13 == edition["isbn_13"][0]
    assert len(isbn13) == 13


def test_extract_isbn13_from_isbn10_only():
    edition = load_fixture("edition_with_isbn10_only.json")
    assert extract_isbn13(edition) == "9780306406157"


def test_extract_isbn13_missing_entirely():
    assert extract_isbn13({"isbn_13": None, "isbn_10": None}) is None


def test_normalize_entry_with_full_detail():
    subjects = load_fixture("subjects_fiction.json")
    work_stub = subjects["works"][0]
    work_detail = load_fixture("work_detail_plain_desc.json")
    edition = load_fixture("edition_with_isbn13.json")

    record = normalize_openlibrary_entry(
        subject_name="fiction",
        work_stub=work_stub,
        work_detail=work_detail,
        edition_detail=edition,
        fetched_at=NOW,
    )

    assert record.title == work_stub["title"]
    assert record.authors == [a["name"] for a in work_stub["authors"]]
    assert record.genres == ["Fiction"]
    assert record.average_rating is None
    assert record.ratings_count is None
    assert record.source_confidence is None
    assert record.source_name == "openlibrary"
    assert record.source_ref == work_stub["key"]
    assert record.isbn13 is not None


def test_normalize_entry_missing_work_and_edition_detail():
    subjects = load_fixture("subjects_fiction.json")
    work_stub = subjects["works"][0]

    record = normalize_openlibrary_entry(
        subject_name="fiction",
        work_stub=work_stub,
        work_detail=None,
        edition_detail=None,
        fetched_at=NOW,
    )

    assert record.description is None
    assert record.isbn13 is None
    assert record.title == work_stub["title"]
