import json
import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.judgment_collectors import (
    COLLECTORS,
    generate_manifest_from_html_files,
    parse_judgment_results_html,
)


SAMPLE_DELHI_HTML = """
<html><body>
  <table>
    <tr>
      <td>Example Petitioner v. State</td>
      <td>W.P.(C) 123/2024</td>
      <td>15 May 2024</td>
      <td><a href="/judgments/example.pdf">PDF</a></td>
    </tr>
  </table>
</body></html>
"""


class JudgmentCollectorsTest(unittest.TestCase):
    def test_parse_saved_high_court_html(self) -> None:
        entries = parse_judgment_results_html(
            SAMPLE_DELHI_HTML,
            config=COLLECTORS["delhi"],
            source_url="fixture.html",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].court_code, "HC-DEL")
        self.assertEqual(entries[0].source_code, "HC_DELHI")
        self.assertEqual(entries[0].judgment_date, "2024-05-15")
        self.assertIn("example.pdf", entries[0].pdf_url)

    def test_generate_manifest_from_saved_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "results.html"
            output_path = root / "manifest.json"
            html_path.write_text(SAMPLE_DELHI_HTML, encoding="utf-8")

            generate_manifest_from_html_files(
                [html_path],
                collector="delhi",
                output_path=output_path,
            )
            data = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(data["judgments"]), 1)
        self.assertEqual(data["judgments"][0]["court_code"], "HC-DEL")


if __name__ == "__main__":
    unittest.main()
