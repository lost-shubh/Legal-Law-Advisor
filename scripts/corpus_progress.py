from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
TARGET_PATH = ROOT / "config" / "case_corpus_targets.json"


def count(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()[0]
        > 0
    )


def count_table(conn: sqlite3.Connection, table_name: str) -> int:
    if not table_exists(conn, table_name):
        return 0
    return count(conn, f"SELECT COUNT(*) FROM {table_name}")


def load_targets(target_path: str | Path = TARGET_PATH) -> dict[str, Any]:
    return json.loads(Path(target_path).read_text(encoding="utf-8"))


def read_staging_counts(db_path: str | Path = DB_PATH) -> dict[str, int]:
    path = Path(db_path)
    if not path.exists():
        return {
            "judgments": 0,
            "statutes": 0,
            "sections": 0,
            "document_texts": 0,
            "legal_books": 0,
            "book_chunks": 0,
            "staging_embeddings": 0,
            "staging_extractions": 0,
        }

    conn = sqlite3.connect(path)
    try:
        return {
            "judgments": count_table(conn, "judgments"),
            "statutes": count_table(conn, "statutes"),
            "sections": count_table(conn, "sections"),
            "document_texts": count_table(conn, "document_texts"),
            "legal_books": count_table(conn, "legal_books"),
            "book_chunks": count_table(conn, "book_chunks"),
            "staging_embeddings": count_table(conn, "staging_embeddings"),
            "staging_extractions": count_table(conn, "staging_extractions"),
        }
    finally:
        conn.close()


def progress_from_counts(
    current: dict[str, int],
    targets: dict[str, Any],
    *,
    database: str,
    database_available: bool = True,
) -> dict[str, Any]:
    target_judgments = int(targets["target_judgments"])
    current_judgments = int(current.get("judgments", 0))
    return {
        "database_available": database_available,
        "database": database,
        "target_judgments": target_judgments,
        "current_judgments": current_judgments,
        "remaining_judgments": max(target_judgments - current_judgments, 0),
        "judgment_progress_percent": round((current_judgments / target_judgments) * 100, 3)
        if target_judgments
        else 0,
        "current_statutes": int(current.get("statutes", 0)),
        "current_sections": int(current.get("sections", 0)),
        "current_document_texts": int(current.get("document_texts", 0)),
        "current_legal_books": int(current.get("legal_books", 0)),
        "current_book_chunks": int(current.get("book_chunks", 0)),
        "current_embeddings": int(current.get("embeddings", 0)),
        "current_section_embeddings": int(current.get("section_embeddings", 0)),
        "current_judgment_embeddings": int(current.get("judgment_embeddings", 0)),
        "current_book_embeddings": int(current.get("book_embeddings", 0)),
        "current_staging_embeddings": int(current.get("staging_embeddings", 0)),
        "current_staging_extractions": int(current.get("staging_extractions", 0)),
        "court_level_targets": targets["court_level_mix"],
        "domain_targets": targets["domain_mix"],
    }


def normalize_production_progress(progress: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    return progress_from_counts(
        {
            "judgments": int(progress.get("current_judgments", 0)),
            "statutes": int(progress.get("statutes", 0)),
            "sections": int(progress.get("sections", 0)),
            "legal_books": int(progress.get("legal_books", 0)),
            "book_chunks": int(progress.get("book_chunks", 0)),
            "embeddings": int(progress.get("embeddings", 0)),
            "section_embeddings": int(progress.get("section_embeddings", 0)),
            "judgment_embeddings": int(progress.get("judgment_embeddings", 0)),
            "book_embeddings": int(progress.get("book_embeddings", 0)),
        },
        targets,
        database="postgresql",
        database_available=bool(progress.get("database_available", True)),
    )


def build_progress(
    *,
    database_url: str | None = None,
    staging_db_path: str | Path = DB_PATH,
    target_path: str | Path = TARGET_PATH,
    prefer_production: bool = True,
) -> dict[str, Any]:
    targets = load_targets(target_path)
    if prefer_production:
        try:
            from legal_db.retrieval.service import LegalRetrievalService

            production_progress = LegalRetrievalService(
                database_url=database_url,
                staging_db_path=staging_db_path,
            ).progress()
            if production_progress.get("database") == "postgresql" and production_progress.get(
                "database_available"
            ):
                return normalize_production_progress(production_progress, targets)
        except Exception:
            pass
    return progress_from_counts(read_staging_counts(staging_db_path), targets, database="sqlite")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report corpus progress, preferring PostgreSQL production counts when available."
    )
    parser.add_argument("--database-url", help="Optional PostgreSQL DATABASE_URL override.")
    parser.add_argument("--staging-db", default=str(DB_PATH), help="SQLite staging database path.")
    parser.add_argument("--target-config", default=str(TARGET_PATH), help="Corpus target JSON path.")
    parser.add_argument("--no-production", action="store_true", help="Force SQLite staging counts.")
    args = parser.parse_args()

    progress = build_progress(
        database_url=args.database_url,
        staging_db_path=args.staging_db,
        target_path=args.target_config,
        prefer_production=not args.no_production,
    )
    print(json.dumps(progress, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
