import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_staging_to_postgres import row_value, split_case_title, staging_counts


class MigrationHelperTest(unittest.TestCase):
    def test_split_case_title_handles_common_versus_forms(self) -> None:
        self.assertEqual(split_case_title("Amit Kumar v. State of Delhi"), ("Amit Kumar", "State of Delhi"))
        self.assertEqual(split_case_title("Company Ltd versus Buyer"), ("Company Ltd", "Buyer"))
        self.assertEqual(split_case_title("Standalone Case Title"), ("Standalone Case Title", None))
        self.assertEqual(split_case_title("   "), (None, None))

    def test_staging_counts_returns_zero_for_missing_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "staging.sqlite"
            conn = sqlite3.connect(db_path)
            try:
                conn.execute("CREATE TABLE cases (id INTEGER PRIMARY KEY)")
                conn.executemany("INSERT INTO cases DEFAULT VALUES", [(), ()])
                conn.commit()
            finally:
                conn.close()

            counts = staging_counts(db_path)

        self.assertEqual(counts["cases"], 2)
        self.assertEqual(counts["judgments"], 0)
        self.assertEqual(counts["staging_embeddings"], 0)

    def test_row_value_returns_default_for_missing_column(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("CREATE TABLE example (name TEXT)")
            conn.execute("INSERT INTO example (name) VALUES ('BNS')")
            row = conn.execute("SELECT * FROM example").fetchone()
        finally:
            conn.close()

        self.assertEqual(row_value(row, "name"), "BNS")
        self.assertEqual(row_value(row, "missing", "fallback"), "fallback")


if __name__ == "__main__":
    unittest.main()
