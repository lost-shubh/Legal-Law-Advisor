import unittest

from legal_db.pdf.ocr import estimate_text_quality, should_extract_for_ai


class OcrQualityTest(unittest.TestCase):
    def test_estimate_text_quality_scores_dense_text_higher_than_noise(self) -> None:
        good_text = (
            "This judgment discusses Section 138 of the Negotiable Instruments Act "
            "and records the evidence, submissions, findings and final order. "
        ) * 80
        noisy_text = "??? ### \ufffd\ufffd -- " * 20

        self.assertGreaterEqual(estimate_text_quality(good_text, page_count=3), 0.6)
        self.assertLess(estimate_text_quality(noisy_text, page_count=3), 0.6)
        self.assertEqual(estimate_text_quality("", page_count=1), 0.0)

    def test_should_extract_for_ai_blocks_short_or_low_quality_text(self) -> None:
        self.assertEqual(should_extract_for_ai(99, 0.9), (False, "TOO_SHORT"))
        self.assertEqual(should_extract_for_ai(500, 0.59), (False, "OCR_QUALITY_TOO_LOW"))
        self.assertEqual(should_extract_for_ai(500, 0.6), (True, None))
        self.assertEqual(should_extract_for_ai(500, None), (True, None))


if __name__ == "__main__":
    unittest.main()
