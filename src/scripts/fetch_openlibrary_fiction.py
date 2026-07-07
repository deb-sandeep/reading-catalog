from __future__ import annotations

import argparse
import datetime
import logging

from src.config import load_config
from src.pipeline.normalize import normalize_openlibrary_entry
from src.sources.openlibrary_client import OpenLibraryClient
from src.storage.db import init_db, make_engine, make_session_factory, session_scope, upsert_book

logger = logging.getLogger(__name__)


def run(subject: str | None, limit: int | None, config_path: str) -> dict:
    config = load_config(config_path)
    logging.basicConfig(level=config.app.log_level)

    subject = subject or config.discovery.openlibrary.subjects[0]
    limit = limit or config.discovery.openlibrary.limit_per_subject

    engine = make_engine(config.app.db_url)
    init_db(engine)
    session_factory = make_session_factory(engine)

    ol_config = config.sources.openlibrary
    fetched_at = datetime.datetime.now(datetime.timezone.utc)

    candidates_seen = 0
    created_count = 0
    updated_count = 0
    no_isbn_count = 0
    no_author_count = 0

    with OpenLibraryClient(
        base_url=ol_config.base_url,
        user_agent=ol_config.user_agent,
        timeout_seconds=ol_config.timeout_seconds,
        max_retries=ol_config.max_retries,
        request_delay_seconds=ol_config.request_delay_seconds,
    ) as client, session_scope(session_factory) as session:
        subject_data = client.fetch_subject(subject, limit)

        for work_stub in subject_data.get("works", []):
            candidates_seen += 1
            work_key = work_stub.get("key")
            work_detail = client.fetch_work(work_key) if work_key else None

            edition_key = work_stub.get("cover_edition_key")
            edition_detail = client.fetch_edition(edition_key) if edition_key else None

            record = normalize_openlibrary_entry(
                subject_name=subject,
                work_stub=work_stub,
                work_detail=work_detail,
                edition_detail=edition_detail,
                fetched_at=fetched_at,
            )

            book, created = upsert_book(session, record)
            if created:
                created_count += 1
            else:
                updated_count += 1
            if not record.isbn13:
                no_isbn_count += 1
            if not record.authors:
                no_author_count += 1

            logger.info(
                "%s | isbn13=%s | %s",
                record.title,
                record.isbn13 or "none",
                "created" if created else "updated",
            )

        session.commit()

    summary = {
        "candidates_seen": candidates_seen,
        "created": created_count,
        "updated": updated_count,
        "no_isbn": no_isbn_count,
        "no_author": no_author_count,
    }
    print(
        f"candidates_seen={candidates_seen} created={created_count} "
        f"updated={updated_count} no_isbn={no_isbn_count} no_author={no_author_count}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and persist books from an Open Library subject browse.")
    parser.add_argument("--subject", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    run(subject=args.subject, limit=args.limit, config_path=args.config)


if __name__ == "__main__":
    main()
