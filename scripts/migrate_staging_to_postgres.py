from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.jobs import DEFAULT_DB_PATH

try:
    from sqlalchemy import text as sql_text
    from sqlalchemy.engine import Engine

    from legal_db.db import make_engine
except ModuleNotFoundError:
    sql_text = None
    Engine = Any  # type: ignore[misc, assignment]
    make_engine = None


def require_postgres_dependencies() -> tuple[Callable[..., Any], Callable[[str | None], Any]]:
    if sql_text is None or make_engine is None:
        raise RuntimeError(
            "PostgreSQL migration dependencies are missing. Install project dependencies first."
        )
    return sql_text, make_engine


@dataclass(frozen=True)
class MigrationSummary:
    sqlite_available: bool
    postgres_available: bool
    dry_run: bool
    counts: dict[str, int]
    migrated: dict[str, int]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sqlite_available": self.sqlite_available,
            "postgres_available": self.postgres_available,
            "dry_run": self.dry_run,
            "counts": self.counts,
            "migrated": self.migrated,
            "errors": self.errors,
        }


def sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()[0]
        > 0
    )


def sqlite_count(conn: sqlite3.Connection, table_name: str) -> int:
    if not sqlite_table_exists(conn, table_name):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def staging_counts(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, int]:
    path = Path(db_path)
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    try:
        return {
            table: sqlite_count(conn, table)
            for table in [
                "source_documents",
                "statutes",
                "sections",
                "cases",
                "judgments",
                "document_texts",
                "legal_books",
                "book_chapters",
                "book_chunks",
                "staging_embeddings",
                "staging_extractions",
            ]
        }
    finally:
        conn.close()


def split_case_title(title: str | None) -> tuple[str | None, str | None]:
    clean = re.sub(r"\s+", " ", title or "").strip()
    if not clean:
        return None, None
    match = re.split(r"\s+(?:v\.?|vs\.?|versus)\s+", clean, maxsplit=1, flags=re.IGNORECASE)
    if len(match) == 2:
        return match[0].strip(" .-"), match[1].strip(" .-")
    return clean, None


def ping_postgres(engine: Engine) -> bool:
    sql, _ = require_postgres_dependencies()
    try:
        with engine.connect() as conn:
            conn.execute(sql("SELECT 1"))
        return True
    except Exception:
        return False


def require_id(pg_conn: Any, sql: str, params: dict[str, Any]) -> int | None:
    sql_fn, _ = require_postgres_dependencies()
    row = pg_conn.execute(sql_fn(sql), params).fetchone()
    return int(row[0]) if row is not None else None


