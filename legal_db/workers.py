from __future__ import annotations

from pathlib import Path

from celery import Celery

from legal_db.config import settings
from legal_db.pdf.ocr import extract_pdf_text

celery_app = Celery("legal_db", broker=settings.redis_url, backend=settings.redis_url)


@celery_app.task(queue="ocr", max_retries=3)
def extract_pdf_text_task(path: str) -> dict[str, object]:
    result = extract_pdf_text(Path(path))
    return {
        "pdf_type": result.pdf_type,
        "page_count": result.page_count,
        "word_count": result.word_count,
        "extraction_method": result.extraction_method,
        "clean_text_preview": result.clean_text[:500],
    }

