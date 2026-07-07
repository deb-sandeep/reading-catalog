from __future__ import annotations

import datetime
import enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Table, Text, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LibraryStatus(str, enum.Enum):
    WORKING = "working"
    CURATED = "curated"


book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("author_id", ForeignKey("authors.id"), primary_key=True),
)

book_genres = Table(
    "book_genres",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isbn13: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    library_status: Mapped[str] = mapped_column(String, nullable=False, default=LibraryStatus.WORKING.value)
    have_ebook: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reading_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    my_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    authors: Mapped[list["Author"]] = relationship(secondary=book_authors, back_populates="books")
    genres: Mapped[list["Genre"]] = relationship(secondary=book_genres, back_populates="books")
    themes: Mapped[list["BookTheme"]] = relationship(back_populates="book")
    source_records: Mapped[list["SourceRecord"]] = relationship(back_populates="book")


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    books: Mapped[list["Book"]] = relationship(secondary=book_authors, back_populates="authors")


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    books: Mapped[list["Book"]] = relationship(secondary=book_genres, back_populates="genres")


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class BookTheme(Base):
    __tablename__ = "book_themes"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id"), primary_key=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="themes")
    theme: Mapped["Theme"] = relationship()


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_ratings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    book: Mapped["Book"] = relationship(back_populates="source_records")
