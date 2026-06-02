from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from legal_db.ingest.base import PoliteFetcher


NEUTRAL_CITATION_RE = re.compile(r"\b(20\d{2})\s+INSC\s+(\d+)\b", re.IGNORECASE)
CASE_NUMBER_RE = re.compile(
    r"\b(?:(?:Civil|Criminal)\s+Appeal\s+No\.?\s+[A-Za-z0-9./() -]+?\s+of\s+\d{4}|"
    r"(?:Writ\s+Petition|SLP|Special\s+Leave\s+Petition|Transfer\s+Petition|"
    r"Review\s+Petition|Contempt\s+Petition)\s*(?:\([A-Za-z.]+\))?\s*"
    r"No\.?\s+[A-Za-z0-9./() -]+?\s+of\s+\d{4}|"
    r"Diary\s+No\.?\s+[A-Za-z0-9./() -]+)",
    re.IGNORECASE,
)
DATE_PATTERNS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "%Y-%m-%d"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"), "%d/%m/%Y"),
    (re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"), "%d.%m.%Y"),
    (re.compile(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b"), "%d %B %Y"),
]

GENERIC_LINK_TEXT = {
    "",
    "pdf",
    "download",
    "view",
    "open",
    "judgment",
    "judgement",
    "order",
    "read more",
}


@dataclass(frozen=True)
class SupremeCourtCitation:
    citation: str
    year: int
    number: int


@dataclass(frozen=True)
class EscrManifestEntry:
    title: str
    pdf_url: str
    judgment_date: str | None = None
    case_number: str | None = None
    neutral_citation: str | None = None
    source_url: str | None = None
    raw_context: str | None = None

    def to_manifest_row(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "collector": "scr.sci.gov.in",
            "source_page": self.source_url,
        }
        if self.raw_context:
            metadata["source_text"] = self.raw_context[:1200]
        return {
            "title": self.title,
            "court_code": "SC",
            "source_code": "ESCR",
            "case_number": self.case_number,
            "neutral_citation": self.neutral_citation,
            "judgment_date": self.judgment_date,
            "judgment_type": "FINAL",
            "pdf_url": self.pdf_url,
            "metadata": {key: value for key, value in metadata.items() if value},
        }


def extract_neutral_citations(text: str) -> list[SupremeCourtCitation]:
    citations: list[SupremeCourtCitation] = []
    for year, number in NEUTRAL_CITATION_RE.findall(text):
        citations.append(
            SupremeCourtCitation(
                citation=f"{year} INSC {int(number)}",
                year=int(year),
                number=int(number),
            )
        )
    return citations


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_judgment_date(text: str) -> str | None:
    for pattern, date_format in DATE_PATTERNS:
        for match in pattern.findall(text):
            normalized = match.replace("-", "/") if date_format == "%d/%m/%Y" else match
            for candidate_format in [date_format, "%d %b %Y"]:
                try:
                    return datetime.strptime(normalized, candidate_format).date().isoformat()
                except ValueError:
                    continue
    return None


def extract_case_number(text: str) -> str | None:
    match = CASE_NUMBER_RE.search(text)
    if not match:
        return None
    return normalize_space(match.group(0)).rstrip(" .,:;|")


def is_pdf_like_link(href: str, text: str) -> bool:
    lowered_href = href.lower()
    lowered_text = text.lower()
    return (
        ".pdf" in lowered_href
        or "dir=" in lowered_href
        or "judgment_pdf" in lowered_href
        or "judgement_pdf" in lowered_href
        or lowered_text in {"pdf", "download pdf", "view pdf"}
    )


def nearest_result_context(anchor: Any) -> Any:
    for tag_name in ["tr", "li", "article"]:
        parent = anchor.find_parent(tag_name)
        if parent is not None:
            return parent
    for parent in anchor.parents:
        classes = " ".join(parent.get("class", [])) if hasattr(parent, "get") else ""
        lowered = classes.lower()
        if any(token in lowered for token in ["result", "card", "judgment", "judgement", "item"]):
            return parent
    return anchor.parent or anchor


def choose_title(anchor_text: str, context_text: str, neutral_citation: str | None) -> str:
    if anchor_text.lower() not in GENERIC_LINK_TEXT and len(anchor_text) >= 8:
        return anchor_text[:240]
    pieces = re.split(r"\s{2,}| \| |\n", context_text)
    for piece in pieces:
        candidate = normalize_space(piece)
        lowered = candidate.lower()
        if not candidate or len(candidate) < 8:
            continue
        if neutral_citation and neutral_citation.lower() in lowered:
            continue
        if lowered in GENERIC_LINK_TEXT:
            continue
        if lowered.startswith(("pdf", "download", "neutral citation", "date", "case no")):
            continue
        if DATE_PATTERNS[0][0].search(candidate) or DATE_PATTERNS[1][0].search(candidate):
            continue
        return candidate[:240]
    return neutral_citation or "Supreme Court Judgment"


def parse_escr_results_html(
    html: str,
    *,
    base_url: str = "https://scr.sci.gov.in/scrsearch/",
    source_url: str | None = None,
    limit: int | None = None,
) -> list[EscrManifestEntry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[EscrManifestEntry] = []
    seen_pdf_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        anchor_text = normalize_space(anchor.get_text(" "))
        href = normalize_space(anchor.get("href"))
        if not href or not is_pdf_like_link(href, anchor_text):
            continue
        pdf_url = urljoin(base_url, href)
        if pdf_url in seen_pdf_urls:
            continue
        context_node = nearest_result_context(anchor)
        context_text = normalize_space(context_node.get_text(" "))
        citations = extract_neutral_citations(context_text)
        neutral_citation = citations[0].citation if citations else None
        entry = EscrManifestEntry(
            title=choose_title(anchor_text, context_text, neutral_citation),
            pdf_url=pdf_url,
            judgment_date=parse_judgment_date(context_text),
            case_number=extract_case_number(context_text),
            neutral_citation=neutral_citation,
            source_url=source_url or base_url,
            raw_context=context_text,
        )
        entries.append(entry)
        seen_pdf_urls.add(pdf_url)
        if limit is not None and len(entries) >= limit:
            break
    return entries


def manifest_from_entries(entries: list[EscrManifestEntry]) -> dict[str, Any]:
    return {
        "source": "scr.sci.gov.in",
        "court_code": "SC",
        "judgments": [entry.to_manifest_row() for entry in entries],
    }


def write_escr_manifest(entries: list[EscrManifestEntry], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest_from_entries(entries), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def generate_manifest_from_html_files(
    html_paths: list[str | Path],
    *,
    output_path: str | Path,
    base_url: str = "https://scr.sci.gov.in/scrsearch/",
    limit: int | None = None,
) -> Path:
    entries: list[EscrManifestEntry] = []
    for html_path in html_paths:
        path = Path(html_path)
        remaining = None if limit is None else max(limit - len(entries), 0)
        if remaining == 0:
            break
        entries.extend(
            parse_escr_results_html(
                path.read_text(encoding="utf-8"),
                base_url=base_url,
                source_url=str(path),
                limit=remaining,
            )
        )
    return write_escr_manifest(entries, output_path)


def generate_manifest_from_urls(
    urls: list[str],
    *,
    output_path: str | Path,
    fetcher: PoliteFetcher | None = None,
    limit: int | None = None,
) -> Path:
    active_fetcher = fetcher or PoliteFetcher()
    entries: list[EscrManifestEntry] = []
    for url in urls:
        remaining = None if limit is None else max(limit - len(entries), 0)
        if remaining == 0:
            break
        response = active_fetcher.get(url)
        if response.status_code >= 400:
            continue
        entries.extend(
            parse_escr_results_html(
                response.text,
                base_url=response.url,
                source_url=url,
                limit=remaining,
            )
        )
    return write_escr_manifest(entries, output_path)
