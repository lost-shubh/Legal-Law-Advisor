import unittest

from legal_db.case_intake.analyzer import analyze_case_text


class CaseIntakeTest(unittest.TestCase):
    def test_detects_issue_tags_and_missing_documents(self) -> None:
        analysis = analyze_case_text(
            "My cheque was dishonoured on 12/04/2025. I sent a legal notice "
            "and have the bank return memo, cheque copy and WhatsApp messages."
        )

        self.assertIn("CHEQUE_BOUNCE", analysis.issue_tags)
        self.assertIn("financial_records", analysis.evidence_found)
        self.assertIn("dishonoured cheque copy", analysis.missing_documents)
        self.assertIn("12/04/2025", analysis.dates_found)

    def test_short_case_text_gets_warning(self) -> None:
        analysis = analyze_case_text("I got a summons.")

        self.assertTrue(analysis.warnings)
        self.assertIn("court_documents", analysis.evidence_found)
