import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.central_acts import (
    extract_sections_from_act_text,
    normalize_act_title,
    read_manifest_candidates,
)


class CentralActsIngestionTest(unittest.TestCase):
    def test_normalize_act_title_removes_final_year_period(self) -> None:
        self.assertEqual(
            normalize_act_title(
                "The Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016."
            ),
            "The Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016",
        )

    def test_read_manifest_candidates_resolves_downloaded_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "act.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            (root / "manifest.csv").write_text(
                "\n".join(
                    [
                        '"index","handle","act_id","act_number","act_year","short_title","item_url","pdf_url","file_path","bytes","sha256","status","http_status","downloaded_at"',
                        f'"1","2160","201618","18","2016","The Aadhaar Act, 2016.","https://www.indiacode.nic.in/handle/123456789/2160","https://www.indiacode.nic.in/bitstream/123456789/2160/1/a.pdf","{pdf_path}","8","abc","downloaded","200","2026-06-03T22:52:51"',
                    ]
                ),
                encoding="utf-8",
            )

            candidates, skipped, scanned = read_manifest_candidates(root)

        self.assertEqual(scanned, 1)
        self.assertFalse(skipped)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].handle, "2160")
        self.assertEqual(candidates[0].act_year, 2016)
        self.assertEqual(candidates[0].title, "The Aadhaar Act, 2016")

    def test_extract_sections_ignores_toc_and_footnotes(self) -> None:
        body = """
        ARRANGEMENT OF SECTIONS
        SECTIONS
        1. Short title, extent and commencement.
        2. Definitions.

        ACT NO. 18 OF 2016
        [25th March, 2016.]
        An Act to provide legal text.

        1. Subs. by Act 10 of 2020, s. 2.
        This is only a footnote and should not be treated as section one.

        1. Short title, extent and commencement.—(1) This Act may be called the Example Act, 2016.
        (2) It extends to the whole of India.

        2. Definitions.—In this Act, unless the context otherwise requires, "Authority" means the
        statutory authority established under this Act for administering the law.
        """

        sections = extract_sections_from_act_text(body)

        self.assertEqual([section["number"] for section in sections], ["1", "2"])
        self.assertIn("Short title", sections[0]["title"])
        self.assertNotIn("Subs. by Act", sections[0]["text"])
        self.assertIn("Definitions", sections[1]["title"])


if __name__ == "__main__":
    unittest.main()
