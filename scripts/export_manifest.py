from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
OUT_PATH = ROOT / "manifests" / "ingestion_summary.json"
TARGET_PATH = ROOT / "config" / "case_corpus_targets.json"


def scalar(conn: sqlite3.Connection, sql: str) -> int:
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
    return scalar(conn, f"SELECT COUNT(*) FROM {table_name}")


def rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    cursor = conn.execute(sql)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_manifest() -> dict[str, object]:
    targets = {}
    if TARGET_PATH.exists():
        targets = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    if not DB_PATH.exists():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "staging_db": str(DB_PATH),
            "status": "missing",
            "targets": targets,
        }

    conn = sqlite3.connect(DB_PATH)
    try:
        judgment_count = count_table(conn, "judgments")
        target_judgments = int(targets.get("target_judgments", 0) or 0)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "staging_db": str(DB_PATH),
            "status": "available",
            "targets": targets,
            "counts": {
                "data_sources": count_table(conn, "data_sources"),
                "source_documents": count_table(conn, "source_documents"),
                "statutes": count_table(conn, "statutes"),
                "sections": count_table(conn, "sections"),
                "document_texts": count_table(conn, "document_texts"),
                "cases": count_table(conn, "cases"),
                "judgments": judgment_count,
                "legal_books": count_table(conn, "legal_books"),
                "book_chapters": count_table(conn, "book_chapters"),
                "book_chunks": count_table(conn, "book_chunks"),
                "staging_embeddings": count_table(conn, "staging_embeddings"),
            },
            "progress": {
                "target_judgments": target_judgments,
                "current_judgments": judgment_count,
                "remaining_judgments": max(target_judgments - judgment_count, 0)
                if target_judgments
                else None,
                "judgment_progress_percent": round((judgment_count / target_judgments) * 100, 3)
                if target_judgments
                else None,
            },
            "priority_acts": rows(
                conn,
                """
                SELECT
                  s.short_title,
                  s.act_name,
                  s.year,
                  COUNT(DISTINCT d.id) AS pdf_documents,
                  MAX(t.word_count) AS max_word_count,
                  COUNT(DISTINCT sec.id) AS extracted_sections
                FROM statutes s
                LEFT JOIN source_documents d
                  ON d.title = s.act_name AND d.document_type = 'ACT_PDF'
                LEFT JOIN document_texts t
                  ON t.source_document_id = d.id
                LEFT JOIN sections sec
                  ON sec.statute_id = s.id
                GROUP BY s.id
                ORDER BY s.id
                """,
            )
            if table_exists(conn, "statutes")
            else [],
            "latest_supreme_court_cases": rows(
                conn,
                """
                SELECT title, case_number, diary_no, decision_date, source_url
                FROM cases
                WHERE court_code = 'SC'
                ORDER BY id DESC
                LIMIT 25
                """,
            )
            if table_exists(conn, "cases")
            else [],
            "legal_books": rows(
                conn,
                """
                SELECT title, material_type, source_code, source_url
                FROM legal_books
                ORDER BY id
                LIMIT 50
                """,
            )
            if table_exists(conn, "legal_books")
            else [],
        }
    finally:
        conn.close()


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(build_manifest(), indent=2), encoding="utf-8")
    print(str(OUT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
