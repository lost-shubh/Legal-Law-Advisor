import unittest

from legal_db.pdf.ocr import page_spans


class PdfPageSpansTest(unittest.TestCase):
    def test_page_spans_are_contiguous_for_page_separated_text(self) -> None:
        text = "first page\n\nsecond page\n\nthird page"
        spans = page_spans(text, 3)
        self.assertEqual(len(spans), 3)
        self.assertEqual(text[spans[0]["character_start"] : spans[0]["character_end"]], "first page")
        self.assertEqual(text[spans[1]["character_start"] : spans[1]["character_end"]], "second page")
        self.assertEqual(spans[0]["page"], 1)

    def test_page_spans_fallback_when_separator_is_missing(self) -> None:
        spans = page_spans("abcdefghij", 2)
        self.assertEqual([(item["character_start"], item["character_end"]) for item in spans], [(0, 5), (5, 10)])


if __name__ == "__main__":
    unittest.main()
