import unittest

from legal_db.citations.graph import citation_context, normalize_citation


class CitationGraphTest(unittest.TestCase):
    def test_normalize_citation_compacts_spacing_and_case(self) -> None:
        self.assertEqual(normalize_citation(" 2026   insc   609 "), "2026 INSC 609")

    def test_citation_context_returns_nearby_text(self) -> None:
        text = "alpha " * 20 + "2026 INSC 609" + " beta" * 20
        context = citation_context(text, text.index("2026"), text.index("2026") + 13, radius=20)

        self.assertIn("2026 INSC 609", context)


if __name__ == "__main__":
    unittest.main()
