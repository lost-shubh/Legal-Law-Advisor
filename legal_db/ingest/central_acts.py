from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from legal_db.config import settings
from legal_db.pdf.ocr import clean_ocr_text, estimate_text_quality, extract_text_pymupdf


DEFAULT_COLLECTION_URL = "https://www.indiacode.nic.in/handle/123456789/1362"
DEFAULT_SOURCE_CODE = "INDIA_CODE_CENTRAL_ACTS"
DEFAULT_SOURCE_NAME = "India Code Central Acts"

SECTION_HEADER_RE = re.compile(
    r"(?ms)^\s*([0-9]+[A-Z]{0,4})\.\s+([^\n]{3,220})\n"
    r"(.*?)(?=^\s*[0-9]+[A-Z]{0,4}\.\s+[^\n]{3,220}\n|\Z)"
)
ACT_BODY_MARKERS = (
    re.compile(r"(?im)^\s*ACT\s+NO\.\s+\d+\s+OF\s+\d{4}"),
    re.compile(r"(?i)\bAn\s+Act\s+to\b"),
)
FOOTNOTE_TITLE_RE = re.compile(
    r"(?i)^(?:subs?\.|ins\.|omitted|section\s+\d|sub-section|clause|"
    r"the act has been|vide\s+notification|for\s+statement|words?\s+)"
)


@dataclass(frozen=True)
class CentralActCandidate:
    index: int
    handle: str
    act_id: str | None
    act_number: str | None
    act_year: int | None
    title: str
    item_url: str | None
    pdf_url: str
    path: Path
    content_hash: str | None
    byte_size: int | None
    downloaded_at: datetime | None


@dataclass
class CentralActsImportSummary:
    database_available: bool
    scanned_rows: int = 0
    eligible_files: int = 0
    imported_source_documents: int = 0
    imported_statutes: int = 0
    imported_sections: int = 0
    extracted_words: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    dry_run: bool = False
    source_code: str = DEFAULT_SOURCE_CODE
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "scanned_rows": self.scanned_rows,
            "eligible_files": self.eligible_files,
            "imported_source_documents": self.imported_source_documents,
            "imported_statutes": self.imported_statutes,
            "imported_sections": self.imported_sections,
            "extracted_words": self.extracted_words,
            "skipped": self.skipped,
            "failed": self.failed,
            "dry_run": self.dry_run,
            "source_code": self.source_code,
            "error": self.error,
        }


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_act_title(value: str | None) -> str:
    title = normalize_space(value)
    if re.search(r"\d{4}\.$", title):
        title = title[:-1]
    return title


