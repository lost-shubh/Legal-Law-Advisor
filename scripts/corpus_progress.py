from __future__ import annotations

import json
import sqlite3
from pathlib import Path


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


def main() -> int:
    targets = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    target_judgments = int(targets["target_judgments"])

    if not DB_PATH.exists():
        current = {
            "judgments": 0,
            "statutes": 0,
            "sections": 0,
            "document_texts": 0,
        }
    else:
        conn = sqlite3.connect(DB_PATH)
        try:
            current = {
                "judgments": count_table(conn, "judgments"),
                "statutes": count_table(conn, "statutes"),
                "sections": count_table(conn, "sections"),
                "document_texts": count_table(conn, "document_texts"),
                "legal_books": count_table(conn, "legal_books"),
                "book_chunks": count_table(conn, "book_chunks"),
                "staging_embeddings": count_table(conn, "staging_embeddings"),
            }
        finally:
            conn.close()

    progress = {
        "target_judgments": target_judgments,
        "current_judgments": current["judgments"],
        "remaining_judgments": max(target_judgments - current["judgments"], 0),
        "judgment_progress_percent": round((current["judgments"] / target_judgments) * 100, 3),
        "current_statutes": current["statutes"],
        "current_sections": current["sections"],
        "current_document_texts": current["document_texts"],
        "current_legal_books": current.get("legal_books", 0),
        "current_book_chunks": current.get("book_chunks", 0),
        "current_staging_embeddings": current.get("staging_embeddings", 0),
        "court_level_targets": targets["court_level_mix"],
        "domain_targets": targets["domain_mix"],
    }
    print(json.dumps(progress, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
