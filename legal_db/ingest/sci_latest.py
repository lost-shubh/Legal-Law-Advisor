from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from legal_db.ingest.base import PoliteFetcher


DEFAULT_SCI_HOME_URL = "https://www.sci.gov.in/"
DEFAULT_OUTPUT = Path("data") / "manifests" / "sc_latest_judgments.local.json"

DIARY_RE = re.compile(
    r"^(?P<diary_number>\d+)\s*/\s*(?P<diary_year>\d{4})\s+-\s+"
    r"(?P<display_date>\d{1,2}-[A-Za-z]{3}-\d{4})$"
)
UPLOADED_RE = re.compile(r"\(Uploaded On\s+(?P<uploaded_at>[^)]+)\)", re.IGNORECASE)


@dataclass(frozen=True)
class SciLatestJudgmentEntry:
    title: str
    case_number: str | None
    diary_number: str | None
    diary_year: str | None
    judgment_date: str | None
    pdf_url: str
    view_url: str
    source_url: str
    uploaded_at: str | None = None

    def to_manifest_row(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "collector": "www.sci.gov.in",
            "source_page": self.source_url,
            "view_url": self.view_url,
            "diary_number": self.diary_number,
            "diary_year": self.diary_year,
            "uploaded_at": self.uploaded_at,
        }
        return {
            "title": self.title,
            "court_code": "SC",
            "source_code": "SCI",
            "case_number": self.case_number,
            "neutral_citation": None,
            "judgment_date": self.judgment_date,
            "judgment_type": "FINAL",
            "pdf_url": self.pdf_url,
            "metadata": {key: value for key, value in metadata.items() if value},
        }


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_display_date(value: str | None) -> str | None:
    text = normalize_space(value)
    if not text:
        return None
    for date_format in ["%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def direct_sci_pdf_url(view_url: str) -> str:
    parsed = urlparse(view_url)
    path = parsed.path.replace("/view-pdf/", "/sci-get-pdf/")
    return urlunparse(parsed._replace(path=path))


def is_latest_judgment_view_url(href: str) -> bool:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    return "view-pdf" in parsed.path and query.get("type", [""])[0] == "j"


def parse_latest_judgment_text(text: str) -> dict[str, str | None]:
    uploaded_match = UPLOADED_RE.search(text)
    uploaded_at = normalize_space(uploaded_match.group("uploaded_at")) if uploaded_match else None
    clean_text = normalize_space(UPLOADED_RE.sub("", text)).rstrip(" -")

    diary_marker = " - Diary Number "
    if diary_marker not in clean_text:
        return {
            "title": clean_text,
            "case_number": None,
            "diary_number": None,
            "diary_year": None,
            "judgment_date": None,
            "uploaded_at": uploaded_at,
        }

    prefix, diary_part = clean_text.split(diary_marker, 1)
    if " - " in prefix:
        title, case_number = prefix.rsplit(" - ", 1)
    else:
        title, case_number = prefix, None

    diary_match = DIARY_RE.match(diary_part)
    if diary_match:
        diary_number = diary_match.group("diary_number")
        diary_year = diary_match.group("diary_year")
        judgment_date = parse_display_date(diary_match.group("display_date"))
    else:
        diary_number = diary_year = judgment_date = None

    return {
        "title": normalize_space(title),
        "case_number": normalize_space(case_number),
        "diary_number": diary_number,
        "diary_year": diary_year,
        "judgment_date": judgment_date,
        "uploaded_at": uploaded_at,
    }


def parse_sci_latest_judgments_html(
    html: str,
    *,
    base_url: str = DEFAULT_SCI_HOME_URL,
    source_url: str = DEFAULT_SCI_HOME_URL,
    limit: int | None = None,
) -> list[SciLatestJudgmentEntry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[SciLatestJudgmentEntry] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        view_url = urljoin(base_url, normalize_space(anchor.get("href")))
        if not is_latest_judgment_view_url(view_url) or view_url in seen_urls:
            continue

        parsed = urlparse(view_url)
        query = parse_qs(parsed.query)
        fields = parse_latest_judgment_text(normalize_space(anchor.get_text(" ")))
        judgment_date = fields["judgment_date"] or parse_display_date(
            query.get("order_date", [None])[0]
        )

        entry = SciLatestJudgmentEntry(
            title=fields["title"] or "Supreme Court Judgment",
            case_number=fields["case_number"],
            diary_number=fields["diary_number"],
            diary_year=fields["diary_year"],
            judgment_date=judgment_date,
            pdf_url=direct_sci_pdf_url(view_url),
            view_url=view_url,
            source_url=source_url,
            uploaded_at=fields["uploaded_at"],
        )
        entries.append(entry)
        seen_urls.add(view_url)
        if limit is not None and len(entries) >= limit:
            break

    return entries


def manifest_from_entries(entries: list[SciLatestJudgmentEntry]) -> dict[str, Any]:
    return {
        "source": "www.sci.gov.in",
        "court_code": "SC",
        "judgments": [entry.to_manifest_row() for entry in entries],
    }


def write_sci_latest_manifest(
    entries: list[SciLatestJudgmentEntry],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest_from_entries(entries), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def generate_latest_judgments_manifest(
    *,
    source_url: str = DEFAULT_SCI_HOME_URL,
    output_path: str | Path = DEFAULT_OUTPUT,
    fetcher: PoliteFetcher | None = None,
    limit: int | None = None,
) -> Path:
    active_fetcher = fetcher or PoliteFetcher()
    response = active_fetcher.get(source_url)
    if response.status_code >= 400:
        raise RuntimeError(f"SCI latest judgments fetch failed with HTTP {response.status_code}")
    entries = parse_sci_latest_judgments_html(
        response.text,
        base_url=response.url,
        source_url=source_url,
        limit=limit,
    )
    return write_sci_latest_manifest(entries, output_path)
