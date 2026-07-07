from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.pipeline.models import BookRecord
from src.storage.db_models import Author, Base, Book, Genre, SourceRecord


def make_engine(db_url: str) -> Engine:
    return create_engine(db_url)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_or_create_author(session: Session, name: str) -> Author:
    author = session.query(Author).filter_by(name=name).one_or_none()
    if author is None:
        author = Author(name=name)
        session.add(author)
        session.flush()
    return author


def get_or_create_genre(session: Session, name: str) -> Genre:
    genre = session.query(Genre).filter_by(name=name).one_or_none()
    if genre is None:
        genre = Genre(name=name)
        session.add(genre)
        session.flush()
    return genre


def find_existing_book(session: Session, record: BookRecord) -> Book | None:
    """Isbn13 exact match first; otherwise a deliberately dumb fallback on
    (title, first author) exact case-insensitive match.

    This is a temporary stand-in for real reconciliation, not the reconciliation
    algorithm itself - no fuzzy matching, no scoring, no cross-source merge. It
    only exists to keep reruns of this single-source script idempotent. It will
    be superseded once pipeline/reconcile.py is built.
    """
    if record.isbn13:
        existing = session.query(Book).filter_by(isbn13=record.isbn13).one_or_none()
        if existing is not None:
            return existing

    if not record.authors:
        return None

    first_author = record.authors[0].casefold()
    title_cf = record.title.casefold()
    candidates = (
        session.query(Book)
        .join(Book.authors)
        .filter(Author.name.ilike(record.authors[0]))
        .all()
    )
    for candidate in candidates:
        if candidate.title.casefold() != title_cf:
            continue
        candidate_author_names = {a.name.casefold() for a in candidate.authors}
        if first_author in candidate_author_names:
            return candidate
    return None


def upsert_book(session: Session, record: BookRecord) -> tuple[Book, bool]:
    """Insert or update a Book from a BookRecord, and always append a
    SourceRecord audit row for this fetch. Returns (book, created)."""
    existing = find_existing_book(session, record)
    created = existing is None
    book = existing if existing is not None else Book(title=record.title)
    if created:
        session.add(book)

    book.title = record.title
    book.isbn13 = record.isbn13 or book.isbn13
    book.average_rating = record.average_rating if record.average_rating is not None else book.average_rating
    book.ratings_count = record.ratings_count if record.ratings_count is not None else book.ratings_count
    book.description = record.description or book.description
    book.publish_year = record.publish_year or book.publish_year
    book.source_confidence = record.source_confidence if record.source_confidence is not None else book.source_confidence
    book.last_checked_at = record.last_checked_at

    book.authors = [get_or_create_author(session, name) for name in record.authors]
    book.genres = [get_or_create_genre(session, name) for name in record.genres]

    session.flush()

    session.add(
        SourceRecord(
            book_id=book.id,
            source_name=record.source_name,
            raw_rating=record.average_rating,
            raw_ratings_count=record.ratings_count,
            fetched_at=record.last_checked_at,
        )
    )

    return book, created
