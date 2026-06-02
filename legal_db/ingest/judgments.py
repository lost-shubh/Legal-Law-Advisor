from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from legal_db.ingest.base import PoliteFetcher
from legal_db.ingest.jobs import DEFAULT_DB_PATH, IngestionJobTracker
from legal_db.pdf.ocr import extract_pdf_text


ROOT = Path(__file__).resolve().parents[2]
RAW_JUDGMENT_DIR = ROOT / "data" / "raw" / "judgments"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_space(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip() or None


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("judgments"), list):
        return data["judgments"]
    raise ValueError("Judgment manifest must be a list or an object with a 'judgments' list.")


def ensure_staging_judgment_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_code TEXT NOT NULL,
          source_url TEXT NOT NULL,
          final_url TEXT,
          document_type TEXT NOT NULL,
          local_path TEXT,
          content_hash TEXT,
          mime_type TEXT,
          byte_size INTEGER,
          http_status INTEGER,
          fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
          title TEXT,
          parse_status TEXT DEFAULT 'PENDING',
          error_msg TEXT,
          UNIQUE(source_url, content_hash)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS document_texts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_document_id INTEGER NOT NULL,
          extraction_method TEXT NOT NULL,
          page_count INTEGER,
          word_count INTEGER,
          raw_text TEXT,
          clean_text TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(source_document_id, extraction_method)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_code TEXT NOT NULL,
          court_code TEXT NOT NULL,
          diary_no TEXT,
          case_number TEXT,
          title TEXT,
          decision_date TEXT,
          source_url TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(court_code, diary_no, decision_date, source_url)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS judgments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          case_id INTEGER NOT NULL,
          source_document_id INTEGER NOT NULL,
          judgment_type TEXT,
          judgment_date TEXT,
          pdf_url TEXT,
          page_count INTEGER,
          word_count INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(case_id, source_document_id)
        )
        """
    )
    conn.commit()


@dataclass(frozen=True)
class JudgmentManifestItem:
    title: str
    court_code: str
    source_code: str
    pdf_url: str | None = None
    local_pdf_path: str | None = None
    judgment_date: str | None = None
    case_number: str | None = None
    neutral_citation: str | None = None
    judgment_type: str = "FINAL"
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgmentManifestItem":
        title = normalize_space(data.get("title"))
        court_code = normalize_space(data.get("court_code"))
        source_code = normalize_space(data.get("source_code")) or "UNKNOWN"
        if not title:
            raise ValueError("Manifest item is missing title.")
        if not court_code:
            raise ValueError(f"Manifest item '{title}' is missing court_code.")
        pdf_url = normalize_space(data.get("pdf_url"))
        local_pdf_path = normalize_space(data.get("local_pdf_path"))
        if not pdf_url and not local_pdf_path:
            raise ValueError(f"Manifest item '{title}' needs pdf_url or local_pdf_path.")
        return cls(
            title=title,
            court_code=court_code,
            source_code=source_code,
            pdf_url=pdf_url,
            local_pdf_path=local_pdf_path,
            judgment_date=normalize_space(data.get("judgment_date")),
            case_number=normalize_space(data.get("case_number")),
            neutral_citation=normalize_space(data.get("neutral_citation")),
            judgment_type=normalize_space(data.get("judgment_type")) or "FINAL",
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )

    @property
    def source_url(self) -> str:
        return self.pdf_url or f"file://{Path(self.local_pdf_path or '').as_posix()}"

    @property
    def item_key(self) -> str:
        return self.neutral_citation or self.case_number or self.source_url

    @property
    def year_bucket(self) -> str:
        if self.judgment_date and len(self.judgment_date) >= 4:
            return self.judgment_date[:4]
        return "unknown-year"


@dataclass(frozen=True)
class JudgmentIngestionSummary:
    job_id: int
    target_count: int
    processed_count: int
    success_count: int
    failed_count: int
    skipped_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "job_id": self.job_id,
            "target_count": self.target_count,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
        }


class JudgmentManifestIngestionPipeline:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        raw_dir: str | Path = RAW_JUDGMENT_DIR,
        fetcher: PoliteFetcher | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.raw_dir = Path(raw_dir)
        self.fetcher = fetcher or PoliteFetcher()
        self.tracker = IngestionJobTracker(self.db_path)

    def ingest_manifest(
        self,
        manifest_path: str | Path,
        *,
        limit: int | None = None,
        download: bool = True,
        extract_text: bool = True,
    ) -> JudgmentIngestionSummary:
        raw_items = load_manifest(manifest_path)
        items = [JudgmentManifestItem.from_dict(item) for item in raw_items]
        if limit is not None:
            items = items[: max(limit, 0)]

        job = self.tracker.create_job(
            "JUDGMENT_MANIFEST",
            source_code="MIXED",
            target_count=len(items),
            metadata={"manifest_path": str(manifest_path), "extract_text": extract_text},
        )

        success = failed = skipped = 0
        for item in items:
            try:
                result_status = self._ingest_one(
                    job.id,
                    item,
                    download=download,
                    extract_text=extract_text,
                )
                if result_status in {"DONE", "DUPLICATE"}:
                    success += 1
                elif result_status == "SKIPPED":
                    skipped += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                self.tracker.record_item(
                    job.id,
                    item_key=item.item_key,
                    item_type="JUDGMENT_PDF",
                    source_url=item.source_url,
                    status="FAILED",
                    metadata=item.metadata,
                    error_msg=str(exc),
                )

        self.tracker.finish_job(job.id, status="DONE")
        return JudgmentIngestionSummary(
            job_id=job.id,
            target_count=len(items),
            processed_count=len(items),
            success_count=success,
            failed_count=failed,
            skipped_count=skipped,
        )

    def _ingest_one(
        self,
        job_id: int,
        item: JudgmentManifestItem,
        *,
        download: bool,
        extract_text: bool,
    ) -> str:
        self.tracker.record_item(
            job_id,
            item_key=item.item_key,
            item_type="JUDGMENT_PDF",
            source_url=item.source_url,
            status="RUNNING",
            metadata=item.metadata,
        )
        pdf_bytes, http_status = self._read_pdf_bytes(item, download=download)
        if pdf_bytes is None:
            self.tracker.record_item(
                job_id,
                item_key=item.item_key,
                item_type="JUDGMENT_PDF",
                source_url=item.source_url,
                status="SKIPPED",
                metadata=item.metadata,
                error_msg="Download disabled and no readable local_pdf_path was provided.",
            )
            return "SKIPPED"

        pdf_hash = sha256_bytes(pdf_bytes)
        local_path = self._store_pdf(item, pdf_hash, pdf_bytes)
        conn = self._connect()
        try:
            source_document_id = self._upsert_source_document(
                conn,
                item,
                local_path=local_path,
                pdf_hash=pdf_hash,
                byte_size=len(pdf_bytes),
                http_status=http_status,
            )
            case_id = self._upsert_case(conn, item, source_document_id)
            judgment_id = self._upsert_judgment(conn, item, case_id, source_document_id)
            if extract_text:
                self._extract_and_store_text(conn, source_document_id, judgment_id, local_path)
            conn.commit()
        finally:
            conn.close()

        self.tracker.record_item(
            job_id,
            item_key=item.item_key,
            item_type="JUDGMENT_PDF",
            source_url=item.source_url,
            status="DONE",
            local_path=str(local_path),
            content_hash=pdf_hash,
            metadata=item.metadata,
        )
        return "DONE"

    def _read_pdf_bytes(
        self,
        item: JudgmentManifestItem,
        *,
        download: bool,
    ) -> tuple[bytes | None, int | None]:
        if item.local_pdf_path:
            path = Path(item.local_pdf_path)
            if path.exists():
                return path.read_bytes(), None
        if not download or not item.pdf_url:
            return None, None
        result = self.fetcher.get(item.pdf_url)
        if result.status_code >= 400:
            raise RuntimeError(f"PDF fetch failed with HTTP {result.status_code}: {item.pdf_url}")
        return result.content, result.status_code

    def _store_pdf(self, item: JudgmentManifestItem, pdf_hash: str, pdf_bytes: bytes) -> Path:
        target_dir = self.raw_dir / item.court_code.lower() / item.year_bucket
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{pdf_hash}.pdf"
        if not target_path.exists():
            target_path.write_bytes(pdf_bytes)
        return target_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        ensure_staging_judgment_tables(conn)
        return conn

    def _upsert_source_document(
        self,
        conn: sqlite3.Connection,
        item: JudgmentManifestItem,
        *,
        local_path: Path,
        pdf_hash: str,
        byte_size: int,
        http_status: int | None,
    ) -> int:
        conn.execute(
            """
            INSERT OR IGNORE INTO source_documents
            (source_code, source_url, final_url, document_type, local_path,
             content_hash, mime_type, byte_size, http_status, title, parse_status)
            VALUES (?, ?, ?, 'JUDGMENT_PDF', ?, ?, 'application/pdf', ?, ?, ?, 'PENDING')
            """,
            (
                item.source_code,
                item.source_url,
                item.pdf_url,
                str(local_path),
                pdf_hash,
                byte_size,
                http_status,
                item.title,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM source_documents
            WHERE source_url = ? AND content_hash = ?
            ORDER BY id DESC LIMIT 1
            """,
            (item.source_url, pdf_hash),
        ).fetchone()
        if row is None:
            raise RuntimeError("Unable to resolve source_document_id after insert.")
        return int(row["id"])

    def _upsert_case(
        self,
        conn: sqlite3.Connection,
        item: JudgmentManifestItem,
        source_document_id: int,
    ) -> int:
        del source_document_id
        diary_no = item.neutral_citation or item.case_number or item.item_key
        conn.execute(
            """
            INSERT OR IGNORE INTO cases
            (source_code, court_code, diary_no, case_number, title, decision_date, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.source_code,
                item.court_code,
                diary_no,
                item.case_number,
                item.title,
                item.judgment_date,
                item.source_url,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM cases
            WHERE court_code = ? AND diary_no = ? AND source_url = ?
            ORDER BY id DESC LIMIT 1
            """,
            (item.court_code, diary_no, item.source_url),
        ).fetchone()
        if row is None:
            raise RuntimeError("Unable to resolve case_id after insert.")
        return int(row["id"])

    def _upsert_judgment(
        self,
        conn: sqlite3.Connection,
        item: JudgmentManifestItem,
        case_id: int,
        source_document_id: int,
    ) -> int:
        conn.execute(
            """
            INSERT OR IGNORE INTO judgments
            (case_id, source_document_id, judgment_type, judgment_date, pdf_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                case_id,
                source_document_id,
                item.judgment_type,
                item.judgment_date,
                item.pdf_url,
            ),
        )
        row = conn.execute(
            """
            SELECT id FROM judgments
            WHERE case_id = ? AND source_document_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (case_id, source_document_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("Unable to resolve judgment_id after insert.")
        return int(row["id"])

    def _extract_and_store_text(
        self,
        conn: sqlite3.Connection,
        source_document_id: int,
        judgment_id: int,
        local_path: Path,
    ) -> None:
        try:
            result = extract_pdf_text(local_path)
        except Exception as exc:
            conn.execute(
                """
                UPDATE source_documents
                SET parse_status = 'FAILED', error_msg = ?
                WHERE id = ?
                """,
                (str(exc), source_document_id),
            )
            return
        conn.execute(
            """
            INSERT INTO document_texts
            (source_document_id, extraction_method, page_count, word_count, raw_text, clean_text)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_document_id, extraction_method) DO UPDATE SET
              page_count = excluded.page_count,
              word_count = excluded.word_count,
              raw_text = excluded.raw_text,
              clean_text = excluded.clean_text
            """,
            (
                source_document_id,
                result.extraction_method,
                result.page_count,
                result.word_count,
                result.raw_text,
                result.clean_text,
            ),
        )
        conn.execute(
            """
            UPDATE judgments
            SET page_count = ?, word_count = ?
            WHERE id = ?
            """,
            (result.page_count, result.word_count, judgment_id),
        )
        conn.execute(
            """
            UPDATE source_documents
            SET parse_status = 'PARSED', error_msg = NULL
            WHERE id = ?
            """,
            (source_document_id,),
        )


def copy_manifest_template(target_path: str | Path) -> Path:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(ROOT / "config" / "judgment_manifest.example.json", target)
    return target
