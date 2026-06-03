import unittest

from legal_db.search.embeddings import (
    PRODUCTION_EMBEDDING_DIMENSIONS,
    build_book_embedding_text,
    build_judgment_embedding_text,
    build_section_embedding_text,
    local_hash_embedding,
)


class MappingRow(dict):
    def __getitem__(self, key):
        return self.get(key)


class ProductionEmbeddingsTest(unittest.TestCase):
    def test_local_hash_embedding_supports_pgvector_dimensions(self) -> None:
        vector = local_hash_embedding("cheque dishonour notice", PRODUCTION_EMBEDDING_DIMENSIONS)

        self.assertEqual(len(vector), 1536)

    def test_embedding_text_builders_include_context(self) -> None:
        section_text = build_section_embedding_text(
            MappingRow(
                act_name="Negotiable Instruments Act",
                section_number="138",
                section_title="Dishonour of cheque",
                section_text="Cheque dishonour and statutory notice.",
            )
        )
        judgment_text = build_judgment_embedding_text(
            MappingRow(
                neutral_citation="2026 INSC 1",
                case_number="Crl.A. 1/2026",
                petitioner="A",
                respondent="B",
                judgment_date="2026-01-01",
                clean_text="The appeal is dismissed.",
            )
        )
        book_text = build_book_embedding_text(
            MappingRow(title="Manual", chapter_title="Chapter 1", chunk_text="Legal aid.")
        )

        self.assertIn("Section 138", section_text)
        self.assertIn("A v. B", judgment_text)
        self.assertIn("Chapter 1", book_text)


if __name__ == "__main__":
    unittest.main()
