from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, field_validator

CURRENT_YEAR = datetime.date.today().year


class BookRecord(BaseModel):
    """Canonical per-source book record. One instance per (book, source) fetch.

    average_rating/ratings_count/source_confidence are left None rather than a
    placeholder when a source doesn't provide them - None is the only value that
    doesn't fabricate data that wasn't actually observed.
    """

    isbn13: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    average_rating: float | None = None
    ratings_count: int | None = None
    description: str | None = None
    publish_year: int | None = None
    source_confidence: float | None = None
    last_checked_at: datetime.datetime

    # Pipeline-internal only - not persisted as `books` table columns.
    source_name: str
    source_ref: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v

    @field_validator("isbn13")
    @classmethod
    def isbn13_must_be_13_digits(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not (len(v) == 13 and v.isdigit()):
            raise ValueError(f"isbn13 must be exactly 13 digits, got {v!r}")
        return v

    @field_validator("average_rating")
    @classmethod
    def rating_in_range(cls, v: float | None) -> float | None:
        if v is not None and not (0 <= v <= 5):
            raise ValueError(f"average_rating must be in [0, 5], got {v!r}")
        return v

    @field_validator("publish_year")
    @classmethod
    def publish_year_sane(cls, v: int | None) -> int | None:
        if v is not None and not (1450 <= v <= CURRENT_YEAR + 1):
            raise ValueError(f"publish_year {v!r} out of plausible range")
        return v
