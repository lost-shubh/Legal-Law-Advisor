import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.jobs import IngestionJobTracker
from legal_db.ingest.judgments import JudgmentManifestIngestionPipeline


class IngestionJobsTest(unittest.TestCase):
    def test_tracker_records_item_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            tracker = IngestionJobTracker(db_path)
            job = tracker.create_job("TEST_JOB", source_code="TEST", target_count=2)
            tracker.record_item(
                job.id,
                item_key="a",
                item_type="JUDGMENT_PDF",
                status="DONE",
                source_url="https://example.test/a.pdf",
            )
            tracker.record_item(
                job.id,
                item_key="b",
                item_type="JUDGMENT_PDF",
                status="FAILED",
                source_url="https://example.test/b.pdf",
                error_msg="bad pdf",
            )
            tracker.finish_job(job.id)

            status = tracker.status()

        self.assertTrue(status["database_available"])
        self.assertEqual(status["jobs"]["by_status"]["DONE"], 1)
        self.assertEqual(status["items"]["by_status"]["DONE"], 1)
        self.assertEqual(status["items"]["by_status"]["FAILED"], 1)
        self.assertEqual(status["recent_jobs"][0]["processed_count"], 2)

    def test_manifest_pipeline_stores_local_pdf_without_text_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "staging.sqlite"
            raw_dir = root / "raw"
            pdf_path = root / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n% local test pdf\n%%EOF")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "judgments": [
                            {
                                "title": "Example Legal Case",
                                "court_code": "SC",
                                "source_code": "ESCR",
                                "case_number": "Civil Appeal No. 1 of 2025",
                                "neutral_citation": "2025 INSC 1",
                                "judgment_date": "2025-01-01",
                                "local_pdf_path": str(pdf_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            pipeline = JudgmentManifestIngestionPipeline(db_path=db_path, raw_dir=raw_dir)
            summary = pipeline.ingest_manifest(
                manifest_path,
                download=False,
                extract_text=False,
            )

            conn = sqlite3.connect(db_path)
            try:
                source_docs = conn.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0]
                cases = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
                judgments = conn.execute("SELECT COUNT(*) FROM judgments").fetchone()[0]
            finally:
                conn.close()
            raw_pdf_exists = any(raw_dir.rglob("*.pdf"))

        self.assertEqual(summary.success_count, 1)
        self.assertEqual(summary.failed_count, 0)
        self.assertEqual(source_docs, 1)
        self.assertEqual(cases, 1)
        self.assertEqual(judgments, 1)
        self.assertTrue(raw_pdf_exists)
