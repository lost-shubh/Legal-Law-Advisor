import unittest

from legal_db.citations.parser import extract_citations


class CitationParserTest(unittest.TestCase):
    def test_extracts_core_indian_citations(self) -> None:
        text = "See 2023 INSC 1042, (2022) 5 SCC 123 and AIR 2020 SC 1234."
        citations = extract_citations(text)
        self.assertEqual([item.reporter for item in citations], ["INSC", "SCC", "AIR_SC"])
