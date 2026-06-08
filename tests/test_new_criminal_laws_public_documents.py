import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.new_criminal_laws_public_documents import (
    PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS,
    download_public_new_criminal_law_documents,
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


class NewCriminalLawsPublicDocumentsTest(unittest.TestCase):
    def test_public_documents_are_official_urls_for_three_new_laws(self) -> None:
        law_tags = {document.law_tag for document in PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS}
        self.assertTrue({"BNS", "BNSS", "BSA"}.issubset(law_tags))
        self.assertGreaterEqual(len(PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS), 18)
        for document in PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS:
            self.assertTrue(
                document.url.startswith(
                    ("https://www.mha.gov.in/", "https://www.ncrb.gov.in/")
                )
            )
            self.assertIn("OFFICIAL_PUBLIC", document.all_subject_tags())
            self.assertIn("NEW_CRIMINAL_LAWS", document.all_subject_tags())

    def test_download_public_documents_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = FakeSession()
            summary = download_public_new_criminal_law_documents(temp_dir, session=session)
            manifest_path = Path(summary.manifest_path or "")

            self.assertEqual(len(session.urls), len(PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS))
            self.assertEqual(len(summary.documents), len(PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS))
            self.assertFalse(summary.failed)
            self.assertTrue(manifest_path.exists())
            self.assertEqual(summary.source_code, "NEW_CRIMINAL_LAWS_PUBLIC")
            for item in summary.documents:
                self.assertTrue(Path(item["path"]).exists())
                self.assertIn(item["status"], {"downloaded", "existing"})
                self.assertTrue(item["url"].startswith("https://"))
                self.assertIn("subject_tags", item)


if __name__ == "__main__":
    unittest.main()
