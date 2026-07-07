import datetime
import json
from pathlib import Path

from src.pipeline.normalize import normalize_openlibrary_search_doc

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime.datetime(2026, 1, 1)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_normalize_doc_without_isbn():
    doc = load_fixture("openlibrary_search_doc.json")
    record = normalize_openlibrary_search_doc(doc, NOW)
    assert record.title == "Dune"
    assert record.authors == ["Frank Herbert"]
    assert record.publish_year == 1965
    assert record.isbn13 is None
    assert record.source_name == "openlibrary"
    assert record.source_ref == "/works/OL893415W"


def test_normalize_doc_with_isbn():
    doc = load_fixture("openlibrary_search_doc_with_isbn.json")
    record = normalize_openlibrary_search_doc(doc, NOW)
    assert record.isbn13 == "9780441013593"
