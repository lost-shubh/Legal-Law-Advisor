from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legal_db.config import settings
from legal_db.citations.parser import extract_citations
from legal_db.ingest.jobs import DEFAULT_DB_PATH


LOCAL_EXTRACTION_MODEL = "local-rule-extractor-v1"
PROMPT_VERSION = "judgment_v1"


ALLOWED_OUTCOMES = {
    "ALLOWED",
    "DISMISSED",
    "PARTLY_ALLOWED",
    "CONVICTED",
    "ACQUITTED",
    "BAIL_GRANTED",
    "BAIL_REJECTED",
    "SETTLED",
    "REMANDED",
    "COMPENSATION_AWARDED",
    "UNKNOWN",
}


@dataclass(frozen=True)
class ExtractionResult:
    payload: dict[str, Any]
    model: str
    validation_errors: list[str]


@dataclass(frozen=True)
class StagingExtractionSummary:
    database_available: bool
    target_count: int
    processed_count: int
    success_count: int
    failed_count: int
    model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "target_count": self.target_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "model": self.model,
        }


def build_extraction_prompt(clean_text: str) -> str:
    clipped = clean_text[:12000]
    return f"""
Extract structured information from this Indian court judgment.
Return only valid JSON with these keys:
acts_cited, outcome, issue_tags, dispute_summary, timeline, key_evidence,
allegations, defence, key_arguments, reasoning, compensation_awarded.

Use null when a field is unavailable. Do not guess values not supported by text.

JUDGMENT TEXT:
{clipped}
""".strip()


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def split_sentences(text: str, limit: int = 8) -> list[str]:
    clean = normalize_space(text)
    if not clean:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    return [sentence.strip() for sentence in sentences if sentence.strip()][:limit]


def snippet_around(text: str, keywords: list[str], max_chars: int = 700) -> str | None:
    clean = normalize_space(text)
    lowered = clean.lower()
    positions = [lowered.find(keyword.lower()) for keyword in keywords if keyword.lower() in lowered]
    if not positions:
        return None
    start = max(min(positions) - max_chars // 3, 0)
    end = min(start + max_chars, len(clean))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end].strip()}{suffix}"


KNOWN_ACT_PATTERNS: dict[str, list[str]] = {
    "Indian Penal Code, 1860": ["indian penal code", "ipc"],
    "Code of Criminal Procedure, 1973": ["code of criminal procedure", "crpc", "cr.p.c"],
    "Bharatiya Nyaya Sanhita, 2023": ["bharatiya nyaya sanhita", "bns"],
    "Bharatiya Nagarik Suraksha Sanhita, 2023": [
        "bharatiya nagarik suraksha sanhita",
        "bnss",
    ],
    "Bharatiya Sakshya Adhiniyam, 2023": ["bharatiya sakshya adhiniyam", "bsa"],
    "Negotiable Instruments Act, 1881": ["negotiable instruments act", "ni act"],
    "Constitution of India": ["constitution of india", "article"],
    "Consumer Protection Act, 2019": ["consumer protection act"],
    "Information Technology Act, 2000": ["information technology act", "it act"],
    "Motor Vehicles Act, 1988": ["motor vehicles act"],
    "Transfer of Property Act, 1882": ["transfer of property act"],
}


ISSUE_TAG_KEYWORDS: dict[str, list[str]] = {
    "CRIMINAL": [
        "criminal",
        "accused",
        "fir",
        "prosecution",
        "prosecuted",
        "offence",
        "conviction",
        "indian penal code",
        "ipc",
    ],
    "CHEQUE_BOUNCE_NI_138": ["cheque", "dishonour", "section 138", "bank return memo"],
    "FAMILY": ["marriage", "divorce", "maintenance", "custody", "matrimonial"],
    "PROPERTY": ["property", "possession", "title", "sale deed", "tenant"],
    "CONSUMER": ["consumer", "deficiency", "refund", "warranty"],
    "LABOUR_EMPLOYMENT": ["employee", "employer", "wages", "termination", "salary"],
    "CONSTITUTIONAL_WRIT": ["writ petition", "article 226", "article 32", "mandamus"],
    "COMMERCIAL_CONTRACT_ARBITRATION": ["contract", "arbitration", "loan", "bank", "drt"],
}


DATE_RE = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|20\d{2}-\d{2}-\d{2})\b"
)
SECTION_RE = re.compile(
    r"\b(?:section|sections|sec\.?)\s+([0-9A-Za-z(),./ -]{1,80})",
    re.IGNORECASE,
)
ACT_RE = re.compile(r"\b[A-Z][A-Za-z\s().,-]+Act,\s*\d{4}\b")
MONEY_RE = re.compile(r"\b(?:Rs\.?|INR)\s*[0-9][0-9,]*(?:\.\d+)?\b", re.IGNORECASE)


