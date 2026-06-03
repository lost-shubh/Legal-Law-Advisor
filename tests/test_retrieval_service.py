import tempfile
import unittest
import sqlite3
from pathlib import Path

from legal_db.retrieval.staging import StagingRetrievalService, make_snippet, tokenize
from legal_db.search.embeddings import build_staging_judgment_embeddings


def create_similar_case_db(db_path: Path, *, text: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE cases (
              id INTEGER PRIMARY KEY,
              title TEXT,
              case_number TEXT,
              diary_no TEXT,
              decision_date TEXT,
              source_url TEXT
            );
            CREATE TABLE source_documents (
              id INTEGER PRIMARY KEY,
              source_url TEXT
            );
            CREATE TABLE judgments (
              id INTEGER PRIMARY KEY,
              case_id INTEGER,
              source_document_id INTEGER,
              pdf_url TEXT
            );
            CREATE TABLE document_texts (
              source_document_id INTEGER,
              clean_text TEXT
            );
            """
        )
        conn.execute(
            """
            INSERT INTO cases
            (id, title, case_number, diary_no, decision_date, source_url)
            VALUES (1, 'Example Cheque Dishonour Case', 'Crl.A. No. 1/2026',
                    '123 / 2025', '2026-01-02', 'https://example.test/case')
            """
        )
        conn.execute(
            "INSERT INTO source_documents (id, source_url) VALUES (7, 'https://example.test/source')"
        )
        conn.execute(
            """
            INSERT INTO judgments (id, case_id, source_document_id, pdf_url)
            VALUES (9, 1, 7, 'https://example.test/judgment.pdf')
            """
        )
        conn.execute(
            "INSERT INTO document_texts (source_document_id, clean_text) VALUES (7, ?)",
            (text,),
        )
        conn.commit()
    finally:
        conn.close()


class RetrievalServiceTest(unittest.TestCase):
    def test_tokenize_removes_common_stopwords(self) -> None:
        self.assertIn("constitution", tokenize("What is the Constitution of India?"))
        self.assertNotIn("what", tokenize("What is the Constitution of India?"))

    def test_make_snippet_focuses_on_matching_term(self) -> None:
        text = "alpha " * 80 + "constitution basic structure judicial review " + "omega " * 80
        snippet = make_snippet(text, {"constitution"}, max_chars=120)
        self.assertIn("constitution", snippet)
        self.assertLessEqual(len(snippet), 126)

    def test_missing_staging_database_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StagingRetrievalService(Path(temp_dir) / "missing.sqlite")
            progress = service.progress()
        self.assertFalse(progress["database_available"])
        self.assertEqual(progress["current_judgments"], 0)

    def test_missing_staging_database_similar_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StagingRetrievalService(Path(temp_dir) / "missing.sqlite")
            results = service.similar_cases("Cheque dishonour notice and bank return memo")
        self.assertEqual(results, [])

    def test_similar_cases_no_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            create_similar_case_db(
                db_path,
                text="Motor accident compensation negligence tribunal insurance award.",
            )
            service = StagingRetrievalService(db_path)
            results = service.similar_cases("trademark infringement passing off dispute")
        self.assertEqual(results, [])

    def test_similar_cases_returns_ranked_judgment_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            create_similar_case_db(
                db_path,
                text=(
                    "The cheque was dishonoured after presentation. The complainant sent "
                    "a statutory legal notice and produced the bank return memo."
                ),
            )
            service = StagingRetrievalService(db_path)
            results = service.similar_cases(
                "Cheque dishonour with legal notice and bank return memo evidence",
                limit=3,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].case_title, "Example Cheque Dishonour Case")
        self.assertEqual(results[0].case_number, "Crl.A. No. 1/2026")
        self.assertEqual(results[0].decision_date, "2026-01-02")
        self.assertEqual(results[0].pdf_url, "https://example.test/judgment.pdf")
        self.assertGreater(results[0].score, 0)
        self.assertIn("cheque", results[0].snippet.lower())

    def test_semantic_search_falls_back_to_lexical_when_embeddings_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            create_similar_case_db(
                db_path,
                text="Cheque dishonour statutory notice bank return memo evidence.",
            )
            service = StagingRetrievalService(db_path)
            results = service.search(
                "cheque dishonour notice",
                source_types=["JUDGMENT"],
                mode="semantic",
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, "JUDGMENT")

    def test_semantic_search_uses_populated_staging_embeddings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            create_similar_case_db(
                db_path,
                text="Cheque dishonour statutory notice bank return memo evidence.",
            )
            summary = build_staging_judgment_embeddings(
                db_path,
                dimensions=32,
                chunk_size=20,
                overlap=0,
            )
            service = StagingRetrievalService(db_path)
            results = service.search(
                "cheque dishonour notice",
                source_types=["JUDGMENT"],
                mode="semantic",
            )

        self.assertEqual(summary.source_rows, 1)
        self.assertGreater(summary.chunks, 0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, "JUDGMENT_SEMANTIC")
        self.assertIn("model_name", results[0].metadata)

