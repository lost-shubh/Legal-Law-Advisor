import json
import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.sci_latest import (
    direct_sci_pdf_url,
    parse_sci_latest_judgments_html,
    write_sci_latest_manifest,
)


SAMPLE_SCI_HOME_HTML = """
<html>
  <body>
    <div id="latest-judgments">
      <a href="https://www.sci.gov.in/view-pdf/?diary_no=133952025&type=j&order_date=2026-06-02&from=latest_judgements_order">
        <i class="fa fa-file-pdf-o"></i>
        SONAL TALPADA VS. VEERBHAN SINGH - C.A. No. 8391/2026 - Diary Number
        13395 / 2025 - <span>02-Jun-2026</span>
        <div>(Uploaded On 03-06-2026 10:13:00)</div>
      </a>
      <a href="https://www.sci.gov.in/view-pdf/?diary_no=488092023&type=o&order_date=2026-05-20&from=latest_judgements_order">
        HANSA JAIN VS. VINOD KUMAR SANGHAI - C.A. No. 8019/2026 - Diary Number
        48809 / 2023 - <span>20-May-2026</span>
      </a>
    </div>
  </body>
</html>
"""


class SciLatestManifestTest(unittest.TestCase):
    def test_direct_sci_pdf_url_uses_pdf_endpoint(self) -> None:
        view_url = (
            "https://www.sci.gov.in/view-pdf/?diary_no=133952025&type=j"
            "&order_date=2026-06-02&from=latest_judgements_order"
        )

        pdf_url = direct_sci_pdf_url(view_url)

        self.assertIn("/sci-get-pdf/", pdf_url)
        self.assertIn("diary_no=133952025", pdf_url)

    def test_parse_sci_latest_judgments_html(self) -> None:
        entries = parse_sci_latest_judgments_html(SAMPLE_SCI_HOME_HTML, limit=10)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "SONAL TALPADA VS. VEERBHAN SINGH")
        self.assertEqual(entries[0].case_number, "C.A. No. 8391/2026")
        self.assertEqual(entries[0].diary_number, "13395")
        self.assertEqual(entries[0].diary_year, "2025")
        self.assertEqual(entries[0].judgment_date, "2026-06-02")
        self.assertEqual(entries[0].uploaded_at, "03-06-2026 10:13:00")
        self.assertIn("/sci-get-pdf/", entries[0].pdf_url)

    def test_write_sci_latest_manifest(self) -> None:
        entries = parse_sci_latest_judgments_html(SAMPLE_SCI_HOME_HTML)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_sci_latest_manifest(entries, Path(temp_dir) / "manifest.json")
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["source"], "www.sci.gov.in")
        self.assertEqual(data["judgments"][0]["court_code"], "SC")
        self.assertEqual(data["judgments"][0]["source_code"], "SCI")
        self.assertEqual(data["judgments"][0]["judgment_type"], "FINAL")


if __name__ == "__main__":
    unittest.main()
