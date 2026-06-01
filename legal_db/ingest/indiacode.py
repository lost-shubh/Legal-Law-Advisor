from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from legal_db.ingest.base import PoliteFetcher

BASE_URL = "https://www.indiacode.nic.in/"
CENTRAL_ACTS_URL = "https://www.indiacode.nic.in/handle/123456789/1362"


@dataclass(frozen=True)
class ActLink:
    title: str
    handle_url: str
    handle_id: str | None


@dataclass(frozen=True)
class SectionLink:
    number: str
    title: str | None
    url: str


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_handle_id(url: str) -> str | None:
    match = re.search(r"/handle/([^?#]+)", url)
    return match.group(1) if match else None


class IndiaCodeClient:
    def __init__(self, fetcher: PoliteFetcher | None = None) -> None:
        self.fetcher = fetcher or PoliteFetcher()

    def discover_act_links(self, collection_url: str = CENTRAL_ACTS_URL) -> list[ActLink]:
        result = self.fetcher.get(collection_url)
        soup = BeautifulSoup(result.text, "html.parser")
        links: list[ActLink] = []
        for anchor in soup.select("a[href*='/handle/']"):
            href = anchor.get("href")
            title = normalize_space(anchor.get_text(" ", strip=True))
            if not href or not title:
                continue
            url = urljoin(BASE_URL, href)
            if "/handle/123456789/" not in url:
                continue
            links.append(ActLink(title=title, handle_url=url, handle_id=extract_handle_id(url)))
        return list({item.handle_url: item for item in links}.values())

    def parse_section_links(self, act_html: str, act_url: str) -> list[SectionLink]:
        soup = BeautifulSoup(act_html, "html.parser")
        sections: list[SectionLink] = []
        for anchor in soup.select("a[href*='section']"):
            text = normalize_space(anchor.get_text(" ", strip=True))
            match = re.search(r"Section\s+([A-Za-z0-9().-]+)", text, flags=re.IGNORECASE)
            if not match:
                continue
            href = anchor.get("href")
            if not href:
                continue
            sections.append(
                SectionLink(
                    number=match.group(1),
                    title=text,
                    url=urljoin(act_url, href),
                )
            )
        return sections

    def fetch_section_text(self, section_url: str) -> str:
        result = self.fetcher.get(section_url)
        soup = BeautifulSoup(result.text, "html.parser")
        candidates = [
            ".section-content",
            "#sectionContent",
            ".act_content",
            "main",
            "body",
        ]
        for selector in candidates:
            node = soup.select_one(selector)
            if node:
                text = normalize_space(node.get_text(" ", strip=True))
                if len(text) > 50:
                    return text
        return ""

