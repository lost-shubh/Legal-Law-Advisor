import unittest

from legal_db.quality.checks import quality_sql
from legal_db.quality.production import quality_gate_passed


class QualityChecksTest(unittest.TestCase):
    def test_quality_sql_includes_backend_completion_checks(self) -> None:
        sql = quality_sql()
        self.assertIn("duplicate_source_documents", sql)
        self.assertIn("duplicate_case_sources", sql)
        self.assertIn("sections_without_text", sql)

    def test_quality_gate_requires_database_and_no_error_failures(self) -> None:
        self.assertFalse(quality_gate_passed({"database_available": False}))
        self.assertFalse(
            quality_gate_passed(
                {"database_available": True, "summary": {"errors": 0, "error_failures": 1}}
            )
        )
        self.assertTrue(
            quality_gate_passed(
                {"database_available": True, "summary": {"errors": 0, "error_failures": 0}}
            )
        )


if __name__ == "__main__":
    unittest.main()
