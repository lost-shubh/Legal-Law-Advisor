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
                "judgments": count(conn, "SELECT COUNT(*) FROM judgments"),
                "statutes": count(conn, "SELECT COUNT(*) FROM statutes"),
                "sections": count(conn, "SELECT COUNT(*) FROM sections"),
                "document_texts": count(conn, "SELECT COUNT(*) FROM document_texts"),
                "legal_books": count(conn, "SELECT COUNT(*) FROM legal_books")
                if table_exists(conn, "legal_books")
                else 0,
                "book_chunks": count(conn, "SELECT COUNT(*) FROM book_chunks")
                if table_exists(conn, "book_chunks")
                else 0,
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
        "court_level_targets": targets["court_level_mix"],
        "domain_targets": targets["domain_mix"],
    }
    print(json.dumps(progress, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
