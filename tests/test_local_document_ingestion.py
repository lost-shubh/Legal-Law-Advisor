import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.local_documents import (
    discover_local_documents,
    infer_material_type,
    normalize_title,
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


if __name__ == "__main__":
    unittest.main()
