from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from legal_db.config import settings
from legal_db.pdf.ocr import clean_ocr_text, estimate_text_quality, extract_text_pymupdf


SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm", ".txt"}
PERSONAL_SKIP_PATTERNS = (
    "cover letter",
    "cover_letter",
    "resume",
    "curriculum vitae",
    ".vcf",
)
CHAPTER_RE = re.compile(
    r"(?im)^\s*chapter\s+([0-9IVXLC]+|[A-Z])(?:\s*[:.\-]\s+|\s{2,})(.{0,140})$"
)


@dataclass(frozen=True)
class LocalDocumentCandidate:
    path: Path
    title: str
    material_type: str
    document_type: str
    subject_tags: list[str]
    source_url: str | None
    canonical_url: str | None
    mime_type: str


@dataclass
class LocalLibrarySummary:
    database_available: bool
    scanned_files: int = 0
    eligible_files: int = 0
    imported_books: int = 0
    imported_chapters: int = 0
    imported_chunks: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    dry_run: bool = False
    source_code: str = "LOCAL_LIBRARY"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "scanned_files": self.scanned_files,
            "eligible_files": self.eligible_files,
            "imported_books": self.imported_books,
            "imported_chapters": self.imported_chapters,
            "imported_chunks": self.imported_chunks,
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_title(path: Path) -> str:
    stem = unquote(path.stem)
    stem = re.sub(r"\[[0-9]+\]", "", stem)
    stem = re.sub(r"[_%]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip(" -_")
    return stem or path.name


def load_document_manifest(manifest_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if manifest_path is None:
        return {}
    path = Path(manifest_path)
    if path.is_dir():
        path = path / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    documents = data.get("documents", []) if isinstance(data, dict) else []
    manifest: dict[str, dict[str, Any]] = {}
    for entry in documents:
        if not isinstance(entry, dict):
            continue
        filename = entry.get("filename") or entry.get("path")
        if filename:
            manifest[Path(str(filename)).name] = entry
    return manifest


def should_skip_path(path: Path, *, include_personal: bool = False) -> str | None:
    if not path.is_file():
        return "not a file"
    name = path.name.lower()
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return f"unsupported extension {path.suffix or '(none)'}"
    if not include_personal and any(pattern in name for pattern in PERSONAL_SKIP_PATTERNS):
        return "looks personal/non-legal; pass --include-personal to force"
    return None


def infer_material_type(title: str) -> str:
    lowered = title.lower()
    if any(term in lowered for term in ["commission", "report", "committee", "nanavati", "justice"]):
        return "REPORT"
    if "manual" in lowered:
        return "MANUAL"
    if any(term in lowered for term in ["guideline", "guide", "policy", "action plan"]):
        return "GUIDE"
    if any(term in lowered for term in ["sanhita", "adhiniyam", "act", "code"]):
        return "OTHER"
    return "OTHER"


def document_type_for_material(material_type: str) -> str:
    if material_type == "REPORT":
        return "REPORT_PDF"
    if material_type in {"GUIDE", "MANUAL"}:
        return "MANUAL_PDF"
    if material_type == "TEXTBOOK":
        return "TEXTBOOK_PDF"
    return "BOOK_PDF"


def document_type_for_path(path: Path, material_type: str) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "HTML_PAGE"
    if suffix == ".txt":
        return "OTHER"
    return document_type_for_material(material_type)


def mime_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".html", ".htm"}:
        return "text/html"
    if suffix == ".txt":
        return "text/plain"
    return "application/octet-stream"


def infer_subject_tags(title: str) -> list[str]:
    lowered = title.lower()
    tags: set[str] = {"LOCAL_LIBRARY"}
    if any(term in lowered for term in ["sanhita", "adhiniyam", "bns", "bnss", "bsa"]):
        tags.add("CRIMINAL_LAW")
    if any(term in lowered for term in ["bns", "nyaya sanhita"]):
        tags.add("BNS")
    if "new criminal law" in lowered or "sankalan" in lowered:
        tags.add("NEW_CRIMINAL_LAWS")
    if any(term in lowered for term in ["police", "jail", "prison", "ips", "capf"]):
        tags.add("POLICING")
    if any(term in lowered for term in ["disaster", "fire", "emergency"]):
        tags.add("PUBLIC_SAFETY")
    if any(term in lowered for term in ["sc-st", "communal", "harmony", "minority"]):
        tags.add("SOCIAL_JUSTICE")
    if any(term in lowered for term in ["commission", "committee", "nanavati", "justice"]):
        tags.add("REPORT")
    return sorted(tags)


def discover_local_documents(
    folder: str | Path,
    *,
    include_personal: bool = False,
    manifest_path: str | Path | None = None,
) -> tuple[list[LocalDocumentCandidate], list[dict[str, str]], int]:
    root = Path(folder)
    manifest = load_document_manifest(manifest_path)
    candidates: list[LocalDocumentCandidate] = []
    skipped: list[dict[str, str]] = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        reason = should_skip_path(path, include_personal=include_personal)
        if reason:
            skipped.append({"path": str(path), "reason": reason})
            continue
        entry = manifest.get(path.name, {})
        title = str(entry.get("title") or normalize_title(path))
        material_type = str(entry.get("material_type") or infer_material_type(title))
        document_type = str(entry.get("document_type") or document_type_for_path(path, material_type))
        subject_tags = set(infer_subject_tags(title))
        manifest_tags = entry.get("subject_tags") or entry.get("tags") or []
        if isinstance(manifest_tags, list):
            subject_tags.update(str(tag) for tag in manifest_tags)
        if "OFFICIAL_PUBLIC" in subject_tags:
            subject_tags.discard("LOCAL_LIBRARY")
        candidates.append(
            LocalDocumentCandidate(
                path=path,
                title=title,
                material_type=material_type,
                document_type=document_type,
                subject_tags=sorted(subject_tags),
                source_url=entry.get("url") or entry.get("source_url"),
                canonical_url=entry.get("canonical_url") or entry.get("url") or entry.get("source_url"),
                mime_type=str(entry.get("content_type") or mime_type_for_path(path)).split(";")[0],
            )
        )
    return candidates, skipped, scanned


def chunk_words(text_value: str, chunk_size: int = 750, overlap: int = 100) -> list[str]:
    words = text_value.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if len(chunk.split()) >= 30:
            chunks.append(chunk)
    return chunks


def split_chapters(clean_text: str) -> list[dict[str, Any]]:
    matches = list(CHAPTER_RE.finditer(clean_text))
    if not matches:
        return [
            {
                "chapter_number": "FULL",
                "chapter_title": "Full document",
                "start_char": 0,
                "end_char": len(clean_text),
                "chapter_text": clean_text,
            }
        ]
    chapters: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(clean_text)
        chapter_text = clean_text[start:end].strip()
        if len(chapter_text.split()) < 50:
            continue
        chapters.append(
            {
                "chapter_number": match.group(1).strip(),
                "chapter_title": re.sub(r"\s+", " ", match.group(2)).strip()
                or f"Chapter {match.group(1)}",
                "start_char": start,
                "end_char": end,
                "chapter_text": chapter_text,
            }
        )
    return chapters or [
        {
            "chapter_number": "FULL",
            "chapter_title": "Full document",
            "start_char": 0,
            "end_char": len(clean_text),
            "chapter_text": clean_text,
        }
    ]


def extract_local_pdf_text(path: Path) -> tuple[str, str, int, int, float]:
    raw_text, page_count = extract_text_pymupdf(path)
    raw_text = raw_text.replace("\x00", "")
    clean_text = clean_ocr_text(raw_text).replace("\x00", "")
    word_count = len(clean_text.split())
    quality = estimate_text_quality(clean_text, page_count)
    return raw_text, clean_text, page_count, word_count, quality


def extract_html_text(path: Path) -> tuple[str, str, int, int, float]:
    from bs4 import BeautifulSoup

    raw_text = path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
    soup = BeautifulSoup(raw_text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text_value = soup.get_text("\n")
    clean_text = clean_ocr_text(text_value).replace("\x00", "")
    word_count = len(clean_text.split())
    quality = estimate_text_quality(clean_text, 1)
    return raw_text, clean_text, 1, word_count, quality


def extract_plain_text(path: Path) -> tuple[str, str, int, int, float]:
    raw_text = path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
    clean_text = clean_ocr_text(raw_text).replace("\x00", "")
    word_count = len(clean_text.split())
    quality = estimate_text_quality(clean_text, 1)
    return raw_text, clean_text, 1, word_count, quality


def extract_local_document_text(path: Path) -> tuple[str, str, int, int, float]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_local_pdf_text(path)
    if suffix in {".html", ".htm"}:
        return extract_html_text(path)
    if suffix == ".txt":
        return extract_plain_text(path)
    raise ValueError(f"Unsupported extension {path.suffix or '(none)'}")


def ensure_source(
    conn: Any,
    *,
    source_code: str,
    source_name: str,
    folder: Path,
    is_official: bool = False,
    notes: str | None = None,
) -> int:
    row = conn.execute(
        sql_text(
            """
            INSERT INTO data_sources
            (source_code, source_name, source_type, base_url, jurisdiction, is_official, notes)
            VALUES (:source_code, :source_name, 'REFERENCE', :base_url, 'INDIA', :is_official,
                    :notes)
            ON CONFLICT (source_code) DO UPDATE SET
              source_name = EXCLUDED.source_name,
              base_url = EXCLUDED.base_url,
              is_official = EXCLUDED.is_official,
              notes = EXCLUDED.notes
            RETURNING id
            """
        ),
        {
            "source_code": source_code,
            "source_name": source_name,
            "base_url": folder.resolve().as_uri(),
            "is_official": is_official,
            "notes": notes
            or "Local user-provided library. Do not redistribute raw files from repository.",
        },
    ).scalar()
    return int(row)


def upsert_source_document(
    conn: Any,
    candidate: LocalDocumentCandidate,
    *,
    source_id: int,
    content_hash: str,
    parse_status: str,
    error_msg: str | None = None,
) -> int:
    path = candidate.path.resolve()
    source_url = candidate.source_url or path.as_uri()
    canonical_url = candidate.canonical_url or source_url
    row = conn.execute(
        sql_text(
            """
            INSERT INTO source_documents
            (source_id, source_url, canonical_url, document_type, local_path, content_hash,
             mime_type, byte_size, http_status, fetched_at, parse_status, error_msg)
            VALUES (:source_id, :source_url, :canonical_url, :document_type, :local_path,
                    :content_hash, :mime_type, :byte_size, 200, NOW(), :parse_status,
                    :error_msg)
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
            "source_url": source_url,
            "canonical_url": canonical_url,
            "document_type": candidate.document_type,
            "local_path": str(path),
            "content_hash": content_hash,
            "mime_type": candidate.mime_type,
            "byte_size": path.stat().st_size,
            "parse_status": parse_status,
            "error_msg": error_msg,
        },
    ).scalar()
    return int(row)


def upsert_book(
    conn: Any,
    candidate: LocalDocumentCandidate,
    *,
    source_code: str,
    source_document_id: int,
    content_hash: str,
    rights_note: str,
) -> int:
    source_url = candidate.source_url or candidate.path.resolve().as_uri()
    row = conn.execute(
        sql_text(
            """
            INSERT INTO legal_books
            (title, material_type, source_code, jurisdiction, subject_tags, source_url,
             source_document_id, content_hash, rights_note)
            VALUES (:title, :material_type, :source_code, 'INDIA', :subject_tags,
                    :source_url, :source_document_id, :content_hash, :rights_note)
            ON CONFLICT (title, source_url) DO UPDATE SET
              material_type = EXCLUDED.material_type,
              source_code = EXCLUDED.source_code,
              subject_tags = EXCLUDED.subject_tags,
              source_document_id = EXCLUDED.source_document_id,
              content_hash = EXCLUDED.content_hash,
              rights_note = EXCLUDED.rights_note
            RETURNING id
            """
        ),
        {
            "title": candidate.title,
            "material_type": candidate.material_type,
            "source_code": source_code,
            "subject_tags": candidate.subject_tags,
            "source_url": source_url,
            "source_document_id": source_document_id,
            "content_hash": content_hash,
            "rights_note": rights_note,
        },
    ).scalar()
    return int(row)


def replace_book_content(conn: Any, *, book_id: int, chapters: list[dict[str, Any]]) -> tuple[int, int]:
    conn.execute(
        sql_text(
            """
            DELETE FROM embeddings
            WHERE source_type = 'BOOK_CHUNK'
              AND source_id IN (SELECT id FROM book_chunks WHERE book_id = :book_id)
            """
        ),
        {"book_id": book_id},
    )
    conn.execute(sql_text("DELETE FROM book_chunks WHERE book_id = :book_id"), {"book_id": book_id})
    conn.execute(sql_text("DELETE FROM book_chapters WHERE book_id = :book_id"), {"book_id": book_id})

    chapter_count = 0
    chunk_count = 0
    for chapter in chapters:
        chapter_text = str(chapter["chapter_text"])
        chapter_id = conn.execute(
            sql_text(
                """
                INSERT INTO book_chapters
                (book_id, chapter_number, chapter_title, start_char, end_char,
                 chapter_text, content_hash)
                VALUES (:book_id, :chapter_number, :chapter_title, :start_char,
                        :end_char, :chapter_text, :content_hash)
                RETURNING id
                """
            ),
            {
                "book_id": book_id,
                "chapter_number": chapter["chapter_number"],
                "chapter_title": chapter["chapter_title"],
                "start_char": chapter["start_char"],
                "end_char": chapter["end_char"],
                "chapter_text": chapter_text,
                "content_hash": sha256_text(chapter_text),
            },
        ).scalar()
        chapter_count += 1
        for index, chunk in enumerate(chunk_words(chapter_text)):
            conn.execute(
                sql_text(
                    """
                    INSERT INTO book_chunks
                    (book_id, chapter_id, chunk_index, chunk_text, word_count, content_hash)
                    VALUES (:book_id, :chapter_id, :chunk_index, :chunk_text,
                            :word_count, :content_hash)
                    """
                ),
                {
                    "book_id": book_id,
                    "chapter_id": int(chapter_id),
                    "chunk_index": index,
                    "chunk_text": chunk,
                    "word_count": len(chunk.split()),
                    "content_hash": sha256_text(chunk),
                },
            )
            chunk_count += 1
    return chapter_count, chunk_count


def ingest_local_library(
    folder: str | Path,
    *,
    database_url: str | None = None,
    source_code: str = "LOCAL_LIBRARY",
    source_name: str = "Local User Document Library",
    include_personal: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
    min_words: int = 80,
    manifest_path: str | Path | None = None,
    source_official: bool = False,
    source_notes: str | None = None,
    rights_note: str | None = None,
) -> LocalLibrarySummary:
    root = Path(folder)
    candidates, skipped, scanned = discover_local_documents(
        root,
        include_personal=include_personal,
        manifest_path=manifest_path,
    )
    if limit is not None:
        candidates = candidates[: max(limit, 0)]
    summary = LocalLibrarySummary(
        database_available=True,
        scanned_files=scanned,
        eligible_files=len(candidates),
        skipped=skipped,
        dry_run=dry_run,
        source_code=source_code,
    )
    if dry_run:
        summary.imported_books = len(candidates)
        return summary

    try:
        engine = make_pg_engine(database_url)
        with engine.begin() as conn:
            source_id = ensure_source(
                conn,
                source_code=source_code,
                source_name=source_name,
                folder=root,
                is_official=source_official,
                notes=source_notes,
            )
        for candidate in candidates:
            try:
                content_hash = sha256_file(candidate.path)
                raw_text, clean_text, page_count, word_count, quality = extract_local_document_text(
                    candidate.path
                )
                with engine.begin() as conn:
                    if word_count < min_words:
                        source_document_id = upsert_source_document(
                            conn,
                            candidate,
                            source_id=source_id,
                            content_hash=content_hash,
                            parse_status="FAILED",
                            error_msg=(
                                f"Only {word_count} extracted words; likely scanned or non-text document."
                            ),
                        )
                        summary.failed.append(
                            {
                                "path": str(candidate.path),
                                "reason": f"too little extracted text ({word_count} words)",
                                "source_document_id": str(source_document_id),
                            }
                        )
                        continue
                    source_document_id = upsert_source_document(
                        conn,
                        candidate,
                        source_id=source_id,
                        content_hash=content_hash,
                        parse_status="PARSED",
                    )
                    book_id = upsert_book(
                        conn,
                        candidate,
                        source_code=source_code,
                        source_document_id=source_document_id,
                        content_hash=content_hash,
                        rights_note=rights_note
                        or (
                            "Local user-provided document. Indexed for private/local research only; "
                            "do not commit, redistribute, or expose raw file contents publicly."
                        ),
                    )
                    chapters = split_chapters(clean_text)
                    chapter_count, chunk_count = replace_book_content(
                        conn,
                        book_id=book_id,
                        chapters=chapters,
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
                    conn.execute(
                        sql_text(
                            """
                            INSERT INTO quality_metrics
                            (metric_name, metric_scope, numerator, denominator, score, notes)
                            VALUES ('local_document_text_quality', :scope, :word_count,
                                    :page_count, :quality, :notes)
                            """
                        ),
                        {
                            "scope": str(candidate.path),
                            "word_count": word_count,
                            "page_count": page_count,
                            "quality": quality,
                            "notes": f"source_document_id={source_document_id}",
                        },
                    )
                summary.imported_books += 1
                summary.imported_chapters += chapter_count
                summary.imported_chunks += chunk_count
            except Exception as exc:
                summary.failed.append({"path": str(candidate.path), "reason": str(exc)})
    except Exception as exc:
        summary.database_available = False
        summary.error = str(exc)
    return summary
