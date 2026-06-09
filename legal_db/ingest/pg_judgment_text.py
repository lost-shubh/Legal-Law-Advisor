from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from legal_db.config import settings
from legal_db.pdf.ocr import extract_pdf_text


@dataclass
class PgJudgmentTextBackfillSummary:
    database_available: bool
    target_count: int = 0
    processed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "target_count": self.target_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "errors": self.errors,
            "error": self.error,
        }


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def fetch_pending_judgments(conn: Any, *, limit: int | None = None) -> list[dict[str, Any]]:
    limit_clause = "LIMIT :limit" if limit is not None else ""
    params = {"limit": max(limit or 0, 0)} if limit is not None else {}
    rows = conn.execute(
        sql_text(
            f"""
            SELECT
              j.id AS judgment_id,
              j.source_document_id,
              sd.local_path,
              sd.source_url,
              j.pdf_url
            FROM judgments j
            JOIN source_documents sd ON sd.id = j.source_document_id
            WHERE (j.clean_text IS NULL OR j.word_count IS NULL OR j.word_count = 0)
              AND sd.local_path IS NOT NULL
              AND sd.document_type = 'JUDGMENT_PDF'
            ORDER BY j.id
            {limit_clause}
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def mark_text_backfill_failed(
    conn: Any,
    *,
    judgment_id: int,
    source_document_id: int,
    error: str,
) -> None:
    conn.execute(
        sql_text(
            """
            UPDATE judgments
            SET extraction_status = 'FAILED', updated_at = NOW()
            WHERE id = :judgment_id
            """
        ),
        {"judgment_id": judgment_id},
    )
    conn.execute(
        sql_text(
            """
            UPDATE source_documents
            SET parse_status = 'FAILED', error_msg = :error_msg
            WHERE id = :source_document_id
            """
        ),
        {"source_document_id": source_document_id, "error_msg": error[:1000]},
    )


def store_text_backfill_result(
    conn: Any,
    *,
    judgment_id: int,
    source_document_id: int,
    result: Any,
) -> None:
    conn.execute(
        sql_text(
            """
            UPDATE judgments
            SET raw_text = :raw_text,
                clean_text = :clean_text,
                text_extraction_method = :text_extraction_method,
                page_count = :page_count,
                word_count = :word_count,
                ocr_quality = :ocr_quality,
                extraction_status = 'DONE',
                updated_at = NOW()
            WHERE id = :judgment_id
            """
        ),
        {
            "judgment_id": judgment_id,
            "raw_text": result.raw_text.replace("\x00", ""),
            "clean_text": result.clean_text.replace("\x00", ""),
            "text_extraction_method": result.extraction_method,
            "page_count": result.page_count,
            "word_count": result.word_count,
            "ocr_quality": result.ocr_quality,
        },
    )
    conn.execute(
        sql_text(
            """
            UPDATE source_documents
            SET parse_status = 'PARSED', error_msg = NULL
            WHERE id = :source_document_id
            """
        ),
        {"source_document_id": source_document_id},
    )


def backfill_production_judgment_text(
    *,
    database_url: str | None = None,
    limit: int | None = None,
) -> PgJudgmentTextBackfillSummary:
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            pending = fetch_pending_judgments(conn, limit=limit)
    except Exception as exc:
        return PgJudgmentTextBackfillSummary(database_available=False, error=str(exc))

    summary = PgJudgmentTextBackfillSummary(
        database_available=True,
        target_count=len(pending),
    )
    for row in pending:
        judgment_id = int(row["judgment_id"])
        source_document_id = int(row["source_document_id"])
        path = Path(str(row["local_path"]))
        summary.processed_count += 1
        try:
            if not path.exists():
                raise FileNotFoundError(f"Local PDF missing: {path}")
            result = extract_pdf_text(path)
            with engine.begin() as conn:
                store_text_backfill_result(
                    conn,
                    judgment_id=judgment_id,
                    source_document_id=source_document_id,
                    result=result,
                )
            summary.success_count += 1
        except Exception as exc:
            message = str(exc)
            with engine.begin() as conn:
                mark_text_backfill_failed(
                    conn,
                    judgment_id=judgment_id,
                    source_document_id=source_document_id,
                    error=message,
                )
            summary.failed_count += 1
            summary.errors.append(
                {
                    "judgment_id": judgment_id,
                    "source_document_id": source_document_id,
                    "local_path": str(path),
                    "error": message,
                }
            )
    return summary
