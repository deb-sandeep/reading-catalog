import datetime

import pytest
from pydantic import ValidationError

from src.pipeline.models import BookRecord

NOW = datetime.datetime(2026, 1, 1)


def make_record(**overrides):
    defaults = dict(title="Some Book", last_checked_at=NOW, source_name="openlibrary")
    defaults.update(overrides)
    return BookRecord(**defaults)


def test_title_required_non_blank():
    with pytest.raises(ValidationError):
        make_record(title="   ")


def test_all_optional_fields_none_constructs_fine():
    record = make_record()
    assert record.isbn13 is None
    assert record.average_rating is None
    assert record.ratings_count is None
    assert record.source_confidence is None
    assert record.authors == []
    assert record.genres == []


def test_isbn13_must_be_13_digits():
    make_record(isbn13="9780306406157")  # ok
    with pytest.raises(ValidationError):
        make_record(isbn13="12345")
    with pytest.raises(ValidationError):
        make_record(isbn13="978030640615X")


def test_average_rating_range():
    make_record(average_rating=4.5)  # ok
    with pytest.raises(ValidationError):
        make_record(average_rating=5.5)
    with pytest.raises(ValidationError):
        make_record(average_rating=-0.1)


def test_publish_year_range():
    make_record(publish_year=1813)  # ok
    with pytest.raises(ValidationError):
        make_record(publish_year=1000)
    with pytest.raises(ValidationError):
        make_record(publish_year=3000)
