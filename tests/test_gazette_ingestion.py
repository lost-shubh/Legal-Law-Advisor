import unittest

from legal_db.ingest.gazette import extract_gazette_signal, parse_gazette_date


class GazetteIngestionTest(unittest.TestCase):
    def test_extract_gazette_signal_for_commencement_notice(self) -> None:
        text = (
            "MINISTRY OF HOME AFFAIRS S.O. 850(E). In exercise of the powers "
            "conferred by sub-section (2) of section 1 of The Bharatiya Nyaya "
            "Sanhita, 2023, the Central Government hereby appoints the 1st day "
            "of July, 2024 as the date on which the provisions shall come into force."
        )

        signal = extract_gazette_signal(text)

        self.assertEqual(signal.notification_number, "S.O. 850(E)")
        self.assertEqual(signal.notification_type, "COMMENCEMENT")
        self.assertEqual(signal.act_name, "The Bharatiya Nyaya Sanhita, 2023")
        self.assertEqual(signal.date_text, "1st day of July, 2024")
        self.assertIn("1", signal.sections_affected)

    def test_parse_gazette_date_accepts_common_formats(self) -> None:
        self.assertEqual(str(parse_gazette_date("1st day of July, 2024")), "2024-07-01")
        self.assertEqual(str(parse_gazette_date("01-07-2024")), "2024-07-01")
        self.assertEqual(str(parse_gazette_date("2024-07-01")), "2024-07-01")


if __name__ == "__main__":
    unittest.main()
