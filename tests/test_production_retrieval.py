import unittest

from legal_db.retrieval.production import normalize_source_types


class ProductionRetrievalTest(unittest.TestCase):
    def test_normalize_source_types_maps_judgment_aliases(self) -> None:
        self.assertEqual(
            normalize_source_types(["SECTION", "JUDGMENT", "BOOK_CHUNK"]),
            {"SECTION", "JUDGMENT_CHUNK", "BOOK_CHUNK"},
        )
        self.assertEqual(normalize_source_types(["judgment_chunk"]), {"JUDGMENT_CHUNK"})

    def test_normalize_source_types_defaults_to_public_sources(self) -> None:
        self.assertEqual(
            normalize_source_types(None),
            {"SECTION", "JUDGMENT_CHUNK", "BOOK_CHUNK"},
        )


if __name__ == "__main__":
    unittest.main()
