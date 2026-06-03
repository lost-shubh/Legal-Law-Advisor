import unittest

from legal_db.case_intake.analyzer import analyze_case_text
from legal_db.case_intake.pipeline import CaseIntakePipeline


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

    def test_private_defence_homicide_fact_pattern_gets_specific_tags(self) -> None:
        analysis = analyze_case_text(
            "On 25th of May 2026 around 12 AM an intruder broke into my house "
            "through the back entrance, broke my locker and safe, and attacked me. "
            "My son held him and I used a wooden stick to protect my family. "
            "The intruder was later found dead and police arrested me for murder. "
            "CCTV camera footage is available and I have no personal advocate."
        )

        self.assertIn("MURDER_CHARGE", analysis.issue_tags)
        self.assertIn("PRIVATE_DEFENCE", analysis.issue_tags)
        self.assertIn("NIGHT_HOUSE_BREAKING", analysis.issue_tags)
        self.assertIn("CULPABLE_HOMICIDE", analysis.issue_tags)
        self.assertIn("LEGAL_AID_NEED", analysis.issue_tags)
        self.assertIn("digital_evidence", analysis.evidence_found)
        self.assertIn("medical_forensic_records", analysis.evidence_found)
        self.assertIn("25th of May 2026", analysis.dates_found)
        self.assertTrue(any("Murder/private-defence" in warning for warning in analysis.warnings))

    def test_case_pipeline_prepends_private_defence_anchors(self) -> None:
        class FakeRetrievalService:
            def __init__(self) -> None:
                self.query = ""

            def retrieve_context(self, query: str, limit: int = 5) -> tuple[str, list]:
                self.query = query
                return "", []

        retrieval = FakeRetrievalService()
        response = CaseIntakePipeline(retrieval_service=retrieval).analyze(
            "An intruder broke into my house at 12 AM, attacked me, and later died. "
            "Police arrested me for murder. CCTV footage exists and I have no personal advocate.",
            use_llm=False,
        )

        titles = [item.title for item in response.retrieved_results]
        self.assertIn("BNS Section 34: Things done in private defence", titles)
        self.assertIn("BNS Section 41: Private defence of property extending to causing death", titles)
        self.assertIn("BNS Section 103: Punishment for murder", titles)
        self.assertIn("BNSS Sections 340-341: Defence by advocate and legal aid", titles)
        self.assertNotIn(
            "BNS Section 76: Assault or use of criminal force to woman with intent to disrobe",
            titles,
        )
        self.assertIn("private defence", retrieval.query.lower())
        self.assertIn("house-breaking", retrieval.query.lower())
