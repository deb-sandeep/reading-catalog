import datetime

import pytest

from src.pipeline.models import BookRecord
from src.storage.db import init_db, make_engine, make_session_factory, session_scope, upsert_book
from src.storage.db_models import Author, Book, Genre

NOW = datetime.datetime(2026, 1, 1)


@pytest.fixture
def session_factory():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def make_record(**overrides):
    defaults = dict(title="Dune", authors=["Frank Herbert"], genres=["Science Fiction"], last_checked_at=NOW, source_name="openlibrary")
    defaults.update(overrides)
    return BookRecord(**defaults)


def test_same_isbn13_upserted_twice_yields_one_row(session_factory):
    with session_scope(session_factory) as session:
        upsert_book(session, make_record(isbn13="9780441013593"))
        upsert_book(session, make_record(isbn13="9780441013593", description="updated desc"))
        session.commit()
        books = session.query(Book).all()
        assert len(books) == 1
        assert books[0].description == "updated desc"


def test_isbn_less_records_dedupe_by_title_and_author(session_factory):
    with session_scope(session_factory) as session:
        upsert_book(session, make_record(isbn13=None))
        upsert_book(session, make_record(isbn13=None))
        session.commit()
        assert session.query(Book).count() == 1


def test_isbn_less_records_with_different_title_create_two_rows(session_factory):
    with session_scope(session_factory) as session:
        upsert_book(session, make_record(isbn13=None, title="Dune"))
        upsert_book(session, make_record(isbn13=None, title="Dune Messiah"))
        session.commit()
        assert session.query(Book).count() == 2


def test_recurring_author_and_genre_names_create_single_rows(session_factory):
    with session_scope(session_factory) as session:
        upsert_book(session, make_record(isbn13=None, title="Dune"))
        upsert_book(session, make_record(isbn13=None, title="Dune Messiah"))
        session.commit()
        assert session.query(Author).filter_by(name="Frank Herbert").count() == 1
        assert session.query(Genre).filter_by(name="Science Fiction").count() == 1


def test_upsert_returns_created_flag(session_factory):
    with session_scope(session_factory) as session:
        _, created_first = upsert_book(session, make_record(isbn13="9780441013593"))
        _, created_second = upsert_book(session, make_record(isbn13="9780441013593"))
        assert created_first is True
        assert created_second is False
