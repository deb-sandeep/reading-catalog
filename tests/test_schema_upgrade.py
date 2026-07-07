import datetime

from sqlalchemy import inspect, text

from src.storage.db import init_db, make_engine, make_session_factory, session_scope
from src.storage.db_models import Book, LibraryStatus


def test_init_db_upgrades_pre_existing_books_table_in_place():
    """Simulates the real data/catalog.db: a books table created before
    library_status/have_ebook/is_read/reading_sequence/my_rating existed.
    init_db() must add the missing columns and default existing rows to the
    working shelf, without a separate migration step."""
    engine = make_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE books (
                id INTEGER PRIMARY KEY,
                isbn13 TEXT UNIQUE,
                title TEXT NOT NULL,
                average_rating REAL,
                ratings_count INTEGER,
                description TEXT,
                publish_year INTEGER,
                source_confidence REAL,
                last_checked_at DATETIME NOT NULL
            )
        """))
        conn.execute(
            text("INSERT INTO books (isbn13, title, last_checked_at) VALUES (:isbn, :title, :checked)"),
            {"isbn": "9780441013593", "title": "Dune", "checked": datetime.datetime(2026, 1, 1)},
        )

    init_db(engine)

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("books")}
    assert {"library_status", "have_ebook", "is_read", "reading_sequence", "my_rating"} <= columns

    session_factory = make_session_factory(engine)
    with session_scope(session_factory) as session:
        book = session.query(Book).filter_by(isbn13="9780441013593").one()
        assert book.library_status == LibraryStatus.WORKING.value
        assert book.have_ebook is False
        assert book.is_read is False
        assert book.reading_sequence is None
        assert book.my_rating is None


def test_init_db_is_noop_on_fresh_database():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)  # creates full schema from scratch, including new columns
    init_db(engine)  # calling again must not error
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("books")}
    assert {"library_status", "have_ebook", "is_read", "reading_sequence", "my_rating"} <= columns
