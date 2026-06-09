from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


AWS_SC_BUCKET_BASE_URL = "https://indian-supreme-court-judgments.s3.amazonaws.com"
DEFAULT_SOURCE_CODE = "SC_AWS_OPEN_DATA"
DEFAULT_OUTPUT = Path("data") / "manifests" / "sc_aws_open_data.local.json"


@dataclass(frozen=True)
class AwsScManifestSummary:
    output: str
    years: list[int]
    judgments: int
    metadata_failed: int
    source_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output,
            "years": self.years,
            "judgments": self.judgments,
            "metadata_failed": self.metadata_failed,
            "source_code": self.source_code,
        }


def aws_url(path: str) -> str:
    return f"{AWS_SC_BUCKET_BASE_URL}/{path.lstrip('/')}"


def english_index_url(year: int) -> str:
    return aws_url(f"data/tar/year={year}/english/english.index.json")


def metadata_json_url(year: int, metadata_filename: str) -> str:
    return aws_url(f"metadata/json/year={year}/{metadata_filename}")


def english_pdf_url(year: int, pdf_filename: str) -> str:
    return aws_url(f"data/pdf/year={year}/english/{pdf_filename}")


def metadata_filename_from_pdf(pdf_filename: str) -> str:
    return re.sub(r"_EN\.pdf$", ".json", pdf_filename, flags=re.IGNORECASE)


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_neutral_citation(value: str | None) -> str | None:
    clean = normalize_space(value)
    if not clean:
        return None
    match = re.fullmatch(r"(\d{4})\s*INSC\s*(\d+)", clean, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)} INSC {int(match.group(2))}"
    return clean


def parse_date(value: str | None) -> str | None:
    clean = normalize_space(value)
    if not clean:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def flatten_index_files(index_payload: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for part in index_payload.get("parts", []):
        if not isinstance(part, dict):
            continue
        files.extend(str(item) for item in part.get("files", []) if str(item).strip())
    return files


def parse_case_details(soup: BeautifulSoup) -> dict[str, str | None]:
    details = soup.find("strong", class_="caseDetailsTD")
    if details is None:
        return {
            "judgment_date": None,
            "case_number": None,
            "disposal_nature": None,
            "bench": None,
        }
    values = [normalize_space(node.get_text(" ")) for node in details.find_all("font")]
    return {
        "judgment_date": parse_date(values[0]) if len(values) > 0 else None,
        "case_number": values[1] if len(values) > 1 else None,
        "disposal_nature": values[2] if len(values) > 2 else None,
        "bench": values[3] if len(values) > 3 else None,
    }


def parse_metadata_payload(payload: dict[str, Any]) -> dict[str, Any]:
    soup = BeautifulSoup(str(payload.get("raw_html") or ""), "html.parser")
    title = None
    citation_parent = soup.find("span", class_="ncDisplay")
    if citation_parent is not None and citation_parent.parent is not None:
        strong = citation_parent.parent.find("strong")
        if strong is not None:
            title = normalize_space(strong.get_text(" "))
    if not title:
        title = f"Supreme Court Judgment {payload.get('path') or ''}".strip()

    details = parse_case_details(soup)
    scr_citation_node = soup.find("span", class_="escrText")
    neutral_node = soup.find("span", class_="ncDisplay")
    neutral_citation = normalize_neutral_citation(
        normalize_space(neutral_node.get_text(" ")) if neutral_node else payload.get("nc_display")
    )
    return {
        "title": title,
        "case_number": details["case_number"],
        "neutral_citation": neutral_citation,
        "judgment_date": details["judgment_date"],
        "scr_citation": normalize_space(scr_citation_node.get_text(" ")) if scr_citation_node else None,
        "disposal_nature": details["disposal_nature"],
        "bench": details["bench"],
        "citation_year": payload.get("citation_year"),
        "scraped_at": payload.get("scraped_at"),
        "metadata_path": payload.get("path"),
    }


def fallback_metadata(year: int, metadata_filename: str) -> dict[str, Any]:
    stem = Path(metadata_filename).stem
    return {
        "title": f"Supreme Court Judgment {stem}",
        "case_number": None,
        "neutral_citation": None,
        "judgment_date": f"{year}-01-01",
        "scr_citation": None,
        "disposal_nature": None,
        "bench": None,
        "citation_year": str(year),
        "scraped_at": None,
        "metadata_path": stem,
    }


def build_manifest_row(
    *,
    year: int,
    pdf_filename: str,
    source_code: str,
    metadata: dict[str, Any],
    metadata_url_value: str,
) -> dict[str, Any]:
    pdf_url = english_pdf_url(year, pdf_filename)
    return {
        "title": metadata["title"],
        "court_code": "SC",
        "source_code": source_code,
        "case_number": metadata.get("case_number"),
        "neutral_citation": metadata.get("neutral_citation"),
        "judgment_date": metadata.get("judgment_date"),
        "judgment_type": "FINAL",
        "pdf_url": pdf_url,
        "metadata": {
            "collector": "aws_open_data_indian_supreme_court_judgments",
            "aws_bucket": "indian-supreme-court-judgments",
            "aws_pdf_key": f"data/pdf/year={year}/english/{pdf_filename}",
            "metadata_url": metadata_url_value,
            "metadata_path": metadata.get("metadata_path"),
            "scr_citation": metadata.get("scr_citation"),
            "disposal_nature": metadata.get("disposal_nature"),
            "bench": metadata.get("bench"),
            "citation_year": metadata.get("citation_year"),
            "scraped_at": metadata.get("scraped_at"),
        },
    }


def generate_aws_sc_open_data_manifest(
    *,
    years: list[int],
    output_path: str | Path = DEFAULT_OUTPUT,
    limit: int | None = None,
    offset: int = 0,
    source_code: str = DEFAULT_SOURCE_CODE,
    include_metadata: bool = True,
    timeout: int = 30,
    session: requests.Session | None = None,
) -> AwsScManifestSummary:
    client = session or requests.Session()
    rows: list[dict[str, Any]] = []
    metadata_failed = 0
    remaining_offset = max(offset, 0)
    max_rows = max(limit, 0) if limit is not None else None

    for year in years:
        response = client.get(english_index_url(year), timeout=timeout)
        response.raise_for_status()
        files = flatten_index_files(response.json())
        if remaining_offset:
            skipped = min(remaining_offset, len(files))
            files = files[skipped:]
            remaining_offset -= skipped
            if not files:
                continue

        for pdf_filename in files:
            if max_rows is not None and len(rows) >= max_rows:
                break
            metadata_filename = metadata_filename_from_pdf(pdf_filename)
            metadata_url_value = metadata_json_url(year, metadata_filename)
            metadata = fallback_metadata(year, metadata_filename)
            if include_metadata:
                try:
                    metadata_response = client.get(metadata_url_value, timeout=timeout)
                    metadata_response.raise_for_status()
                    metadata = parse_metadata_payload(metadata_response.json())
                except requests.RequestException:
                    metadata_failed += 1
            rows.append(
                build_manifest_row(
                    year=year,
                    pdf_filename=pdf_filename,
                    source_code=source_code,
                    metadata=metadata,
                    metadata_url_value=metadata_url_value,
                )
            )
        if max_rows is not None and len(rows) >= max_rows:
            break

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "source": "AWS Open Data - Indian Supreme Court Judgments",
                "court_code": "SC",
                "source_code": source_code,
                "judgments": rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return AwsScManifestSummary(
        output=str(output),
        years=years,
        judgments=len(rows),
        metadata_failed=metadata_failed,
        source_code=source_code,
    )
