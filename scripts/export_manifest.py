from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
OUT_PATH = ROOT / "manifests" / "ingestion_summary.json"


def scalar(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    cursor = conn.execute(sql)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_manifest() -> dict[str, object]:
    if not DB_PATH.exists():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "staging_db": str(DB_PATH),
            "status": "missing",
        }

    conn = sqlite3.connect(DB_PATH)
    try:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "staging_db": str(DB_PATH),
            "status": "available",
            "counts": {
                "data_sources": scalar(conn, "SELECT COUNT(*) FROM data_sources"),
                "source_documents": scalar(conn, "SELECT COUNT(*) FROM source_documents"),
                "statutes": scalar(conn, "SELECT COUNT(*) FROM statutes"),
                "sections": scalar(conn, "SELECT COUNT(*) FROM sections"),
                "document_texts": scalar(conn, "SELECT COUNT(*) FROM document_texts"),
                "cases": scalar(conn, "SELECT COUNT(*) FROM cases"),
                "judgments": scalar(conn, "SELECT COUNT(*) FROM judgments"),
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
            ),
            "latest_supreme_court_cases": rows(
                conn,
                """
                SELECT title, case_number, diary_no, decision_date, source_url
                FROM cases
                WHERE court_code = 'SC'
                ORDER BY id DESC
                LIMIT 25
                """,
            ),
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

