import unittest
from decimal import Decimal

from legal_db.ai.production import parse_money_to_decimal


class ProductionExtractionTest(unittest.TestCase):
    def test_parse_money_to_decimal_handles_indian_money_text(self) -> None:
        self.assertEqual(parse_money_to_decimal("Rs. 1,25,000"), Decimal("125000"))
        self.assertEqual(parse_money_to_decimal("INR 5000.50"), Decimal("5000.50"))
        self.assertIsNone(parse_money_to_decimal(None))
        self.assertIsNone(parse_money_to_decimal("not available"))


if __name__ == "__main__":
    unittest.main()