def extract_acts_cited(text: str) -> list[str]:
    lowered = text.lower()
    acts: set[str] = set()
    for act_name, keywords in KNOWN_ACT_PATTERNS.items():
        if any(keyword in lowered for keyword in keywords):
            acts.add(act_name)
    acts.update(normalize_space(match.group(0)) for match in ACT_RE.finditer(text))
    return sorted(acts)


def extract_sections_cited(text: str, limit: int = 40) -> list[str]:
    sections: list[str] = []
    seen: set[str] = set()
    for match in SECTION_RE.finditer(text[:20000]):
        raw = normalize_space(match.group(1)).strip(" .,:;")
        if not raw:
            continue
        for part in re.split(r",| and ", raw):
            section = normalize_space(part).strip(" .,:;")
            if not section or len(section) > 30:
                continue
            lowered = section.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            sections.append(section)
            if len(sections) >= limit:
                return sections
    return sections


def extract_issue_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags = [
        tag
        for tag, keywords in ISSUE_TAG_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return tags or ["UNKNOWN"]


def infer_outcome(text: str) -> str:
    lowered = text.lower()
    tail = lowered[-6000:]
    if "partly allowed" in tail or "allowed in part" in tail:
        return "PARTLY_ALLOWED"
    if re.search(r"\b(appeal|petition|application)\s+(?:is\s+)?allowed\b", tail):
        return "ALLOWED"
    if re.search(r"\b(appeal|petition|application)\s+(?:is\s+)?dismissed\b", tail):
        return "DISMISSED"
    if "bail is granted" in tail or "granted bail" in tail:
        return "BAIL_GRANTED"
    if "bail is rejected" in tail or "bail application is dismissed" in tail:
        return "BAIL_REJECTED"
    if "acquitted" in tail or "conviction is set aside" in tail:
        return "ACQUITTED"
    if "convicted" in tail and "set aside" not in tail:
        return "CONVICTED"
    if "settlement" in tail or "settled" in tail or "compromise" in tail:
        return "SETTLED"
    if "remanded" in tail or "remand" in tail:
        return "REMANDED"
    if "compensation" in tail and MONEY_RE.search(tail):
        return "COMPENSATION_AWARDED"
    return "UNKNOWN"


def extract_timeline(text: str, limit: int = 12) -> list[dict[str, str]]:
    clean = normalize_space(text)
    timeline: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in DATE_RE.finditer(clean[:30000]):
        date_text = match.group(0)
        if date_text in seen:
            continue
        seen.add(date_text)
        start = max(match.start() - 120, 0)
        end = min(match.end() + 180, len(clean))
        timeline.append({"date_text": date_text, "context": clean[start:end].strip()})
        if len(timeline) >= limit:
            break
    return timeline


def local_extract_judgment(clean_text: str, model: str = LOCAL_EXTRACTION_MODEL) -> ExtractionResult:
    text = normalize_space(clean_text)
    citations = [
        {
            "citation": item.citation,
            "reporter": item.reporter,
            "year": item.year,
        }
        for item in extract_citations(text)
    ]
    payload: dict[str, Any] = {
        "acts_cited": extract_acts_cited(text),
        "sections_cited": extract_sections_cited(text),
        "issue_tags": extract_issue_tags(text),
        "dispute_summary": " ".join(split_sentences(text, limit=3)) or None,
        "timeline": extract_timeline(text),
        "allegations": snippet_around(text, ["alleged", "allegation", "complaint", "prosecution"]),
        "defence": snippet_around(text, ["defence", "defense", "appellant submitted", "respondent submitted"]),
        "evidence_discussed": snippet_around(text, ["evidence", "witness", "document", "exhibit"]),
        "key_evidence": snippet_around(text, ["evidence", "witness", "document", "bank", "memo"]),
        "key_arguments": snippet_around(text, ["submitted", "contended", "argued", "counsel"]),
        "reasoning": snippet_around(text, ["we are of the view", "held", "considered", "therefore"]),
        "outcome": infer_outcome(text),
        "compensation_awarded": (MONEY_RE.search(text).group(0) if MONEY_RE.search(text) else None),
        "citations": citations,
    }
    return ExtractionResult(
        payload=payload,
        model=model,
        validation_errors=validate_payload(payload, text),
    )


def validate_payload(payload: dict[str, Any], source_text: str) -> list[str]:
    errors: list[str] = []
    outcome = payload.get("outcome")
    if outcome and outcome not in ALLOWED_OUTCOMES:
        errors.append(f"Unsupported outcome: {outcome}")
    amount = payload.get("compensation_awarded")
    if amount not in (None, "") and str(amount).replace(",", "") not in source_text.replace(",", ""):
        errors.append("Compensation amount does not appear literally in source text")
    if not isinstance(payload.get("issue_tags", []), list):
        errors.append("issue_tags must be a list")
    if not isinstance(payload.get("acts_cited", []), list):
        errors.append("acts_cited must be a list")
    return errors


def ensure_staging_extraction_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_extractions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          judgment_id INTEGER NOT NULL,
          case_id INTEGER,
          source_document_id INTEGER,
          model_name TEXT NOT NULL,
          prompt_version TEXT NOT NULL,
          status TEXT NOT NULL,
          payload_json TEXT,
          validation_errors_json TEXT,
          content_hash TEXT,
          error_msg TEXT,
          extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(judgment_id, model_name, prompt_version)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_staging_extractions_status
        ON staging_extractions(status)
        """
    )
    conn.commit()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()[0]
        > 0
    )


def _content_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_staging_judgments(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    limit: int | None = None,
    model: str = LOCAL_EXTRACTION_MODEL,
) -> StagingExtractionSummary:
    path = Path(db_path)
    if not path.exists():
        return StagingExtractionSummary(False, 0, 0, 0, 0, model)
    conn = sqlite3.connect(path)
    try:
        required = ["judgments", "document_texts"]
        if not all(_table_exists(conn, table_name) for table_name in required):
            return StagingExtractionSummary(True, 0, 0, 0, 0, model)
        ensure_staging_extraction_tables(conn)
        sql = """
            SELECT j.id, j.case_id, j.source_document_id, dt.clean_text
            FROM judgments j
            JOIN document_texts dt ON dt.source_document_id = j.source_document_id
            WHERE dt.clean_text IS NOT NULL
            ORDER BY j.id
        """
        if limit is not None:
            rows = conn.execute(sql + " LIMIT ?", (max(limit, 0),)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()

        success = failed = 0
        for judgment_id, case_id, source_document_id, clean_text in rows:
            try:
                result = local_extract_judgment(clean_text or "", model=model)
                status = "DONE" if not result.validation_errors else "NEEDS_REVIEW"
                conn.execute(
                    """
                    INSERT INTO staging_extractions
                    (judgment_id, case_id, source_document_id, model_name, prompt_version,
                     status, payload_json, validation_errors_json, content_hash, error_msg,
                     extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                    ON CONFLICT(judgment_id, model_name, prompt_version)
                    DO UPDATE SET case_id = excluded.case_id,
                                  source_document_id = excluded.source_document_id,
                                  status = excluded.status,
                                  payload_json = excluded.payload_json,
                                  validation_errors_json = excluded.validation_errors_json,
                                  content_hash = excluded.content_hash,
                                  error_msg = NULL,
                                  extracted_at = excluded.extracted_at
                    """,
                    (
                        judgment_id,
                        case_id,
                        source_document_id,
                        result.model,
                        PROMPT_VERSION,
                        status,
                        json.dumps(result.payload, sort_keys=True),
                        json.dumps(result.validation_errors),
                        _content_hash(clean_text or ""),
                        datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    ),
                )
                success += 1
            except Exception as exc:
                failed += 1
                conn.execute(
                    """
                    INSERT INTO staging_extractions
                    (judgment_id, case_id, source_document_id, model_name, prompt_version,
                     status, error_msg, extracted_at)
                    VALUES (?, ?, ?, ?, ?, 'FAILED', ?, ?)
                    ON CONFLICT(judgment_id, model_name, prompt_version)
                    DO UPDATE SET status = 'FAILED',
                                  error_msg = excluded.error_msg,
                                  extracted_at = excluded.extracted_at
                    """,
                    (
                        judgment_id,
                        case_id,
                        source_document_id,
                        model,
                        PROMPT_VERSION,
                        str(exc),
                        datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    ),
                )
        conn.commit()
        return StagingExtractionSummary(True, len(rows), len(rows), success, failed, model)
    finally:
        conn.close()


def staging_extraction_status(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    path = Path(db_path)
    if not path.exists():
        return {"database_available": False, "extractions": {"total": 0, "by_status": {}}}
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        if not _table_exists(conn, "staging_extractions"):
            return {"database_available": True, "extractions": {"total": 0, "by_status": {}}}
        by_status = {
            row["status"]: row["count"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS count FROM staging_extractions GROUP BY status"
            )
        }
        recent = [
            dict(row)
            for row in conn.execute(
                """
                SELECT judgment_id, case_id, model_name, prompt_version, status, extracted_at
                FROM staging_extractions
                ORDER BY id DESC
                LIMIT 10
                """
            )
        ]
        return {
            "database_available": True,
            "extractions": {"total": sum(by_status.values()), "by_status": by_status},
            "recent_extractions": recent,
        }
    finally:
        conn.close()


def extract_with_openai(clean_text: str, model: str | None = None) -> ExtractionResult:
    from openai import OpenAI

    selected_model = model or settings.openai_extraction_model
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=selected_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a legal data extraction assistant for Indian courts. "
                    "Return only valid JSON."
                ),
            },
            {"role": "user", "content": build_extraction_prompt(clean_text)},
        ],
    )
    raw = response.output_text
    payload = json.loads(raw)
    return ExtractionResult(
        payload=payload,
        model=selected_model,
        validation_errors=validate_payload(payload, clean_text),
    )

