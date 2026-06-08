import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.corpus_progress import (
    build_progress,
    normalize_production_progress,
    read_staging_counts,
)


TARGETS = {
    "target_judgments": 10000,
    "court_level_mix": [{"court_level": "SUPREME", "target_count": 1}],
    "domain_mix": [{"domain": "CRIMINAL", "target_count": 1}],
}


class CorpusProgressTest(unittest.TestCase):
    def test_read_staging_counts_handles_missing_optional_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("CREATE TABLE judgments (id INTEGER)")
                conn.execute("CREATE TABLE statutes (id INTEGER)")
                conn.execute("CREATE TABLE sections (id INTEGER)")
                conn.executemany("INSERT INTO judgments (id) VALUES (?)", [(1,), (2,)])
                conn.execute("INSERT INTO statutes (id) VALUES (1)")
                conn.executemany("INSERT INTO sections (id) VALUES (?)", [(1,), (2,), (3,)])
                conn.commit()
            finally:
                conn.close()

            counts = read_staging_counts(db_path)

        self.assertEqual(counts["judgments"], 2)
        self.assertEqual(counts["statutes"], 1)
        self.assertEqual(counts["sections"], 3)
        self.assertEqual(counts["book_chunks"], 0)

    def test_build_progress_can_force_sqlite_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_path = root / "targets.json"
            db_path = root / "staging.sqlite"
            target_path.write_text(json.dumps(TARGETS), encoding="utf-8")
            sqlite3.connect(db_path).close()

            progress = build_progress(
                staging_db_path=db_path,
                target_path=target_path,
                prefer_production=False,
            )

        self.assertEqual(progress["database"], "sqlite")
        self.assertEqual(progress["current_judgments"], 0)
        self.assertEqual(progress["target_judgments"], 10000)

    def test_normalize_production_progress_preserves_pg_counts(self) -> None:
        progress = normalize_production_progress(
            {
                "database_available": True,
                "database": "postgresql",
                "current_judgments": 25,
                "statutes": 851,
                "sections": 38094,
                "legal_books": 63,
                "book_chunks": 3377,
                "embeddings": 42663,
                "section_embeddings": 38094,
                "judgment_embeddings": 1192,
                "book_embeddings": 3377,
            },
            TARGETS,
        )

        self.assertEqual(progress["database"], "postgresql")
        self.assertEqual(progress["current_sections"], 38094)
        self.assertEqual(progress["current_legal_books"], 63)
        self.assertEqual(progress["current_embeddings"], 42663)


if __name__ == "__main__":
    unittest.main()
