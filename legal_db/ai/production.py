from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from legal_db.ai.extract import (
    LOCAL_EXTRACTION_MODEL,
    PROMPT_VERSION,
    local_extract_judgment,
)
from legal_db.config import settings
from legal_db.pdf.ocr import should_extract_for_ai


@dataclass(frozen=True)
class ProductionExtractionSummary:
    database_available: bool
    target_count: int
    processed_count: int
    success_count: int
    failed_count: int
    model: str
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "target_count": self.target_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "model": self.model,
            "errors": self.errors or [],
        }


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def parse_money_to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = re.sub(r"(?i)\b(rs\.?|inr)\b", "", value).replace(",", "").strip()
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return Decimal(match.group(0)) if match else None


def find_section_id(pg_conn: Any, raw_number: str, acts_cited: list[str]) -> tuple[int | None, int | None]:
    raw = raw_number.strip()
    if not raw:
        return None, None
    for act_name in acts_cited or [None]:
        row = pg_conn.execute(
            sql_text(
                """
                SELECT s.id AS section_id, s.statute_id
                FROM sections s
                JOIN statutes st ON st.id = s.statute_id
                WHERE lower(s.section_number) = lower(:section_number)
                  AND (:act_name IS NULL OR lower(st.act_name) = lower(:act_name))
                ORDER BY CASE WHEN :act_name IS NULL THEN 1 ELSE 0 END, s.id
                LIMIT 1
                """
            ),
            {"section_number": raw, "act_name": act_name},
        ).mappings().fetchone()
        if row is not None:
            return int(row["section_id"]), int(row["statute_id"])
    return None, None


