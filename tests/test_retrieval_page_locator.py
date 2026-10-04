import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from legal_db.retrieval.staging import StagingRetrievalService


class RetrievalPageLocatorTest(unittest.TestCase):
    def test_judgment_search_exposes_page_for_lexical_hit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.sqlite"
            conn = sqlite3.connect(path)
            try:
                conn.executescript("""
                    CREATE TABLE cases (id INTEGER PRIMARY KEY, title TEXT, case_number TEXT, decision_date TEXT);
                    CREATE TABLE judgments (id INTEGER PRIMARY KEY, case_id INTEGER, source_document_id INTEGER, pdf_url TEXT);
                    CREATE TABLE document_texts (source_document_id INTEGER, clean_text TEXT, page_spans_json TEXT);
                    INSERT INTO cases VALUES (1, 'Example v State', '1/2026', '2026-01-01');
                    INSERT INTO judgments VALUES (1, 1, 9, 'https://example.test/judgment.pdf');
                    """)
                conn.execute(
                    "INSERT INTO document_texts VALUES (?, ?, ?)",
                    (9, "intro text\n\nSection 138 requires notice", json.dumps([
                        {"page": 1, "character_start": 0, "character_end": 10},
                        {"page": 2, "character_start": 12, "character_end": 44},
                    ])),
                )
                conn.commit()
            finally:
                conn.close()
            results = StagingRetrievalService(path).search("Section 138 notice", source_types=["JUDGMENT"])
            self.assertEqual(results[0].metadata["page"], 2)


if __name__ == "__main__":
    unittest.main()
