import tempfile
import unittest
import json
from pathlib import Path

from legal_db.ingest.local_documents import (
    discover_local_documents,
    extract_local_document_text,
    infer_material_type,
    normalize_title,
    split_chapters,
)


class LocalDocumentIngestionTest(unittest.TestCase):
    def test_normalize_title_decodes_common_download_names(self) -> None:
        self.assertEqual(
            normalize_title(Path("Communal%20harmonyEnglish_29042017_0[1].pdf")),
            "Communal harmonyEnglish 29042017 0",
        )

    def test_infer_material_type_from_filename(self) -> None:
        self.assertEqual(infer_material_type("Justice Raghubar Commission"), "REPORT")
        self.assertEqual(infer_material_type("Transfer Posting Guidelines"), "GUIDE")
        self.assertEqual(infer_material_type("Bharatiya Nyaya Sanhita 2023"), "OTHER")

    def test_discover_local_documents_skips_non_pdf_and_personal_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Legal_Report.pdf").write_bytes(b"%PDF-1.4")
            (root / "Resume.pdf").write_bytes(b"%PDF-1.4")
            (root / "contact.vcf").write_text("BEGIN:VCARD", encoding="utf-8")

            candidates, skipped, scanned = discover_local_documents(root)

        self.assertEqual(scanned, 3)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Legal Report")
        self.assertEqual(len(skipped), 2)

    def test_discover_local_documents_uses_manifest_for_public_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "IndexBNS.html").write_text("<html><body>BNS index</body></html>", encoding="utf-8")
            manifest = {
                "documents": [
                    {
                        "filename": "IndexBNS.html",
                        "title": "NCRB Sankalan BNS Index",
                        "url": "https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBNS.html",
                        "document_type": "HTML_PAGE",
                        "content_type": "text/html; charset=UTF-8",
                        "subject_tags": ["OFFICIAL_PUBLIC"],
                    }
                ]
            }
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            candidates, skipped, scanned = discover_local_documents(
                root,
                manifest_path=root / "manifest.json",
            )

        self.assertEqual(scanned, 2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(candidates[0].title, "NCRB Sankalan BNS Index")
        self.assertEqual(candidates[0].document_type, "HTML_PAGE")
        self.assertEqual(candidates[0].mime_type, "text/html")
        self.assertEqual(
            candidates[0].source_url,
            "https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBNS.html",
        )
        self.assertIn("BNS", candidates[0].subject_tags)
        self.assertIn("OFFICIAL_PUBLIC", candidates[0].subject_tags)
        self.assertNotIn("LOCAL_LIBRARY", candidates[0].subject_tags)

    def test_extract_local_document_text_supports_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bns.html"
            body = " ".join(["Bharatiya Nyaya Sanhita section"] * 40)
            path.write_text(
                f"<html><script>ignore me</script><body><h1>BNS</h1><p>{body}</p></body></html>",
                encoding="utf-8",
            )

            _, clean_text, page_count, word_count, quality = extract_local_document_text(path)

        self.assertEqual(page_count, 1)
        self.assertGreater(word_count, 80)
        self.assertGreater(quality, 0)
        self.assertIn("Bharatiya Nyaya Sanhita", clean_text)
        self.assertNotIn("ignore me", clean_text)

    def test_split_chapters_does_not_treat_plain_part_text_as_heading(self) -> None:
        text = "This is part of public servant text. " * 80
        chapters = split_chapters(text)
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0]["chapter_number"], "FULL")


if __name__ == "__main__":
    unittest.main()
