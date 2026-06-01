import unittest

from legal_db.search.embeddings import chunk_words


class ChunkingTest(unittest.TestCase):
    def test_chunk_words_with_overlap(self) -> None:
        chunks = chunk_words(" ".join(str(i) for i in range(20)), chunk_size=10, overlap=2)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].split()[-2:], chunks[1].split()[:2])
