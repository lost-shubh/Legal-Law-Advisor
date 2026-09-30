import unittest

from legal_db.llm.rag import RagResponse
from legal_db.retrieval.staging import SearchResult
from legal_db.verified.research import build_verified_research


class FakePipeline:
    def __init__(self, response: RagResponse) -> None:
        self.response = response

    def answer(self, question: str, context_limit: int, use_llm: bool) -> RagResponse:
        return self.response


class VerifiedResearchTest(unittest.TestCase):
    def test_supported_claim_is_retained(self) -> None:
        result = build_verified_research(
            "What does Section 138 require?",
            pipeline=FakePipeline(
                RagResponse(
                    prompt="What does Section 138 require?",
                    answer="Section 138 requires a statutory notice.",
                    model="test-model",
                    model_status="ok",
                    retrieved_results=[
                        SearchResult(
                            source_type="SECTION",
                            title="Negotiable Instruments Act Section 138",
                            snippet="Section 138 requires a statutory notice before further proceedings.",
                            score=0.9,
                            source_url="https://example.test/section-138",
                        )
                    ],
                )
            ),
        )
        self.assertEqual(result["verification_status"], "verified_with_evidence")
        self.assertEqual(result["claims"][0]["support"], "supported")
        self.assertIn("notice", result["claims"][0]["matched_terms"])
        self.assertTrue(result["claims"][0]["evidence_excerpts"])
        self.assertEqual(result["claims"][0]["evidence_locations"][0]["type"], "retrieved_excerpt")
        self.assertIn("locator", result["evidence"][0])
        self.assertGreater(result["claims"][0]["confidence"], 0.5)
        self.assertTrue(result["verified_answer"])

    def test_no_evidence_abstains(self) -> None:
        result = build_verified_research(
            "Question without a matching authority",
            pipeline=FakePipeline(
                RagResponse(
                    prompt="Question without a matching authority",
                    answer=None,
                    model=None,
                    model_status="skipped",
                    retrieved_results=[],
                )
            ),
        )
        self.assertEqual(result["verification_status"], "abstained_no_evidence")
        self.assertIsNone(result["verified_answer"])


if __name__ == "__main__":
    unittest.main()
