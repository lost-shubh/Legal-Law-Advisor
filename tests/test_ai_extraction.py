import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from legal_db.ai.extract import (
    extract_staging_judgments,
    local_extract_judgment,
    staging_extraction_status,
)


def create_extraction_db(db_path: Path, text: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE judgments (
              id INTEGER PRIMARY KEY,
              case_id INTEGER,
              source_document_id INTEGER
            );
            CREATE TABLE document_texts (
              source_document_id INTEGER,
              clean_text TEXT
            );
            """
        )
        conn.execute(
            "INSERT INTO judgments (id, case_id, source_document_id) VALUES (1, 11, 7)"
        )
        conn.execute(
            "INSERT INTO document_texts (source_document_id, clean_text) VALUES (7, ?)",
            (text,),
        )
        conn.commit()
    finally:
        conn.close()


class AiExtractionTest(unittest.TestCase):
    def test_local_extract_judgment_detects_core_fields(self) -> None:
        result = local_extract_judgment(
            """
            The appellant was prosecuted under Section 420 of the Indian Penal Code, 1860.
            Learned counsel submitted that the bank loan account was settled before the DRT.
            For these reasons, the appeal is allowed.
            """
        )

        self.assertEqual(result.payload["outcome"], "ALLOWED")
        self.assertIn("Indian Penal Code, 1860", result.payload["acts_cited"])
        self.assertIn("CRIMINAL", result.payload["issue_tags"])
        self.assertTrue(result.payload["sections_cited"])

    def test_extract_staging_judgments_writes_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            create_extraction_db(
                db_path,
                (
                    "Section 138 of the Negotiable Instruments Act was discussed. "
                    "The complainant produced the cheque, bank return memo, statutory notice, "
                    "postal receipt and account statement. The accused disputed liability and "
                    "argued that the cheque was issued only as security. The trial court reviewed "
                    "the evidence, the presumption under law, the reply notice, the testimony of "
                    "the bank witness and the documents placed on record. Learned counsel submitted "
                    "that the statutory demand was validly served and that the debt was enforceable. "
                    "The appellate court considered the reasoning, the findings and the defence "
                    "version in detail. The court held that the evidence was sufficient and the "
                    "cheque was dishonoured. For these reasons, the appeal is dismissed."
                ),
            )
            summary = extract_staging_judgments(db_path, limit=1)
            status = staging_extraction_status(db_path)

            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute(
                    "SELECT payload_json FROM staging_extractions WHERE judgment_id = 1"
                ).fetchone()
            finally:
                conn.close()

        payload = json.loads(row[0])
        self.assertTrue(summary.database_available)
        self.assertEqual(summary.processed_count, 1)
        self.assertEqual(summary.failed_count, 0)
        self.assertEqual(status["extractions"]["total"], 1)
        self.assertEqual(payload["outcome"], "DISMISSED")
        self.assertIn("CHEQUE_BOUNCE_NI_138", payload["issue_tags"])

    def test_missing_database_status_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "missing.sqlite"
            summary = extract_staging_judgments(db_path)
            status = staging_extraction_status(db_path)

        self.assertFalse(summary.database_available)
        self.assertFalse(status["database_available"])


if __name__ == "__main__":
    unittest.main()
