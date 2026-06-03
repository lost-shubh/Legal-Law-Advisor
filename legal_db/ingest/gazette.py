from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class GazetteSignal:
    notification_number: str | None
    notification_type: str
    act_name: str | None
    date_text: str | None
    sections_affected: list[str]


@dataclass(frozen=True)
class GazetteIngestionSummary:
    database_available: bool
    notification_id: int | None
    source_document_id: int | None
    notification_type: str | None
    act_name: str | None
    statute_id: int | None
    notification_date: str | None
    sections_affected: list[str]
    updated_statutes: int
    updated_sections: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "notification_id": self.notification_id,
            "source_document_id": self.source_document_id,
            "notification_type": self.notification_type,
            "act_name": self.act_name,
            "statute_id": self.statute_id,
            "notification_date": self.notification_date,
            "sections_affected": self.sections_affected,
            "updated_statutes": self.updated_statutes,
            "updated_sections": self.updated_sections,
            "error": self.error,
        }


NOTIFICATION_RE = re.compile(r"\b(?:S\.O\.|G\.S\.R\.)\s*\d+\s*\(E\)", re.IGNORECASE)
SECTION_RE = re.compile(
    r"(?<!-)\bsection[s]?\s+"
    r"((?:\d+[A-Za-z]?(?:\([^)]+\))?)(?:\s*(?:,|and)\s*\d+[A-Za-z]?(?:\([^)]+\))?)*)",
    re.IGNORECASE,
)
ACT_RE = re.compile(
    r"\bThe\s+([A-Z][A-Za-z\s(),.-]+?(?:Act|Sanhita|Adhiniyam|Code|Rules),\s*\d{4})",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+,\s+\d{4}\b"
    r"|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)
MINISTRY_RE = re.compile(r"\bMINISTRY OF\s+([A-Z][A-Z\s&,-]+)", re.IGNORECASE)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def classify_notification(text: str) -> str:
    lowered = text.lower()
    if "come into force" in lowered or "shall come into force" in lowered:
        return "COMMENCEMENT"
    if "amend" in lowered or "substituted" in lowered or "inserted" in lowered:
        return "AMENDMENT"
    if "repeal" in lowered:
        return "REPEAL"
    if "rules" in lowered:
        return "RULES"
    return "OTHER"


def extract_gazette_signal(text: str) -> GazetteSignal:
    notification_match = NOTIFICATION_RE.search(text)
    sections: list[str] = []
    for match in SECTION_RE.findall(text[:5000]):
        sections.extend([part.strip() for part in re.split(r",|and", match) if part.strip()])
    act_match = ACT_RE.search(text[:5000])
    date_match = DATE_RE.search(text[:5000])
    return GazetteSignal(
        notification_number=notification_match.group(0) if notification_match else None,
        notification_type=classify_notification(text),
        act_name=act_match.group(0).strip() if act_match else None,
        date_text=date_match.group(0) if date_match else None,
        sections_affected=dedupe_sections(sections),
    )


def dedupe_sections(raw_sections: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in raw_sections:
        value = re.sub(r"\s+", " ", raw).strip(" .;:")
        if not value:
            continue
        key = value.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(value)
    return cleaned


def parse_gazette_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    iso_match = re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        return date.fromisoformat(text)
    numeric_match = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", text)
    if numeric_match:
        day, month, year = (int(part) for part in numeric_match.groups())
        return date(year, month, day)
    words_match = re.fullmatch(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+([A-Za-z]+),\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if words_match:
        day_raw, month_raw, year_raw = words_match.groups()
        month = MONTHS.get(month_raw.lower())
        if month is None:
            return None
        return date(int(year_raw), month, int(day_raw))
    return None


def infer_ministry(text: str) -> str | None:
    match = MINISTRY_RE.search(text[:2000])
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip(" ,-").title()


def infer_subject(signal: GazetteSignal) -> str:
    parts = [signal.notification_type]
    if signal.act_name:
        parts.append(signal.act_name)
    if signal.date_text:
        parts.append(signal.date_text)
    return " - ".join(parts)


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.config import settings
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def find_statute_id(conn: Any, act_name: str | None) -> int | None:
    if not act_name:
        return None
    exact = conn.execute(
        sql_text(
            """
            SELECT id
            FROM statutes
            WHERE lower(act_name) = lower(:act_name)
               OR lower(short_title) = lower(:act_name)
            ORDER BY id
            LIMIT 1
            """
        ),
        {"act_name": act_name},
    ).scalar()
    if exact is not None:
        return int(exact)

    compact = re.sub(r"^the\s+", "", act_name, flags=re.IGNORECASE)
    compact = re.sub(r",\s*\d{4}$", "", compact).strip()
    fuzzy = conn.execute(
        sql_text(
            """
            SELECT id
            FROM statutes
            WHERE lower(act_name) LIKE '%' || lower(:act_key) || '%'
            ORDER BY id
            LIMIT 1
            """
        ),
        {"act_key": compact},
    ).scalar()
    return int(fuzzy) if fuzzy is not None else None


def ensure_gazette_source_document(conn: Any, *, source_url: str | None, text: str) -> int | None:
    if not source_url:
        return None
    source_id = conn.execute(
        sql_text("SELECT id FROM data_sources WHERE source_code = 'EGAZETTE' LIMIT 1")
    ).scalar()
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    row = conn.execute(
        sql_text(
            """
            INSERT INTO source_documents
            (source_id, source_url, canonical_url, document_type, content_hash,
             mime_type, byte_size, fetched_at, parse_status)
            VALUES (:source_id, :source_url, :source_url, 'GAZETTE_PDF',
                    :content_hash, 'text/plain', :byte_size, NOW(), 'PARSED')
            ON CONFLICT (source_url, content_hash) DO UPDATE SET
              parse_status = 'PARSED',
              fetched_at = COALESCE(source_documents.fetched_at, EXCLUDED.fetched_at)
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "source_url": source_url,
            "content_hash": content_hash,
            "byte_size": len(text.encode("utf-8")),
        },
    ).scalar()
    return int(row) if row is not None else None


def upsert_gazette_notification(
    *,
    text: str,
    database_url: str | None = None,
    source_url: str | None = None,
    source_document_id: int | None = None,
    update_effective_dates: bool = True,
) -> GazetteIngestionSummary:
    signal = extract_gazette_signal(text)
    notification_date = parse_gazette_date(signal.date_text)
    try:
        engine = make_pg_engine(database_url)
        with engine.begin() as conn:
            resolved_source_document_id = source_document_id or ensure_gazette_source_document(
                conn,
                source_url=source_url,
                text=text,
            )
            statute_id = find_statute_id(conn, signal.act_name)
            existing_id = conn.execute(
                sql_text(
                    """
                    SELECT id
                    FROM gazette_notifications
                    WHERE COALESCE(gazette_number, '') = COALESCE(:gazette_number, '')
                      AND COALESCE(act_name, '') = COALESCE(:act_name, '')
                      AND notification_type = :notification_type
                    ORDER BY id
                    LIMIT 1
                    """
                ),
                {
                    "gazette_number": signal.notification_number,
                    "act_name": signal.act_name,
                    "notification_type": signal.notification_type,
                },
            ).scalar()
            params = {
                "gazette_number": signal.notification_number,
                "notification_date": notification_date,
                "ministry": infer_ministry(text),
                "subject": infer_subject(signal),
                "act_name": signal.act_name,
                "statute_id": statute_id,
                "sections_affected": signal.sections_affected,
                "notification_type": signal.notification_type,
                "source_document_id": resolved_source_document_id,
                "full_text": text,
            }
            if existing_id is None:
                notification_id = conn.execute(
                    sql_text(
                        """
                        INSERT INTO gazette_notifications
                        (gazette_number, notification_date, ministry, subject, act_name,
                         statute_id, sections_affected, notification_type, source_document_id,
                         full_text, extraction_status)
                        VALUES (:gazette_number, :notification_date, :ministry, :subject,
                                :act_name, :statute_id, :sections_affected, :notification_type,
                                :source_document_id, :full_text, 'DONE')
                        RETURNING id
                        """
                    ),
                    params,
                ).scalar()
            else:
                notification_id = conn.execute(
                    sql_text(
                        """
                        UPDATE gazette_notifications
                        SET notification_date = :notification_date,
                            ministry = :ministry,
                            subject = :subject,
                            statute_id = :statute_id,
                            sections_affected = :sections_affected,
                            source_document_id = COALESCE(:source_document_id, source_document_id),
                            full_text = :full_text,
                            extraction_status = 'DONE'
                        WHERE id = :id
                        RETURNING id
                        """
                    ),
                    {**params, "id": existing_id},
                ).scalar()

            updated_statutes = 0
            updated_sections = 0
            if update_effective_dates and statute_id is not None and notification_date is not None:
                if signal.notification_type == "COMMENCEMENT":
                    result = conn.execute(
                        sql_text(
                            """
                            UPDATE statutes
                            SET commenced_on = COALESCE(commenced_on, :notification_date),
                                updated_at = NOW()
                            WHERE id = :statute_id
                            """
                        ),
                        {"statute_id": statute_id, "notification_date": notification_date},
                    )
                    updated_statutes = int(result.rowcount or 0)
                if signal.sections_affected:
                    result = conn.execute(
                        sql_text(
                            """
                            UPDATE sections
                            SET effective_from = COALESCE(effective_from, :notification_date),
                                updated_at = NOW()
                            WHERE statute_id = :statute_id
                              AND section_number = ANY(:sections_affected)
                            """
                        ),
                        {
                            "statute_id": statute_id,
                            "notification_date": notification_date,
                            "sections_affected": signal.sections_affected,
                        },
                    )
                    updated_sections = int(result.rowcount or 0)
    except Exception as exc:
        return GazetteIngestionSummary(
            database_available=False,
            notification_id=None,
            source_document_id=None,
            notification_type=signal.notification_type,
            act_name=signal.act_name,
            statute_id=None,
            notification_date=notification_date.isoformat() if notification_date else None,
            sections_affected=signal.sections_affected,
            updated_statutes=0,
            updated_sections=0,
            error=str(exc),
        )

    return GazetteIngestionSummary(
        database_available=True,
        notification_id=int(notification_id) if notification_id is not None else None,
        source_document_id=resolved_source_document_id,
        notification_type=signal.notification_type,
        act_name=signal.act_name,
        statute_id=statute_id,
        notification_date=notification_date.isoformat() if notification_date else None,
        sections_affected=signal.sections_affected,
        updated_statutes=updated_statutes,
        updated_sections=updated_sections,
    )

