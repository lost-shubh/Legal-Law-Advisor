import tempfile
import unittest
from pathlib import Path

from legal_db.retrieval.staging import StagingRetrievalService, make_snippet, tokenize


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

