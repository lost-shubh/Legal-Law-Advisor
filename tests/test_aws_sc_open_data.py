import json
import tempfile
import unittest
from pathlib import Path

from legal_db.ingest.aws_sc_open_data import (
    english_pdf_url,
    flatten_index_files,
    generate_aws_sc_open_data_manifest,
    metadata_filename_from_pdf,
    normalize_neutral_citation,
    parse_metadata_payload,
)


SAMPLE_RAW_HTML = """
<font size="4">
  <strong>KRISHNA DEVI <span class="fst-italic">versus</span> UNION OF INDIA</strong>
  - <span class="escrText">[2025] 1 S.C.R. 81</span>
  <span class="ncDisplay">2025 INSC 24</span>
</font>
<strong class="caseDetailsTD">
  <span>Decision Date :</span><font color="green">02-01-2025</font>
  <span>| Case No :</span><font color="green">CIVIL APPEAL No. 47/2025</font>
  <span>| Disposal Nature :</span><font color="green">Appeal(s) allowed</font>
  <span>| Bench :</span><font color="green">2 Judges</font>
</strong>
"""


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str, **_: object) -> FakeResponse:
        self.urls.append(url)
        if url.endswith("english.index.json"):
            return FakeResponse({"parts": [{"files": ["2025_1_81_92_EN.pdf"]}]})
        return FakeResponse(
            {
                "raw_html": SAMPLE_RAW_HTML,
                "path": "2025_1_81_92",
                "citation_year": "2025",
                "nc_display": "2025INSC24",
                "scraped_at": "2025-07-31T19:21:01.212042",
            }
        )


class AwsScOpenDataTest(unittest.TestCase):
    def test_index_file_helpers(self) -> None:
        self.assertEqual(metadata_filename_from_pdf("2025_1_81_92_EN.pdf"), "2025_1_81_92.json")
        self.assertIn(
            "/data/pdf/year=2025/english/2025_1_81_92_EN.pdf",
            english_pdf_url(2025, "2025_1_81_92_EN.pdf"),
        )
        self.assertEqual(flatten_index_files({"parts": [{"files": ["a.pdf"]}, {"files": ["b.pdf"]}]}), ["a.pdf", "b.pdf"])

    def test_parse_metadata_payload_extracts_manifest_fields(self) -> None:
        parsed = parse_metadata_payload(
            {
                "raw_html": SAMPLE_RAW_HTML,
                "path": "2025_1_81_92",
                "citation_year": "2025",
                "nc_display": "2025INSC24",
            }
        )

        self.assertEqual(parsed["title"], "KRISHNA DEVI versus UNION OF INDIA")
        self.assertEqual(parsed["neutral_citation"], "2025 INSC 24")
        self.assertEqual(parsed["judgment_date"], "2025-01-02")
        self.assertEqual(parsed["case_number"], "CIVIL APPEAL No. 47/2025")
        self.assertEqual(parsed["bench"], "2 Judges")

    def test_normalize_neutral_citation(self) -> None:
        self.assertEqual(normalize_neutral_citation("2025INSC24"), "2025 INSC 24")

    def test_generate_manifest_from_fake_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            summary = generate_aws_sc_open_data_manifest(
                years=[2025],
                output_path=path,
                limit=1,
                session=FakeSession(),
            )
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(summary.judgments, 1)
        self.assertEqual(data["judgments"][0]["source_code"], "SC_AWS_OPEN_DATA")
        self.assertEqual(data["judgments"][0]["court_code"], "SC")
        self.assertEqual(data["judgments"][0]["neutral_citation"], "2025 INSC 24")


if __name__ == "__main__":
    unittest.main()
