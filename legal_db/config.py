from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://legal:legal@localhost:5432/legaldb",
    )
    pg_dsn: str = os.getenv("PG_DSN", "postgresql://legal:legal@localhost:5432/legaldb")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    object_storage_backend: str = os.getenv("OBJECT_STORAGE_BACKEND", "local")
    local_storage_root: Path = Path(
        os.getenv("LOCAL_STORAGE_ROOT", "F:/indian-legal-database/data")
    )

    s3_endpoint_url: str | None = os.getenv("S3_ENDPOINT_URL")
    s3_access_key_id: str | None = os.getenv("S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = os.getenv("S3_SECRET_ACCESS_KEY")
    s3_raw_bucket: str = os.getenv("S3_RAW_BUCKET", "legal-docs-raw")
    s3_ocr_bucket: str = os.getenv("S3_OCR_BUCKET", "legal-docs-ocr")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_extraction_model: str = os.getenv("OPENAI_EXTRACTION_MODEL", "gpt-4.1-mini")

    scrape_user_agent: str = os.getenv(
        "SCRAPE_USER_AGENT",
        "IndianLegalDatabaseResearchBot/0.1 contact@example.com",
    )
    scrape_delay_seconds: int = _get_int("SCRAPE_DELAY_SECONDS", 3)
    max_pdf_mb: int = _get_int("MAX_PDF_MB", 100)


settings = Settings()

