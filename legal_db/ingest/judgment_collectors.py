from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


DATE_PATTERNS = [
    (re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"), "%Y-%m-%d"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"), "%d/%m/%Y"),
    (re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"), "%d.%m.%Y"),
    (re.compile(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\b"), "%d %B %Y"),
]
CASE_NUMBER_RE = re.compile(
    r"\b(?:C\.?A\.?|Cr\.?A\.?|W\.?P\.?|W\.?P\.?\(C\)|W\.?P\.?\(Crl\)|"
    r"SLP|RFA|FAO|CS|ARB\.?P\.?|CRL\.?M\.?C\.?|BAIL\s+APPLN\.?|"
    r"Criminal\s+Appeal|Civil\s+Appeal|Writ\s+Petition|Suit|Appeal)"
    r"\s*(?:No\.?)?\s*[A-Za-z0-9./() -]+(?:/|of\s+)\d{4}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class JudgmentCollectorConfig:
    name: str
    source_code: str
    court_code: str
    base_url: str


COLLECTORS: dict[str, JudgmentCollectorConfig] = {
    "doj": JudgmentCollectorConfig(
        name="Department of Justice Judgment Portal",
        source_code="DOJ_JUDGMENTS",
        court_code="HC-UNKNOWN",
        base_url="https://doj.gov.in/judgment-search-portal/",
    ),
    "delhi": JudgmentCollectorConfig(
        name="Delhi High Court",
        source_code="HC_DELHI",
        court_code="HC-DEL",
        base_url="https://delhihighcourt.nic.in/",
    ),
    "bombay": JudgmentCollectorConfig(
        name="Bombay High Court",
        source_code="HC_BOMBAY",
        court_code="HC-BOM",
        base_url="https://bombayhighcourt.nic.in/",
    ),
}


@dataclass(frozen=True)
class CollectedJudgment:
    title: str
    pdf_url: str
    court_code: str
    source_code: str
    case_number: str | None = None
    judgment_date: str | None = None
    source_url: str | None = None
    raw_context: str | None = None

    def to_manifest_row(self) -> dict[str, Any]:
        metadata = {
            "collector": self.source_code,
            "source_page": self.source_url,
            "source_text": self.raw_context[:1200] if self.raw_context else None,
        }
        return {
            "title": self.title,
            "court_code": self.court_code,
            "source_code": self.source_code,
            "case_number": self.case_number,
            "neutral_citation": None,
            "judgment_date": self.judgment_date,
            "judgment_type": "FINAL",
            "pdf_url": self.pdf_url,
            "metadata": {key: value for key, value in metadata.items() if value},
        }


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_date(text: str) -> str | None:
    normalized_text = normalize_space(text)
    for pattern, date_format in DATE_PATTERNS:
        for match in pattern.findall(normalized_text):
            value = match.replace("-", "/") if date_format == "%d/%m/%Y" else match
            for candidate_format in [date_format, "%d %b %Y"]:
                try:
                    return datetime.strptime(value, candidate_format).date().isoformat()
                except ValueError:
                    continue
    return None


def extract_case_number(text: str) -> str | None:
    match = CASE_NUMBER_RE.search(text)
    return normalize_space(match.group(0)).rstrip(" .,:;") if match else None


def is_judgment_pdf_link(href: str, anchor_text: str) -> bool:
    lowered_href = href.lower()
    lowered_text = anchor_text.lower()
    return (
        ".pdf" in lowered_href
        or "judgment" in lowered_href
        or "judgement" in lowered_href
        or "order" in lowered_href
        or lowered_text in {"pdf", "download", "download pdf", "judgment", "judgement"}
    )


def nearest_context(anchor: Any) -> Any:
    for tag_name in ["tr", "li", "article"]:
        parent = anchor.find_parent(tag_name)
        if parent is not None:
            return parent
    for parent in anchor.parents:
        classes = " ".join(parent.get("class", [])) if hasattr(parent, "get") else ""
        if any(token in classes.lower() for token in ["result", "judgment", "judgement", "case"]):
            return parent
    return anchor.parent or anchor


def choose_title(anchor_text: str, context_text: str, case_number: str | None) -> str:
    generic = {"", "pdf", "download", "download pdf", "view", "judgment", "judgement", "order"}
    if anchor_text.lower() not in generic and len(anchor_text) >= 8:
        return anchor_text[:240]
    pieces = re.split(r"\s{2,}| \| |\n", context_text)
    for piece in pieces:
        candidate = normalize_space(piece)
        lowered = candidate.lower()
        if not candidate or lowered in generic:
            continue
        if case_number and case_number.lower() in lowered and len(candidate) < len(case_number) + 8:
            continue
        if DATE_PATTERNS[0][0].search(candidate) or DATE_PATTERNS[1][0].search(candidate):
            continue
        return candidate[:240]
    return case_number or "Court Judgment"


def infer_court_code(text: str, default: str) -> str:
    lowered = text.lower()
    if "delhi high court" in lowered or "high court of delhi" in lowered:
        return "HC-DEL"
    if "bombay high court" in lowered or "high court of bombay" in lowered:
        return "HC-BOM"
    if "madras high court" in lowered:
        return "HC-MAD"
    if "allahabad high court" in lowered:
        return "HC-ALL"
    if "karnataka high court" in lowered:
        return "HC-KAR"
    if "calcutta high court" in lowered:
        return "HC-CAL"
    return default


def parse_judgment_results_html(
    html: str,
    *,
    config: JudgmentCollectorConfig,
    source_url: str | None = None,
    limit: int | None = None,
) -> list[CollectedJudgment]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[CollectedJudgment] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        anchor_text = normalize_space(anchor.get_text(" "))
        href = normalize_space(anchor.get("href"))
        if not href or not is_judgment_pdf_link(href, anchor_text):
            continue
        pdf_url = urljoin(config.base_url, href)
        if pdf_url in seen_urls:
            continue
        context_node = nearest_context(anchor)
        context_text = normalize_space(context_node.get_text(" "))
        case_number = extract_case_number(context_text)
        entry = CollectedJudgment(
            title=choose_title(anchor_text, context_text, case_number),
            pdf_url=pdf_url,
            court_code=infer_court_code(context_text, config.court_code),
            source_code=config.source_code,
            case_number=case_number,
            judgment_date=parse_date(context_text),
            source_url=source_url or config.base_url,
            raw_context=context_text,
        )
        entries.append(entry)
        seen_urls.add(pdf_url)
        if limit is not None and len(entries) >= limit:
            break
    return entries


def manifest_from_entries(
    entries: list[CollectedJudgment],
    *,
    source: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "judgments": [entry.to_manifest_row() for entry in entries],
    }


def write_collector_manifest(
    entries: list[CollectedJudgment],
    output_path: str | Path,
    *,
    source: str,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest_from_entries(entries, source=source), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def generate_manifest_from_html_files(
    html_paths: list[str | Path],
    *,
    collector: str,
    output_path: str | Path,
    limit: int | None = None,
) -> Path:
    config = COLLECTORS[collector]
    entries: list[CollectedJudgment] = []
    for html_path in html_paths:
        remaining = None if limit is None else max(limit - len(entries), 0)
        if remaining == 0:
            break
        path = Path(html_path)
        entries.extend(
            parse_judgment_results_html(
                path.read_text(encoding="utf-8"),
                config=config,
                source_url=str(path),
                limit=remaining,
            )
        )
    return write_collector_manifest(entries, output_path, source=config.name)
