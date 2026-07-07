from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.storage.db_models import Book, LibraryStatus


class CuratedBookUpdate(BaseModel):
    book_id: int
    have_ebook: bool = False
    is_read: bool = False
    reading_sequence: int | None = None
    my_rating: float | None = Field(default=None, ge=0, le=5)


def apply_curated_updates(session: Session, updates: list[CuratedBookUpdate]) -> None:
    """Writes user-edited curated-library metadata back to Book rows.

    Ignores any book_id that no longer exists or is no longer curated (e.g.
    the row was edited in the UI, then demoted/deleted elsewhere before
    saving) rather than raising - the UI's data_editor round-trip is the only
    caller, and silently skipping a stale row is safer than crashing the save.
    """
    for update in updates:
        book = session.get(Book, update.book_id)
        if book is None or book.library_status != LibraryStatus.CURATED.value:
            continue
        book.have_ebook = update.have_ebook
        book.is_read = update.is_read
        book.reading_sequence = update.reading_sequence
        book.my_rating = update.my_rating
