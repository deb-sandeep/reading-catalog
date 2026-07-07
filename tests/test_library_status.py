import datetime

import pytest

from src.pipeline.curated import CuratedBookUpdate, apply_curated_updates
from src.pipeline.models import BookRecord
from src.storage.db import (
    import_to_working_shelf,
    init_db,
    make_engine,
    make_session_factory,
    promote_to_curated,
    session_scope,
    upsert_book,
)
from src.storage.db_models import Book, LibraryStatus

NOW = datetime.datetime(2026, 1, 1)


@pytest.fixture
def session_factory():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return make_session_factory(engine)


def make_record(**overrides):
    defaults = dict(
        title="Dune", authors=["Frank Herbert"], genres=["Science Fiction"],
        last_checked_at=NOW, source_name="openlibrary",
    )
    defaults.update(overrides)
    return BookRecord(**defaults)


def test_import_to_working_shelf_sets_status_on_create(session_factory):
    with session_scope(session_factory) as session:
        book, created = import_to_working_shelf(session, make_record(isbn13="9780441013593"))
        session.commit()
        assert created is True
        assert book.library_status == LibraryStatus.WORKING.value


def test_import_to_working_shelf_does_not_downgrade_existing_curated_book(session_factory):
    with session_scope(session_factory) as session:
        book, _ = import_to_working_shelf(session, make_record(isbn13="9780441013593"))
        promote_to_curated(session, book)
        session.commit()
        assert book.library_status == LibraryStatus.CURATED.value

        # Re-importing the same book (e.g. it shows up again in a search) must not demote it
        book2, created2 = import_to_working_shelf(session, make_record(isbn13="9780441013593", description="new desc"))
        session.commit()
        assert created2 is False
        assert book2.id == book.id
        assert book2.library_status == LibraryStatus.CURATED.value


def test_upsert_book_never_alters_library_status(session_factory):
    with session_scope(session_factory) as session:
        book, _ = import_to_working_shelf(session, make_record(isbn13="9780441013593"))
        promote_to_curated(session, book)
        session.commit()

        # Plain upsert_book (rich-view backfill path) must leave status untouched
        upsert_book(session, make_record(isbn13="9780441013593", average_rating=4.5, ratings_count=100))
        session.commit()
        assert book.library_status == LibraryStatus.CURATED.value
        assert book.average_rating == 4.5


def test_promote_to_curated_assigns_next_sequence_and_is_idempotent(session_factory):
    with session_scope(session_factory) as session:
        book1, _ = import_to_working_shelf(session, make_record(isbn13="1111111111111", title="Book One"))
        book2, _ = import_to_working_shelf(session, make_record(isbn13="2222222222222", title="Book Two"))
        session.commit()

        promote_to_curated(session, book1)
        session.commit()
        assert book1.reading_sequence == 1

        promote_to_curated(session, book2)
        session.commit()
        assert book2.reading_sequence == 2

        # Idempotent: promoting an already-curated book is a no-op
        promote_to_curated(session, book1)
        session.commit()
        assert book1.reading_sequence == 1


def test_apply_curated_updates_writes_fields(session_factory):
    with session_scope(session_factory) as session:
        book, _ = import_to_working_shelf(session, make_record(isbn13="9780441013593"))
        promote_to_curated(session, book)
        session.commit()

        apply_curated_updates(session, [
            CuratedBookUpdate(book_id=book.id, have_ebook=True, is_read=True, reading_sequence=5, my_rating=4.5),
        ])
        session.commit()

        refreshed = session.get(Book, book.id)
        assert refreshed.have_ebook is True
        assert refreshed.is_read is True
        assert refreshed.reading_sequence == 5
        assert refreshed.my_rating == 4.5


def test_apply_curated_updates_ignores_non_curated_book_id(session_factory):
    with session_scope(session_factory) as session:
        book, _ = import_to_working_shelf(session, make_record(isbn13="9780441013593"))
        session.commit()
        assert book.library_status == LibraryStatus.WORKING.value

        apply_curated_updates(session, [
            CuratedBookUpdate(book_id=book.id, have_ebook=True, is_read=True, reading_sequence=1, my_rating=5.0),
        ])
        session.commit()

        refreshed = session.get(Book, book.id)
        # Untouched - book was never curated, update should have been skipped
        assert refreshed.have_ebook is False
        assert refreshed.my_rating is None
