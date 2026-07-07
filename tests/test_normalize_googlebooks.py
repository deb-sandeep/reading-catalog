import datetime
import json
from pathlib import Path

from src.pipeline.normalize import _parse_year_prefix, normalize_googlebooks_volume

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime.datetime(2026, 1, 1)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_parse_year_prefix_full_date():
    assert _parse_year_prefix("2010-05-14") == 2010


def test_parse_year_prefix_year_only():
    assert _parse_year_prefix("2010") == 2010


def test_parse_year_prefix_missing_or_garbage():
    assert _parse_year_prefix(None) is None
    assert _parse_year_prefix("") is None
    assert _parse_year_prefix("unknown") is None


def test_normalize_full_volume_prefers_isbn13():
    raw = load_fixture("googlebooks_volume_full.json")
    record = normalize_googlebooks_volume(raw, NOW)
    assert record.title == "Dune"
    assert record.isbn13 == "9780441013593"
    assert record.authors == ["Frank Herbert"]
    assert record.genres == ["Fiction"]
    assert record.publish_year == 2005
    assert record.average_rating is None
    assert record.ratings_count is None
    assert record.source_name == "googlebooks"
    assert record.source_ref == "saONEAAAQBAJ"


def test_normalize_isbn10_only_converts_to_isbn13():
    raw = load_fixture("googlebooks_volume_isbn10_only.json")
    record = normalize_googlebooks_volume(raw, NOW)
    assert record.isbn13 == "9780306406157"  # standard test vector for 0306406152


def test_normalize_with_real_ratings_present():
    raw = load_fixture("googlebooks_volume_with_ratings.json")
    record = normalize_googlebooks_volume(raw, NOW)
    assert record.average_rating == 4.5
    assert record.ratings_count == 90


def test_normalize_no_isbn_no_ratings():
    raw = load_fixture("googlebooks_volume_no_ratings.json")
    record = normalize_googlebooks_volume(raw, NOW)
    assert record.isbn13 is None
    assert record.average_rating is None
    assert record.authors == []
    assert record.publish_year is None