def parse_int(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_manifest_candidates(
    folder: str | Path,
    *,
    manifest_name: str = "manifest.csv",
) -> tuple[list[CentralActCandidate], list[dict[str, str]], int]:
    root = Path(folder)
    manifest_path = root / manifest_name
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    candidates: list[CentralActCandidate] = []
    skipped: list[dict[str, str]] = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        path_value = row.get("file_path") or ""
        path = Path(path_value) if path_value else root / ""
        if not path.is_absolute():
            path = root / path
        if row.get("status") and row.get("status") != "downloaded":
            skipped.append({"path": str(path), "reason": f"status={row.get('status')}"})
            continue
        if path.suffix.lower() != ".pdf":
            skipped.append({"path": str(path), "reason": "not a PDF"})
            continue
        if not path.exists():
            skipped.append({"path": str(path), "reason": "file missing"})
            continue
        pdf_url = normalize_space(row.get("pdf_url"))
        if not pdf_url:
            skipped.append({"path": str(path), "reason": "missing pdf_url"})
            continue
        title = normalize_act_title(row.get("short_title"))
        if not title:
            skipped.append({"path": str(path), "reason": "missing short_title"})
            continue
        candidates.append(
            CentralActCandidate(
                index=parse_int(row.get("index")) or len(candidates) + 1,
                handle=normalize_space(row.get("handle")),
                act_id=normalize_space(row.get("act_id")) or None,
                act_number=normalize_space(row.get("act_number")) or None,
                act_year=parse_int(row.get("act_year")),
                title=title,
                item_url=normalize_space(row.get("item_url")) or None,
                pdf_url=pdf_url,
                path=path,
                content_hash=(normalize_space(row.get("sha256")).lower() or None),
                byte_size=parse_int(row.get("bytes")),
                downloaded_at=parse_datetime(row.get("downloaded_at")),
            )
        )
    return candidates, skipped, len(rows)


def act_body_start(text_value: str) -> int:
    starts = []
    for pattern in ACT_BODY_MARKERS:
        match = pattern.search(text_value)
        if match:
            starts.append(match.start())
    return min(starts) if starts else 0


def looks_like_footnote_title(title: str) -> bool:
    return bool(FOOTNOTE_TITLE_RE.search(title))


def extract_sections_from_act_text(text_value: str) -> list[dict[str, str]]:
    start = act_body_start(text_value)
    found: dict[str, tuple[str, str, int]] = {}
    for match in SECTION_HEADER_RE.finditer(text_value):
        if match.start() < start:
            continue
        number = match.group(1).strip()
        title = normalize_space(match.group(2))
        if looks_like_footnote_title(title):
            continue
        body = normalize_space(f"{match.group(2)} {match.group(3)}").replace("\x00", "")
        if len(body.split()) < 8:
            continue
        existing = found.get(number)
        if existing is None or len(body) > len(existing[1]):
            found[number] = (title, body, match.start())
    return [
        {"number": number, "title": title, "text": body}
        for number, (title, body, _) in sorted(found.items(), key=lambda item: item[1][2])
    ]


def extract_act_pdf(path: Path) -> tuple[str, int, int, float, list[dict[str, str]]]:
    raw_text, page_count = extract_text_pymupdf(path)
    clean_text = clean_ocr_text(raw_text).replace("\x00", "")
    word_count = len(clean_text.split())
    quality = estimate_text_quality(clean_text, page_count)
    sections = extract_sections_from_act_text(clean_text)
    return clean_text, page_count, word_count, quality, sections


def ensure_india_code_source(
    conn: Any,
    *,
    source_code: str,
    source_name: str,
    base_url: str = DEFAULT_COLLECTION_URL,
) -> int:
    row = conn.execute(
        sql_text(
            """
            INSERT INTO data_sources
            (source_code, source_name, source_type, base_url, jurisdiction, is_official,
             notes)
            VALUES (:source_code, :source_name, 'STATUTE', :base_url, 'INDIA', true,
                    'Official India Code Central Acts corpus imported from local downloaded PDFs.')
            ON CONFLICT (source_code) DO UPDATE SET
              source_name = EXCLUDED.source_name,
              source_type = EXCLUDED.source_type,
              base_url = EXCLUDED.base_url,
              jurisdiction = EXCLUDED.jurisdiction,
              is_official = EXCLUDED.is_official,
              notes = EXCLUDED.notes
            RETURNING id
            """
        ),
        {"source_code": source_code, "source_name": source_name, "base_url": base_url},
    ).scalar()
    return int(row)


def upsert_source_document(
    conn: Any,
    candidate: CentralActCandidate,
    *,
    source_id: int,
    content_hash: str,
    parse_status: str,
    error_msg: str | None = None,
) -> int:
    path = candidate.path.resolve()
    row = conn.execute(
        sql_text(
            """
            INSERT INTO source_documents
            (source_id, source_url, canonical_url, document_type, local_path, content_hash,
             mime_type, byte_size, http_status, fetched_at, parse_status, error_msg)
            VALUES (:source_id, :source_url, :canonical_url, 'ACT_PDF', :local_path,
                    :content_hash, 'application/pdf', :byte_size, 200, :fetched_at,
                    :parse_status, :error_msg)
            ON CONFLICT (source_url, content_hash) DO UPDATE SET
              source_id = EXCLUDED.source_id,
              canonical_url = EXCLUDED.canonical_url,
              document_type = EXCLUDED.document_type,
              local_path = EXCLUDED.local_path,
              byte_size = EXCLUDED.byte_size,
              fetched_at = EXCLUDED.fetched_at,
              parse_status = EXCLUDED.parse_status,
              error_msg = EXCLUDED.error_msg
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "source_url": candidate.pdf_url,
            "canonical_url": candidate.item_url or candidate.pdf_url,
            "local_path": str(path),
            "content_hash": content_hash,
            "byte_size": candidate.byte_size or path.stat().st_size,
            "fetched_at": candidate.downloaded_at,
            "parse_status": parse_status,
            "error_msg": error_msg,
        },
    ).scalar()
    return int(row)


def upsert_statute(
    conn: Any,
    candidate: CentralActCandidate,
    *,
    source_id: int,
    content_hash: str,
) -> int:
    india_code_id = f"123456789/{candidate.handle}" if candidate.handle else None
    existing = conn.execute(
        sql_text(
            """
            SELECT id
            FROM statutes
            WHERE (:india_code_id IS NOT NULL AND india_code_id = :india_code_id)
               OR (lower(act_name) = lower(:act_name)
                   AND year IS NOT DISTINCT FROM :year
                   AND jurisdiction = 'CENTRAL')
            ORDER BY id
            LIMIT 1
            """
        ),
        {
            "india_code_id": india_code_id,
            "act_name": candidate.title,
            "year": candidate.act_year,
        },
    ).scalar()
    if existing is not None:
        conn.execute(
            sql_text(
                """
                UPDATE statutes
                SET act_name = :act_name,
                    short_title = :short_title,
                    year = :year,
                    jurisdiction = 'CENTRAL',
                    source_id = :source_id,
                    source_url = :source_url,
                    india_code_id = :india_code_id,
                    is_in_force = true,
                    content_hash = :content_hash,
                    last_fetched = NOW(),
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": existing,
                "act_name": candidate.title,
                "short_title": candidate.title,
                "year": candidate.act_year,
                "source_id": source_id,
                "source_url": candidate.item_url or candidate.pdf_url,
                "india_code_id": india_code_id,
                "content_hash": content_hash,
            },
        )
        return int(existing)

    row = conn.execute(
        sql_text(
            """
            INSERT INTO statutes
            (act_name, short_title, year, jurisdiction, source_id, source_url,
             india_code_id, is_in_force, content_hash, last_fetched)
            VALUES (:act_name, :short_title, :year, 'CENTRAL', :source_id, :source_url,
                    :india_code_id, true, :content_hash, NOW())
            RETURNING id
            """
        ),
        {
            "act_name": candidate.title,
            "short_title": candidate.title,
            "year": candidate.act_year,
            "source_id": source_id,
            "source_url": candidate.item_url or candidate.pdf_url,
            "india_code_id": india_code_id,
            "content_hash": content_hash,
        },
    ).scalar()
    return int(row)


def replace_sections(
    conn: Any,
    *,
    statute_id: int,
    source_document_id: int,
    source_url: str,
    sections: list[dict[str, str]],
) -> int:
    conn.execute(
        sql_text(
            """
            DELETE FROM embeddings
            WHERE source_type = 'SECTION'
              AND source_id IN (SELECT id FROM sections WHERE statute_id = :statute_id)
            """
        ),
        {"statute_id": statute_id},
    )
    conn.execute(sql_text("DELETE FROM sections WHERE statute_id = :statute_id"), {"statute_id": statute_id})
    for section in sections:
        conn.execute(
            sql_text(
                """
                INSERT INTO sections
                (statute_id, section_number, section_title, section_text, is_current,
                 source_document_id, content_hash)
                VALUES (:statute_id, :section_number, :section_title, :section_text, true,
                        :source_document_id, :content_hash)
                """
            ),
            {
                "statute_id": statute_id,
                "section_number": section["number"],
                "section_title": section["title"],
                "section_text": section["text"],
                "source_document_id": source_document_id,
                "source_url": source_url,
                "content_hash": sha256_text(section["text"]),
            },
        )
    return len(sections)


def import_central_acts(
    folder: str | Path,
    *,
    database_url: str | None = None,
    source_code: str = DEFAULT_SOURCE_CODE,
    source_name: str = DEFAULT_SOURCE_NAME,
    manifest_name: str = "manifest.csv",
    dry_run: bool = False,
    limit: int | None = None,
    min_words: int = 80,
) -> CentralActsImportSummary:
    candidates, skipped, scanned = read_manifest_candidates(folder, manifest_name=manifest_name)
    if limit is not None:
        candidates = candidates[: max(limit, 0)]
    summary = CentralActsImportSummary(
        database_available=True,
        scanned_rows=scanned,
        eligible_files=len(candidates),
        skipped=skipped,
        dry_run=dry_run,
        source_code=source_code,
    )
    if dry_run:
        summary.imported_source_documents = len(candidates)
        summary.imported_statutes = len(candidates)
        return summary

    try:
        engine = make_pg_engine(database_url)
        with engine.begin() as conn:
            source_id = ensure_india_code_source(
                conn,
                source_code=source_code,
                source_name=source_name,
            )
        for candidate in candidates:
            try:
                content_hash = candidate.content_hash or sha256_file(candidate.path)
                clean_text, _page_count, word_count, _quality, sections = extract_act_pdf(candidate.path)
                summary.extracted_words += word_count
                if word_count < min_words:
                    with engine.begin() as conn:
                        source_document_id = upsert_source_document(
                            conn,
                            candidate,
                            source_id=source_id,
                            content_hash=content_hash,
                            parse_status="FAILED",
                            error_msg=f"Only {word_count} extracted words.",
                        )
                    summary.failed.append(
                        {
                            "path": str(candidate.path),
                            "reason": f"too little extracted text ({word_count} words)",
                            "source_document_id": str(source_document_id),
                        }
                    )
                    continue
                if not sections:
                    with engine.begin() as conn:
                        source_document_id = upsert_source_document(
                            conn,
                            candidate,
                            source_id=source_id,
                            content_hash=content_hash,
                            parse_status="FAILED",
                            error_msg="No sections extracted from PDF text.",
                        )
                    summary.failed.append(
                        {
                            "path": str(candidate.path),
                            "reason": "no sections extracted",
                            "source_document_id": str(source_document_id),
                        }
                    )
                    continue
                with engine.begin() as conn:
                    source_document_id = upsert_source_document(
                        conn,
                        candidate,
                        source_id=source_id,
                        content_hash=content_hash,
                        parse_status="PARSED",
                    )
                    statute_id = upsert_statute(
                        conn,
                        candidate,
                        source_id=source_id,
                        content_hash=content_hash,
                    )
                    section_count = replace_sections(
                        conn,
                        statute_id=statute_id,
                        source_document_id=source_document_id,
                        source_url=candidate.pdf_url,
                        sections=sections,
                    )
                summary.imported_source_documents += 1
                summary.imported_statutes += 1
                summary.imported_sections += section_count
            except Exception as exc:
                summary.failed.append({"path": str(candidate.path), "reason": str(exc)})
    except Exception as exc:
        summary.database_available = False
        summary.error = str(exc)
    return summary