def insert_extraction_run(
    pg_conn: Any,
    *,
    judgment_id: int,
    model: str,
    status: str,
    validation_status: str,
    error_msg: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    pg_conn.execute(
        sql_text(
            """
            INSERT INTO extraction_runs
            (target_type, target_id, model_name, model_version, prompt_version, status,
             validation_status, error_msg, started_at, finished_at)
            VALUES ('JUDGMENT', :judgment_id, :model, :model_version, :prompt_version,
                    :status, :validation_status, :error_msg, :started_at, :finished_at)
            """
        ),
        {
            "judgment_id": judgment_id,
            "model": model,
            "model_version": "v1",
            "prompt_version": PROMPT_VERSION,
            "status": status,
            "validation_status": validation_status,
            "error_msg": error_msg,
            "started_at": now,
            "finished_at": now,
        },
    )


def store_extraction_payload(
    pg_conn: Any,
    *,
    case_id: int,
    judgment_id: int,
    payload: dict[str, Any],
    model: str,
    validation_errors: list[str],
) -> None:
    validation_status = "AUTO_VALIDATED" if not validation_errors else "UNVALIDATED"
    pg_conn.execute(sql_text("DELETE FROM outcomes WHERE judgment_id = :judgment_id"), {"judgment_id": judgment_id})
    pg_conn.execute(sql_text("DELETE FROM case_facts WHERE judgment_id = :judgment_id"), {"judgment_id": judgment_id})
    pg_conn.execute(
        sql_text("DELETE FROM case_sections WHERE case_id = :case_id AND source = 'AI_EXTRACTED'"),
        {"case_id": case_id},
    )

    compensation = parse_money_to_decimal(payload.get("compensation_awarded"))
    pg_conn.execute(
        sql_text(
            """
            INSERT INTO outcomes
            (case_id, judgment_id, result, compensation, confidence)
            VALUES (:case_id, :judgment_id, :result, :compensation, :confidence)
            """
        ),
        {
            "case_id": case_id,
            "judgment_id": judgment_id,
            "result": payload.get("outcome") or "UNKNOWN",
            "compensation": compensation,
            "confidence": Decimal("0.75") if not validation_errors else Decimal("0.45"),
        },
    )

    for issue_tag in payload.get("issue_tags") or ["UNKNOWN"]:
        pg_conn.execute(
            sql_text(
                """
                INSERT INTO case_issues (case_id, issue_tag, confidence, source)
                VALUES (:case_id, :issue_tag, :confidence, 'AI_EXTRACTED')
                ON CONFLICT (case_id, issue_tag) DO UPDATE SET
                  confidence = EXCLUDED.confidence,
                  source = EXCLUDED.source
                """
            ),
            {"case_id": case_id, "issue_tag": issue_tag, "confidence": Decimal("0.70")},
        )

    acts_cited = payload.get("acts_cited") or []
    for raw_number in payload.get("sections_cited") or []:
        section_id, statute_id = find_section_id(pg_conn, str(raw_number), acts_cited)
        pg_conn.execute(
            sql_text(
                """
                INSERT INTO case_sections
                (case_id, statute_id, section_id, raw_act_name, raw_section_number,
                 mention_type, confidence, source)
                VALUES (:case_id, :statute_id, :section_id, :raw_act_name,
                        :raw_section_number, 'REFERRED', :confidence, 'AI_EXTRACTED')
                """
            ),
            {
                "case_id": case_id,
                "statute_id": statute_id,
                "section_id": section_id,
                "raw_act_name": acts_cited[0] if acts_cited else None,
                "raw_section_number": str(raw_number),
                "confidence": Decimal("0.60") if section_id else Decimal("0.35"),
            },
        )

    pg_conn.execute(
        sql_text(
            """
            INSERT INTO case_facts
            (judgment_id, dispute_summary, timeline, allegations, defence, evidence_discussed,
             key_arguments, reasoning, validation_status, extracted_at, model_used, model_version)
            VALUES (:judgment_id, :dispute_summary, CAST(:timeline AS jsonb), :allegations,
                    :defence, :evidence_discussed, :key_arguments, :reasoning,
                    :validation_status, NOW(), :model, 'v1')
            """
        ),
        {
            "judgment_id": judgment_id,
            "dispute_summary": payload.get("dispute_summary"),
            "timeline": json.dumps(payload.get("timeline") or []),
            "allegations": payload.get("allegations"),
            "defence": payload.get("defence"),
            "evidence_discussed": payload.get("evidence_discussed"),
            "key_arguments": payload.get("key_arguments"),
            "reasoning": payload.get("reasoning"),
            "validation_status": validation_status,
            "model": model,
        },
    )


def extract_production_judgments(
    *,
    database_url: str | None = None,
    limit: int | None = None,
    model: str = LOCAL_EXTRACTION_MODEL,
) -> ProductionExtractionSummary:
    errors: list[str] = []
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
    except Exception as exc:
        return ProductionExtractionSummary(False, 0, 0, 0, 0, model, [str(exc)])

    sql = """
        SELECT id, case_id, clean_text, word_count, ocr_quality
        FROM judgments
        WHERE clean_text IS NOT NULL
        ORDER BY id
    """
    if limit is not None:
        sql += " LIMIT :limit"

    processed = success = failed = 0
    with engine.begin() as pg_conn:
        rows = pg_conn.execute(
            sql_text(sql),
            {"limit": max(limit or 0, 0)} if limit is not None else {},
        ).mappings().all()
        for row in rows:
            processed += 1
            judgment_id = int(row["id"])
            case_id = int(row["case_id"])
            try:
                can_extract, skip_reason = should_extract_for_ai(
                    int(row["word_count"] or len((row["clean_text"] or "").split())),
                    float(row["ocr_quality"]) if row["ocr_quality"] is not None else None,
                )
                if not can_extract:
                    pg_conn.execute(
                        sql_text("UPDATE judgments SET extraction_status = 'SKIPPED' WHERE id = :id"),
                        {"id": judgment_id},
                    )
                    insert_extraction_run(
                        pg_conn,
                        judgment_id=judgment_id,
                        model=model,
                        status="SKIPPED",
                        validation_status="UNVALIDATED",
                        error_msg=skip_reason,
                    )
                    success += 1
                    continue
                result = local_extract_judgment(row["clean_text"] or "", model=model)
                store_extraction_payload(
                    pg_conn,
                    case_id=case_id,
                    judgment_id=judgment_id,
                    payload=result.payload,
                    model=result.model,
                    validation_errors=result.validation_errors,
                )
                status = "DONE" if not result.validation_errors else "NEEDS_REVIEW"
                pg_conn.execute(
                    sql_text("UPDATE judgments SET extraction_status = :status WHERE id = :id"),
                    {"status": status, "id": judgment_id},
                )
                insert_extraction_run(
                    pg_conn,
                    judgment_id=judgment_id,
                    model=result.model,
                    status="DONE",
                    validation_status="AUTO_VALIDATED" if not result.validation_errors else "UNVALIDATED",
                    error_msg="; ".join(result.validation_errors) if result.validation_errors else None,
                )
                success += 1
            except Exception as exc:
                failed += 1
                errors.append(f"judgment_id={judgment_id}: {exc}")
                pg_conn.execute(
                    sql_text("UPDATE judgments SET extraction_status = 'FAILED' WHERE id = :id"),
                    {"id": judgment_id},
                )
                insert_extraction_run(
                    pg_conn,
                    judgment_id=judgment_id,
                    model=model,
                    status="FAILED",
                    validation_status="UNVALIDATED",
                    error_msg=str(exc),
                )

    return ProductionExtractionSummary(True, processed, processed, success, failed, model, errors)


def production_extraction_status(database_url: str | None = None) -> dict[str, Any]:
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            by_status = {
                row["extraction_status"]: int(row["count"])
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
            }
            counts = conn.execute(
                sql_text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM outcomes) AS outcomes,
                      (SELECT COUNT(*) FROM case_issues) AS case_issues,
                      (SELECT COUNT(*) FROM case_sections) AS case_sections,
                      (SELECT COUNT(*) FROM case_facts) AS case_facts,
                      (SELECT COUNT(*) FROM extraction_runs) AS extraction_runs
                    """
                )
            ).mappings().one()
            recent = [
                dict(row)
                for row in conn.execute(
                    sql_text(
                        """
                        SELECT target_id AS judgment_id, model_name, prompt_version, status, finished_at
                        FROM extraction_runs
                        WHERE target_type = 'JUDGMENT'
                        ORDER BY id DESC
                        LIMIT 10
                        """
                    )
                ).mappings()
            ]
    except Exception as exc:
        return {"database_available": False, "extractions": {"total": 0, "by_status": {}, "error": str(exc)}}

    return {
        "database_available": True,
        "database": "postgresql",
        "extractions": {
            "total": sum(by_status.values()),
            "by_status": by_status,
            "outcomes": int(counts["outcomes"] or 0),
            "case_issues": int(counts["case_issues"] or 0),
            "case_sections": int(counts["case_sections"] or 0),
            "case_facts": int(counts["case_facts"] or 0),
            "extraction_runs": int(counts["extraction_runs"] or 0),
        },
        "recent_extractions": recent,
    }
