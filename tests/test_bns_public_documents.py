import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.bns_public_documents import (
    PUBLIC_BNS_DOCUMENTS,
    download_public_bns_documents,
)


class FakeResponse:
    def __init__(self, content: bytes, content_type: str = "text/html") -> None:
        self.content = content
        self.status_code = 200
        self.headers = {"Content-Type": content_type}


class FakeSession:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str, **_: object) -> FakeResponse:
        self.urls.append(url)
        content_type = "application/pdf" if url.endswith(".pdf") else "text/html"
        return FakeResponse(f"downloaded from {url}".encode("utf-8"), content_type)


class BnsPublicDocumentsTest(unittest.TestCase):
    def test_public_bns_documents_are_official_urls(self) -> None:
        self.assertGreaterEqual(len(PUBLIC_BNS_DOCUMENTS), 4)
        for document in PUBLIC_BNS_DOCUMENTS:
            self.assertTrue(
                document.url.startswith(
                    ("https://www.mha.gov.in/", "https://www.ncrb.gov.in/")
                )
            )
            self.assertIn("BNS", document.subject_tags)

    def test_download_public_bns_documents_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = FakeSession()
            summary = download_public_bns_documents(temp_dir, session=session)
            manifest_path = Path(summary.manifest_path or "")

            self.assertEqual(len(session.urls), len(PUBLIC_BNS_DOCUMENTS))
            self.assertEqual(len(summary.documents), len(PUBLIC_BNS_DOCUMENTS))
            self.assertFalse(summary.failed)
            self.assertTrue(manifest_path.exists())
            for item in summary.documents:
                self.assertTrue(Path(item["path"]).exists())
                self.assertIn(item["status"], {"downloaded", "existing"})
                self.assertTrue(item["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