def upsert_source_document(pg_conn: Any, row: sqlite3.Row) -> int | None:
    sql, _ = require_postgres_dependencies()
    source_id = require_id(
        pg_conn,
        "SELECT id FROM data_sources WHERE source_code = :source_code",
        {"source_code": row["source_code"]},
    )
    if source_id is None:
        return None
    inserted = pg_conn.execute(
        sql(
            """
            INSERT INTO source_documents
            (source_id, source_url, canonical_url, document_type, local_path, content_hash,
             mime_type, byte_size, http_status, fetched_at, parse_status, error_msg)
            VALUES (:source_id, :source_url, :canonical_url, :document_type, :local_path,
                    :content_hash, :mime_type, :byte_size, :http_status, :fetched_at,
                    :parse_status, :error_msg)
            ON CONFLICT (source_url, content_hash) DO UPDATE SET
              canonical_url = EXCLUDED.canonical_url,
              local_path = EXCLUDED.local_path,
              http_status = EXCLUDED.http_status,
              parse_status = EXCLUDED.parse_status,
              error_msg = EXCLUDED.error_msg
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "source_url": row["source_url"],
            "canonical_url": row["final_url"],
            "document_type": row["document_type"],
            "local_path": row["local_path"],
            "content_hash": row["content_hash"],
            "mime_type": row["mime_type"],
            "byte_size": row["byte_size"],
            "http_status": row["http_status"],
            "fetched_at": row["fetched_at"],
            "parse_status": row["parse_status"] or "PENDING",
            "error_msg": row["error_msg"],
        },
    ).fetchone()
    return int(inserted[0]) if inserted is not None else None


def migrate_judgment_rows(sqlite_conn: sqlite3.Connection, engine: Engine) -> dict[str, int]:
    sql, _ = require_postgres_dependencies()
    migrated = {"source_documents": 0, "cases": 0, "judgments": 0}
    sqlite_conn.row_factory = sqlite3.Row
    if not all(
        sqlite_table_exists(sqlite_conn, table)
        for table in ["source_documents", "cases", "judgments"]
    ):
        return migrated

    with engine.begin() as pg_conn:
        source_map: dict[int, int] = {}
        for row in sqlite_conn.execute("SELECT * FROM source_documents"):
            source_document_id = upsert_source_document(pg_conn, row)
            if source_document_id is not None:
                source_map[int(row["id"])] = source_document_id
                migrated["source_documents"] += 1

        case_rows = sqlite_conn.execute("SELECT * FROM cases ORDER BY id").fetchall()
        case_map: dict[int, int] = {}
        for row in case_rows:
            court_id = require_id(
                pg_conn,
                "SELECT id FROM courts WHERE court_code = :court_code",
                {"court_code": row["court_code"]},
            )
            source_document_id = None
            if sqlite_table_exists(sqlite_conn, "judgments"):
                doc_row = sqlite_conn.execute(
                    "SELECT source_document_id FROM judgments WHERE case_id = ? ORDER BY id LIMIT 1",
                    (row["id"],),
                ).fetchone()
                if doc_row is not None:
                    source_document_id = source_map.get(int(doc_row["source_document_id"]))
            petitioner, respondent = split_case_title(row["title"])
            inserted = pg_conn.execute(
                sql(
                    """
                    INSERT INTO cases
                    (case_number, neutral_citation, court_id, decision_date, status,
                     petitioner, respondent, source_url, source_document_id)
                    VALUES (:case_number, :neutral_citation, :court_id, :decision_date,
                            'DECIDED', :petitioner, :respondent, :source_url,
                            :source_document_id)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "case_number": row["case_number"],
                    "neutral_citation": row["diary_no"] if "INSC" in (row["diary_no"] or "") else None,
                    "court_id": court_id,
                    "decision_date": row["decision_date"],
                    "petitioner": petitioner,
                    "respondent": respondent,
                    "source_url": row["source_url"],
                    "source_document_id": source_document_id,
                },
            ).fetchone()
            if inserted is None:
                existing = pg_conn.execute(
                    sql(
                        """
                        SELECT id FROM cases
                        WHERE court_id IS NOT DISTINCT FROM :court_id
                          AND case_number IS NOT DISTINCT FROM :case_number
                          AND source_url IS NOT DISTINCT FROM :source_url
                        ORDER BY id DESC LIMIT 1
                        """
                    ),
                    {
                        "court_id": court_id,
                        "case_number": row["case_number"],
                        "source_url": row["source_url"],
                    },
                ).fetchone()
                if existing is None:
                    continue
                case_map[int(row["id"])] = int(existing[0])
            else:
                case_map[int(row["id"])] = int(inserted[0])
                migrated["cases"] += 1

        text_by_doc = {}
        if sqlite_table_exists(sqlite_conn, "document_texts"):
            for row in sqlite_conn.execute("SELECT * FROM document_texts"):
                text_by_doc[int(row["source_document_id"])] = row

        for row in sqlite_conn.execute("SELECT * FROM judgments ORDER BY id"):
            case_id = case_map.get(int(row["case_id"]))
            source_document_id = source_map.get(int(row["source_document_id"]))
            if case_id is None or source_document_id is None:
                continue
            source_doc = sqlite_conn.execute(
                "SELECT content_hash FROM source_documents WHERE id = ?",
                (row["source_document_id"],),
            ).fetchone()
            text_row = text_by_doc.get(int(row["source_document_id"]))
            pg_conn.execute(
                sql(
                    """
                    INSERT INTO judgments
                    (case_id, court_id, judgment_date, judgment_type, pdf_url, pdf_hash,
                     raw_text, clean_text, text_extraction_method, page_count, word_count,
                     source_document_id, extraction_status)
                    SELECT :case_id, c.court_id, :judgment_date, :judgment_type, :pdf_url,
                           :pdf_hash, :raw_text, :clean_text, :method, :page_count, :word_count,
                           :source_document_id, :extraction_status
                    FROM cases c
                    WHERE c.id = :case_id
                    ON CONFLICT (pdf_hash) DO UPDATE SET
                      clean_text = EXCLUDED.clean_text,
                      raw_text = EXCLUDED.raw_text,
                      word_count = EXCLUDED.word_count,
                      page_count = EXCLUDED.page_count,
                      extraction_status = EXCLUDED.extraction_status
                    """
                ),
                {
                    "case_id": case_id,
                    "judgment_date": row["judgment_date"],
                    "judgment_type": row["judgment_type"] or "FINAL",
                    "pdf_url": row["pdf_url"],
                    "pdf_hash": source_doc["content_hash"] if source_doc else None,
                    "raw_text": text_row["raw_text"] if text_row else None,
                    "clean_text": text_row["clean_text"] if text_row else None,
                    "method": text_row["extraction_method"] if text_row else None,
                    "page_count": text_row["page_count"] if text_row else row["page_count"],
                    "word_count": text_row["word_count"] if text_row else row["word_count"],
                    "source_document_id": source_document_id,
                    "extraction_status": "DONE" if text_row else "PENDING",
                },
            )
            migrated["judgments"] += 1
    return migrated


def migrate(db_path: str | Path, database_url: str | None, dry_run: bool) -> MigrationSummary:
    path = Path(db_path)
    counts = staging_counts(path)
    errors: list[str] = []
    if not path.exists():
        return MigrationSummary(False, False, dry_run, counts, {}, ["SQLite staging DB missing"])

    if dry_run:
        return MigrationSummary(True, False, True, counts, {}, [])

    try:
        _, engine_factory = require_postgres_dependencies()
    except RuntimeError as exc:
        return MigrationSummary(True, False, False, counts, {}, [str(exc)])

    engine = engine_factory(database_url)
    postgres_available = ping_postgres(engine)
    if not postgres_available:
        errors.append("PostgreSQL is not reachable; run after Docker/PostgreSQL is available.")
        return MigrationSummary(True, postgres_available, dry_run, counts, {}, errors)

    sqlite_conn = sqlite3.connect(path)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        migrated = migrate_judgment_rows(sqlite_conn, engine)
        return MigrationSummary(True, True, False, counts, migrated, errors)
    except Exception as exc:
        errors.append(str(exc))
        return MigrationSummary(True, True, False, counts, {}, errors)
    finally:
        sqlite_conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate staging SQLite judgment rows into production PostgreSQL."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = migrate(args.db_path, args.database_url, args.dry_run)
    print(json.dumps(summary.to_dict(), indent=2))
    return 1 if summary.errors and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
