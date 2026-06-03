from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from legal_db.config import settings
from legal_db.quality.production import run_production_quality_checks


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def row_dict(row: Any) -> dict[str, Any]:
    return {key: json_value(value) for key, value in dict(row).items()}


def database_unavailable_payload(error: Exception) -> dict[str, Any]:
    return {"database_available": False, "error": str(error)}


def production_corpus_summary(database_url: str | None = None) -> dict[str, Any]:
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            counts = row_dict(
                conn.execute(
                    sql_text(
                        """
                        SELECT
                          (SELECT COUNT(*) FROM statutes) AS statutes,
                          (SELECT COUNT(*) FROM sections) AS sections,
                          (SELECT COUNT(*) FROM source_documents) AS source_documents,
                          (SELECT COUNT(*) FROM cases) AS cases,
                          (SELECT COUNT(*) FROM judgments) AS judgments,
                          (SELECT COUNT(*) FROM legal_books) AS legal_books,
                          (SELECT COUNT(*) FROM book_chapters) AS book_chapters,
                          (SELECT COUNT(*) FROM book_chunks) AS book_chunks,
                          (SELECT COUNT(*) FROM embeddings) AS embeddings,
                          (SELECT COUNT(*) FROM gazette_notifications) AS gazette_notifications,
                          (SELECT COUNT(*) FROM citations) AS citations,
                          (SELECT COUNT(*) FROM case_citations) AS case_citations
                        """
                    )
                )
                .mappings()
                .one()
            )
            embedding_counts = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT source_type, COUNT(*) AS count, MAX(created_at) AS latest_created_at
                        FROM embeddings
                        GROUP BY source_type
                        ORDER BY source_type
                        """
                    )
                ).mappings()
            ]
            coverage_by_court = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT c.court_code, c.court_name, c.court_level,
                               COUNT(j.id) AS judgments,
                               MAX(j.judgment_date) AS latest_judgment_date
                        FROM courts c
                        LEFT JOIN judgments j ON j.court_id = c.id
                        GROUP BY c.id, c.court_code, c.court_name, c.court_level
                        ORDER BY judgments DESC, c.court_code
                        """
                    )
                ).mappings()
            ]
            extraction_status = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT extraction_status, COUNT(*) AS count
                        FROM judgments
                        GROUP BY extraction_status
                        ORDER BY extraction_status
                        """
                    )
                ).mappings()
            ]
            ocr_quality = row_dict(
                conn.execute(
                    sql_text(
                        """
                        SELECT
                          COUNT(*) FILTER (WHERE ocr_quality IS NULL) AS unknown,
                          COUNT(*) FILTER (WHERE ocr_quality < 0.6) AS low,
                          COUNT(*) FILTER (WHERE ocr_quality >= 0.6 AND ocr_quality < 0.8) AS medium,
                          COUNT(*) FILTER (WHERE ocr_quality >= 0.8) AS high
                        FROM judgments
                        """
                    )
                )
                .mappings()
                .one()
            )
    except Exception as exc:
        return database_unavailable_payload(exc)

    return {
        "database_available": True,
        "counts": counts,
        "embedding_counts": embedding_counts,
        "coverage_by_court": coverage_by_court,
        "extraction_status": extraction_status,
        "ocr_quality": ocr_quality,
    }


def production_source_health(database_url: str | None = None) -> dict[str, Any]:
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            sources = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT ds.source_code, ds.source_name, ds.source_type, ds.base_url,
                               ds.is_official,
                               COUNT(sd.id) AS source_documents,
                               COUNT(sd.id) FILTER (WHERE sd.parse_status = 'PARSED') AS parsed_documents,
                               COUNT(sd.id) FILTER (WHERE sd.parse_status = 'FAILED') AS failed_documents,
                               MAX(sd.fetched_at) AS last_fetched_at,
                               MAX(sd.created_at) AS last_document_created_at
                        FROM data_sources ds
                        LEFT JOIN source_documents sd ON sd.source_id = ds.id
                        GROUP BY ds.id, ds.source_code, ds.source_name, ds.source_type,
                                 ds.base_url, ds.is_official
                        ORDER BY ds.source_type, ds.source_code
                        """
                    )
                ).mappings()
            ]
            recent_scrapes = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT url, http_status, bytes, scraped_at, source_name, error_msg
                        FROM scrape_log
                        ORDER BY scraped_at DESC
                        LIMIT 20
                        """
                    )
                ).mappings()
            ]
            recent_jobs = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT job_code, job_type, source_code, status, target_count,
                               processed_count, success_count, failed_count, skipped_count,
                               started_at, updated_at, finished_at, error_msg
                        FROM ingestion_jobs
                        ORDER BY updated_at DESC, id DESC
                        LIMIT 20
                        """
                    )
                ).mappings()
            ]
    except Exception as exc:
        return database_unavailable_payload(exc)

    return {
        "database_available": True,
        "sources": sources,
        "recent_scrapes": recent_scrapes,
        "recent_jobs": recent_jobs,
    }


def production_operations_status(database_url: str | None = None) -> dict[str, Any]:
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            queues = row_dict(
                conn.execute(
                    sql_text(
                        """
                        SELECT
                          (SELECT COUNT(*) FROM judgments WHERE extraction_status = 'PENDING')
                            AS judgments_pending_extraction,
                          (SELECT COUNT(*) FROM judgments WHERE extraction_status = 'FAILED')
                            AS judgments_failed_extraction,
                          (SELECT COUNT(*) FROM judgments WHERE clean_text IS NULL)
                            AS judgments_pending_text,
                          (SELECT COUNT(*) FROM judgments WHERE ocr_quality IS NOT NULL AND ocr_quality < 0.6)
                            AS judgments_low_ocr_quality
                        """
                    )
                )
                .mappings()
                .one()
            )
            latest_runs = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT target_type, target_id, model_name, prompt_version, status,
                               validation_status, started_at, finished_at, error_msg
                        FROM extraction_runs
                        ORDER BY id DESC
                        LIMIT 20
                        """
                    )
                ).mappings()
            ]
            recent_gazette = [
                row_dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT gazette_number, notification_date, notification_type,
                               act_name, sections_affected, extraction_status, created_at
                        FROM gazette_notifications
                        ORDER BY created_at DESC, id DESC
                        LIMIT 20
                        """
                    )
                ).mappings()
            ]
    except Exception as exc:
        return database_unavailable_payload(exc)

    return {
        "database_available": True,
        "queues": queues,
        "latest_extraction_runs": latest_runs,
        "recent_gazette_notifications": recent_gazette,
    }


def production_admin_panels(database_url: str | None = None) -> dict[str, Any]:
    corpus = production_corpus_summary(database_url)
    sources = production_source_health(database_url)
    operations = production_operations_status(database_url)
    quality = run_production_quality_checks(database_url)
    return {
        "database_available": all(
            panel.get("database_available") for panel in (corpus, sources, operations, quality)
        ),
        "corpus": corpus,
        "sources": sources,
        "operations": operations,
        "quality": quality,
    }
