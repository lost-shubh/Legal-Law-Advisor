import unittest

from legal_db.ingest.pg_judgment_text import PgJudgmentTextBackfillSummary


class PgJudgmentTextBackfillTest(unittest.TestCase):
    def test_summary_to_dict(self) -> None:
        summary = PgJudgmentTextBackfillSummary(
            database_available=True,
            target_count=2,
            processed_count=2,
            success_count=1,
            failed_count=1,
            errors=[{"judgment_id": 7, "error": "bad pdf"}],
        )

        payload = summary.to_dict()

        self.assertTrue(payload["database_available"])
        self.assertEqual(payload["target_count"], 2)
        self.assertEqual(payload["success_count"], 1)
        self.assertEqual(payload["failed_count"], 1)
        self.assertEqual(payload["errors"][0]["judgment_id"], 7)


if __name__ == "__main__":
    unittest.main()
