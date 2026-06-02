from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"

JOB_STATUSES = {"PENDING", "RUNNING", "DONE", "FAILED", "PAUSED", "SKIPPED"}
ITEM_STATUSES = {"PENDING", "RUNNING", "DONE", "FAILED", "SKIPPED", "DUPLICATE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True)


def json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def ensure_ingestion_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_code TEXT UNIQUE NOT NULL,
          job_type TEXT NOT NULL,
          source_code TEXT,
          source_url TEXT,
          status TEXT NOT NULL,
          target_count INTEGER DEFAULT 0,
          processed_count INTEGER DEFAULT 0,
          success_count INTEGER DEFAULT 0,
          failed_count INTEGER DEFAULT 0,
          skipped_count INTEGER DEFAULT 0,
          metadata_json TEXT,
          error_msg TEXT,
          started_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          finished_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_items (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id INTEGER NOT NULL,
          item_key TEXT NOT NULL,
          item_type TEXT NOT NULL,
          source_url TEXT,
          status TEXT NOT NULL,
          local_path TEXT,
          content_hash TEXT,
          metadata_json TEXT,
          error_msg TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(job_id, item_key)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_type ON ingestion_jobs(job_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_items_job ON ingestion_items(job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_items_status ON ingestion_items(status)")
    conn.commit()


@dataclass(frozen=True)
class IngestionJob:
    id: int
    job_code: str
    job_type: str
    source_code: str | None
    status: str


class IngestionJobTracker:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        ensure_ingestion_tables(conn)
        return conn

    def create_job(
        self,
        job_type: str,
        *,
        source_code: str | None = None,
        source_url: str | None = None,
        target_count: int = 0,
        metadata: dict[str, Any] | None = None,
        status: str = "RUNNING",
    ) -> IngestionJob:
        if status not in JOB_STATUSES:
            raise ValueError(f"Unsupported job status: {status}")
        now = utc_now()
        job_code = f"{job_type.lower()}-{now.replace(':', '').replace('+', 'z')}"
        conn = self.connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO ingestion_jobs
                (job_code, job_type, source_code, source_url, status, target_count,
                 metadata_json, started_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_code,
                    job_type,
                    source_code,
                    source_url,
                    status,
                    target_count,
                    json_dumps(metadata),
                    now,
                    now,
                ),
            )
            job_id = int(cursor.lastrowid)
            conn.commit()
        finally:
            conn.close()
        return IngestionJob(job_id, job_code, job_type, source_code, status)

    def record_item(
        self,
        job_id: int,
        *,
        item_key: str,
        item_type: str,
        status: str,
        source_url: str | None = None,
        local_path: str | None = None,
        content_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
        error_msg: str | None = None,
    ) -> None:
        if status not in ITEM_STATUSES:
            raise ValueError(f"Unsupported item status: {status}")
        now = utc_now()
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO ingestion_items
                (job_id, item_key, item_type, source_url, status, local_path,
                 content_hash, metadata_json, error_msg, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, item_key) DO UPDATE SET
                  status = excluded.status,
                  local_path = excluded.local_path,
                  content_hash = excluded.content_hash,
                  metadata_json = excluded.metadata_json,
                  error_msg = excluded.error_msg,
                  updated_at = excluded.updated_at
                """,
                (
                    job_id,
                    item_key,
                    item_type,
                    source_url,
                    status,
                    local_path,
                    content_hash,
                    json_dumps(metadata),
                    error_msg,
                    now,
                    now,
                ),
            )
            self._refresh_job_counts(conn, job_id)
            conn.commit()
        finally:
            conn.close()

    def finish_job(self, job_id: int, *, status: str = "DONE", error_msg: str | None = None) -> None:
        if status not in JOB_STATUSES:
            raise ValueError(f"Unsupported job status: {status}")
        now = utc_now()
        conn = self.connect()
        try:
            self._refresh_job_counts(conn, job_id)
            conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = ?, error_msg = ?, finished_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, error_msg, now, now, job_id),
            )
            conn.commit()
        finally:
            conn.close()

    def status(self) -> dict[str, Any]:
        if not self.db_path.exists():
            return {
                "database_available": False,
                "jobs": {"total": 0, "by_status": {}},
                "items": {"total": 0, "by_status": {}},
                "recent_jobs": [],
            }
        conn = self.connect()
        try:
            job_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM ingestion_jobs GROUP BY status"
            ).fetchall()
            item_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM ingestion_items GROUP BY status"
            ).fetchall()
            recent_rows = conn.execute(
                """
                SELECT id, job_code, job_type, source_code, status, target_count,
                       processed_count, success_count, failed_count, skipped_count,
                       started_at, finished_at, error_msg, metadata_json
                FROM ingestion_jobs
                ORDER BY id DESC
                LIMIT 10
                """
            ).fetchall()
        finally:
            conn.close()
        by_job_status = {row["status"]: int(row["count"]) for row in job_rows}
        by_item_status = {row["status"]: int(row["count"]) for row in item_rows}
        return {
            "database_available": True,
            "jobs": {
                "total": sum(by_job_status.values()),
                "by_status": by_job_status,
            },
            "items": {
                "total": sum(by_item_status.values()),
                "by_status": by_item_status,
            },
            "recent_jobs": [self._job_row_to_dict(row) for row in recent_rows],
        }

    def _refresh_job_counts(self, conn: sqlite3.Connection, job_id: int) -> None:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM ingestion_items WHERE job_id = ? GROUP BY status",
            (job_id,),
        ).fetchall()
        counts = {row["status"]: int(row["count"]) for row in rows}
        processed = sum(counts.values())
        success = counts.get("DONE", 0) + counts.get("DUPLICATE", 0)
        failed = counts.get("FAILED", 0)
        skipped = counts.get("SKIPPED", 0)
        conn.execute(
            """
            UPDATE ingestion_jobs
            SET processed_count = ?, success_count = ?, failed_count = ?,
                skipped_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (processed, success, failed, skipped, utc_now(), job_id),
        )

    def _job_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "job_code": row["job_code"],
            "job_type": row["job_type"],
            "source_code": row["source_code"],
            "status": row["status"],
            "target_count": int(row["target_count"] or 0),
            "processed_count": int(row["processed_count"] or 0),
            "success_count": int(row["success_count"] or 0),
            "failed_count": int(row["failed_count"] or 0),
            "skipped_count": int(row["skipped_count"] or 0),
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "error_msg": row["error_msg"],
            "metadata": json_loads(row["metadata_json"]),
        }
