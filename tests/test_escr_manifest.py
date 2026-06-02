import json
import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.escr import (
    extract_neutral_citations,
    generate_manifest_from_html_files,
    parse_escr_results_html,
)


SAMPLE_ESCR_HTML = """
<html>
  <body>
    <table>
      <tr>
        <td>Example Petitioner v. Union of India</td>
        <td>Civil Appeal No. 1234 of 2025</td>
        <td>2025 INSC 77</td>
        <td>15 May 2025</td>
        <td><a href="/?dir=admin/judgement_pdf/2025/example.pdf">PDF</a></td>
      </tr>
      <tr>
        <td>State of Example v. Accused Person</td>
        <td>Criminal Appeal No. 55 of 2024</td>
        <td>2024 INSC 902</td>
        <td>2024-11-02</td>
        <td><a href="https://scr.sci.gov.in/judgment_pdf/2024/state.pdf">Download PDF</a></td>
      </tr>
    </table>
  </body>
</html>
"""


class EscrManifestTest(unittest.TestCase):
    def test_extract_neutral_citations(self) -> None:
        citations = extract_neutral_citations("See 2025 INSC 77 and 2024 INSC 902.")

        self.assertEqual(citations[0].citation, "2025 INSC 77")
        self.assertEqual(citations[1].year, 2024)

    def test_parse_escr_results_html_to_manifest_entries(self) -> None:
        entries = parse_escr_results_html(
            SAMPLE_ESCR_HTML,
            base_url="https://scr.sci.gov.in/scrsearch/",
            source_url="fixture.html",
        )

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].neutral_citation, "2025 INSC 77")
        self.assertEqual(entries[0].case_number, "Civil Appeal No. 1234 of 2025")
        self.assertEqual(entries[0].judgment_date, "2025-05-15")
        self.assertIn("dir=admin/judgement_pdf", entries[0].pdf_url)
        self.assertEqual(entries[1].judgment_date, "2024-11-02")

    def test_generate_manifest_from_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "results.html"
            output_path = root / "manifest.json"
            html_path.write_text(SAMPLE_ESCR_HTML, encoding="utf-8")

            generate_manifest_from_html_files([html_path], output_path=output_path, limit=1)

            data = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(data["source"], "scr.sci.gov.in")
        self.assertEqual(len(data["judgments"]), 1)
        self.assertEqual(data["judgments"][0]["court_code"], "SC")
        self.assertEqual(data["judgments"][0]["source_code"], "ESCR")
