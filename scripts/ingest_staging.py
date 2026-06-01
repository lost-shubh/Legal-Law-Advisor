from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.parse import parse_qs

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "legal_corpus_staging.sqlite"

USER_AGENT = "IndianLegalDatabaseResearchBot/0.1 local-research"
REQUEST_DELAY_SECONDS = 2


@dataclass(frozen=True)
class PriorityAct:
    short_title: str
    act_name: str
    year: int
    url: str | None
    pdf_urls: tuple[str, ...] = ()


PRIORITY_ACTS: list[PriorityAct] = [
    PriorityAct(
        "BNS",
        "The Bharatiya Nyaya Sanhita, 2023",
        2023,
        "https://www.indiacode.nic.in/handle/123456789/20062",
        ("https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf",),
    ),
    PriorityAct(
        "BNSS",
        "The Bharatiya Nagarik Suraksha Sanhita, 2023",
        2023,
        "https://www.indiacode.nic.in/handle/123456789/20099",
        (
            "https://www.indiacode.nic.in/bitstream/123456789/21544/1/"
            "the_bharatiya_nagarik_suraksha_sanhita%2C_2023.pdf",
        ),
    ),
    PriorityAct(
        "BSA",
        "The Bharatiya Sakshya Adhiniyam, 2023",
        2023,
        "https://www.indiacode.nic.in/handle/123456789/20063",
        ("https://www.indiacode.nic.in/bitstream/123456789/20063/1/aa202347.pdf",),
    ),
    PriorityAct(
        "DPDP",
        "The Digital Personal Data Protection Act, 2023",
        2023,
        "https://www.indiacode.nic.in/handle/123456789/22037",
        ("https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf",),
    ),
    PriorityAct(
        "NI_ACT",
        "The Negotiable Instruments Act, 1881",
        1881,
        "https://www.indiacode.nic.in/handle/123456789/2189",
        ("https://www.indiacode.nic.in/bitstream/123456789/2189/1/a1881-26.pdf",),
    ),
    PriorityAct(
        "IT_ACT",
        "The Information Technology Act, 2000",
        2000,
        "https://www.indiacode.nic.in/handle/123456789/1999",
        ("https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf",),
    ),
    PriorityAct(
        "CONSUMER",
        "The Consumer Protection Act, 2019",
        2019,
        None,
        ("https://www.indiacode.nic.in/bitstream/123456789/18964/1/cpa.pdf",),
    ),
    PriorityAct(
        "HMA",
        "The Hindu Marriage Act, 1955",
        1955,
        "https://www.indiacode.nic.in/handle/123456789/1560",
        ("https://www.indiacode.nic.in/bitstream/123456789/1560/1/A1955-25.pdf",),
    ),
    PriorityAct(
        "DV_ACT",
        "The Protection of Women from Domestic Violence Act, 2005",
        2005,
        "https://www.indiacode.nic.in/handle/123456789/2021",
        ("https://www.indiacode.nic.in/bitstream/123456789/2021/5/A2005-43.pdf",),
    ),
    PriorityAct(
        "TPA",
        "The Transfer of Property Act, 1882",
        1882,
        None,
        ("https://www.indiacode.nic.in/bitstream/123456789/14648/1/tpa.pdf",),
    ),
    PriorityAct(
        "CONSTITUTION",
        "The Constitution of India",
        1950,
        "https://www.indiacode.nic.in/handle/123456789/19150",
        ("https://www.indiacode.nic.in/bitstream/123456789/19150/1/constitution_of_india.pdf",),
    ),
    PriorityAct(
        "MV_ACT",
        "The Motor Vehicles Act, 1988",
        1988,
        "https://www.indiacode.nic.in/handle/123456789/1798",
        ("https://www.indiacode.nic.in/bitstream/123456789/9460/1/a1988-59.pdf",),
    ),
    PriorityAct(
        "ID_ACT",
        "The Industrial Disputes Act, 1947",
        1947,
        "https://www.indiacode.nic.in/handle/123456789/22042",
        (
            "https://cgit.labour.gov.in/sites/default/files/"
            "Industrial%20Disputes%20Act%2C%201947%28%20as%20amended%20by%20"
            "Finance%20Act%2C2017%29.pdf",
        ),
    ),
    PriorityAct(
        "IPC",
        "The Indian Penal Code, 1860",
        1860,
        "https://www.indiacode.nic.in/handle/123456789/12850",
        ("https://www.indiacode.nic.in/bitstream/123456789/4219/1/THE-INDIAN-PENAL-CODE-1860.pdf",),
    ),
    PriorityAct(
        "CRPC",
        "The Code of Criminal Procedure, 1973",
        1973,
        "https://www.indiacode.nic.in/handle/123456789/15247",
        (
            "https://www.indiacode.nic.in/bitstream/123456789/21613/1/"
            "the_code_of_criminal_procedure%2C_1973.pdf",
        ),
    ),
    PriorityAct(
        "EVIDENCE",
        "The Indian Evidence Act, 1872",
        1872,
        "https://www.indiacode.nic.in/handle/123456789/15351",
        ("https://www.indiacode.nic.in/bitstream/123456789/15351/1/iea_1872.pdf",),
    ),
]


SOURCE_SEEDS = {
    "INDIA_CODE": "https://www.indiacode.nic.in/",
    "EGAZETTE": "https://egazette.gov.in/",
    "SCI": "https://www.sci.gov.in/",
    "ESCR": "https://scr.sci.gov.in/scrsearch/",
    "DOJ_JUDGMENTS": "https://doj.gov.in/judgment-search-portal/",
    "ECOURTS": "https://services.ecourts.gov.in/ecourtindia_v6/",
    "NJDG": "https://doj.gov.in/the-national-judicial-data-grid-njdg/",
    "LABOUR": "https://labour.gov.in/",
    "CGIT": "https://cgit.labour.gov.in/",
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS data_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_code TEXT UNIQUE NOT NULL,
  base_url TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_code TEXT NOT NULL,
  source_url TEXT NOT NULL,
  final_url TEXT,
  document_type TEXT NOT NULL,
  local_path TEXT,
  content_hash TEXT,
  mime_type TEXT,
  byte_size INTEGER,
  http_status INTEGER,
  fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
  title TEXT,
  parse_status TEXT DEFAULT 'PENDING',
  error_msg TEXT,
  UNIQUE(source_url, content_hash)
);

CREATE TABLE IF NOT EXISTS statutes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  short_title TEXT,
  act_name TEXT NOT NULL,
  year INTEGER,
  jurisdiction TEXT DEFAULT 'CENTRAL',
  source_url TEXT,
  source_document_id INTEGER,
  content_hash TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(act_name, year, jurisdiction)
);

CREATE TABLE IF NOT EXISTS sections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  statute_id INTEGER NOT NULL,
  section_number TEXT NOT NULL,
  section_title TEXT,
  section_text TEXT,
  source_url TEXT,
  source_document_id INTEGER,
  content_hash TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(statute_id, section_number, content_hash)
);

CREATE TABLE IF NOT EXISTS document_texts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_document_id INTEGER NOT NULL,
  extraction_method TEXT NOT NULL,
  page_count INTEGER,
  word_count INTEGER,
  raw_text TEXT,
  clean_text TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_document_id, extraction_method)
);

CREATE TABLE IF NOT EXISTS discovered_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_document_id INTEGER,
  source_url TEXT NOT NULL,
  link_url TEXT NOT NULL,
  link_text TEXT,
  link_type TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(parent_document_id, link_url)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_type TEXT NOT NULL,
  started_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  status TEXT NOT NULL,
  stats_json TEXT,
  error_msg TEXT
);

CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_code TEXT NOT NULL,
  court_code TEXT NOT NULL,
  diary_no TEXT,
  case_number TEXT,
  title TEXT,
  decision_date TEXT,
  source_url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(court_code, diary_no, decision_date, source_url)
);

CREATE TABLE IF NOT EXISTS judgments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id INTEGER NOT NULL,
  source_document_id INTEGER NOT NULL,
  judgment_type TEXT,
  judgment_date TEXT,
  pdf_url TEXT,
  page_count INTEGER,
  word_count INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(case_id, source_document_id)
);
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def source_code_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "cgit.labour.gov.in" in host:
        return "CGIT"
    if "labour.gov.in" in host:
        return "LABOUR"
    if "indiacode.nic.in" in host:
        return "INDIA_CODE"
    return "INDIA_CODE"


def init_db(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    for source_code, base_url in SOURCE_SEEDS.items():
        conn.execute(
            "INSERT OR IGNORE INTO data_sources (source_code, base_url) VALUES (?, ?)",
            (source_code, base_url),
        )
    conn.commit()
    return conn


class Fetcher:
    def __init__(self, delay_seconds: int = REQUEST_DELAY_SECONDS) -> None:
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self.last_fetch = 0.0

    def get(self, url: str) -> requests.Response:
        elapsed = time.monotonic() - self.last_fetch
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        response = self.session.get(url, timeout=45, allow_redirects=True)
        self.last_fetch = time.monotonic()
        return response


def local_path_for(url: str, content_hash: str, document_type: str) -> Path:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_") or "unknown-host"
    suffix = ".pdf" if "PDF" in document_type else ".html"
    return RAW_DIR / host / content_hash[:2] / f"{content_hash}{suffix}"


def store_document(
    conn: sqlite3.Connection,
    response: requests.Response,
    source_code: str,
    document_type: str,
    title: str | None = None,
) -> int:
    data = response.content
    digest = sha256_bytes(data)
    path = local_path_for(response.url, digest, document_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    conn.execute(
        """
        INSERT OR IGNORE INTO source_documents
        (source_code, source_url, final_url, document_type, local_path, content_hash,
         mime_type, byte_size, http_status, title)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_code,
            response.request.url,
            response.url,
            document_type,
            str(path),
            digest,
            response.headers.get("content-type"),
            len(data),
            response.status_code,
            title,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM source_documents WHERE source_url = ? AND content_hash = ?",
        (response.request.url, digest),
    ).fetchone()
    if not row:
        raise RuntimeError("failed to store source document")
    return int(row[0])


def discover_pdf_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        text = normalize_space(anchor.get_text(" ", strip=True))
        absolute = urljoin(base_url, href)
        lowered = (href + " " + text).lower()
        if ".pdf" in lowered or "download" in lowered or "view" in lowered:
            links.append((absolute, text))
    return list(dict.fromkeys(links))


def extract_section_blocks(html: str) -> list[tuple[str, str | None, str]]:
    soup = BeautifulSoup(html, "lxml")
    text = normalize_space(soup.get_text(" ", strip=True))
    blocks: list[tuple[str, str | None, str]] = []
    pattern = re.compile(
        r"(?:^|\s)(?:Section\s+)?([0-9]+[A-Z]?(?:[A-Z])?)\.\s+(.{20,2500}?)(?=\s(?:Section\s+)?[0-9]+[A-Z]?\.\s+|$)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        number = match.group(1)
        body = normalize_space(match.group(2))
        title = body[:160]
        if len(body) >= 40:
            blocks.append((number, title, body))
    return blocks


def clean_pdf_text(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(path: Path) -> tuple[str, str, int, int]:
    import fitz

    doc = fitz.open(path)
    raw_text = "\n\n".join(page.get_text("text") for page in doc)
    clean_text = clean_pdf_text(raw_text)
    return raw_text, clean_text, doc.page_count, len(clean_text.split())


SECTION_HEADER_RE = re.compile(
    r"(?ms)^\s*(\d+[A-Z]?)\.\s+([^\n]{3,220})\n(.*?)(?=^\s*\d+[A-Z]?\.\s+[^\n]{3,220}\n|\Z)"
)


def extract_sections_from_text(text: str) -> list[tuple[str, str | None, str]]:
    found: dict[str, tuple[str | None, str]] = {}
    for match in SECTION_HEADER_RE.finditer(text):
        number = match.group(1).strip()
        title = normalize_space(match.group(2))
        body = normalize_space(match.group(2) + " " + match.group(3))
        if len(body.split()) < 8:
            continue
        existing = found.get(number)
        if existing is None or len(body) > len(existing[1]):
            found[number] = (title, body)
    return [(number, title, body) for number, (title, body) in found.items()]


def view_pdf_to_get_pdf(url: str) -> str:
    return url.replace("/view-pdf/", "/sci-get-pdf/")


def parse_latest_sc_links(html: str, base_url: str) -> list[dict[str, str | None]]:
    soup = BeautifulSoup(html, "lxml")
    links: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href*='view-pdf']"):
        href = anchor.get("href")
        if not href:
            continue
        view_url = urljoin(base_url, href)
        if view_url in seen:
            continue
        seen.add(view_url)
        text = normalize_space(anchor.get_text(" ", strip=True))
        parsed = urlparse(view_url)
        query = parse_qs(parsed.query)
        title = text.split(" - ")[0] if text else None
        case_number = None
        match = re.search(r"\s-\s(.+?)\s-\sDiary Number", text)
        if match:
            case_number = normalize_space(match.group(1))
        links.append(
            {
                "title": title,
                "case_number": case_number,
                "diary_no": (query.get("diary_no") or [None])[0],
                "order_date": (query.get("order_date") or [None])[0],
                "type": (query.get("type") or [None])[0],
                "view_url": view_url,
                "pdf_url": view_pdf_to_get_pdf(view_url),
            }
        )
    return links


def discover_act_url(fetcher: Fetcher, act: PriorityAct) -> str | None:
    if act.url:
        return act.url
    query = requests.utils.quote(act.act_name)
    candidates = [
        f"https://www.indiacode.nic.in/search?query={query}",
        f"https://www.indiacode.nic.in/simple-search?query={query}",
    ]
    for url in candidates:
        try:
            response = fetcher.get(url)
        except requests.RequestException:
            continue
        if response.status_code >= 400:
            continue
        soup = BeautifulSoup(response.text, "lxml")
        target_words = set(re.findall(r"[a-z0-9]+", act.act_name.lower()))
        best: tuple[int, str] | None = None
        for anchor in soup.select("a[href*='/handle/']"):
            text = normalize_space(anchor.get_text(" ", strip=True))
            href = anchor.get("href") or ""
            words = set(re.findall(r"[a-z0-9]+", text.lower()))
            score = len(target_words & words)
            if score >= 3:
                absolute = urljoin(response.url, href)
                if best is None or score > best[0]:
                    best = (score, absolute)
        if best:
            return best[1]
    return None


def ingest_priority_acts(limit: int | None = None) -> dict[str, int]:
    conn = init_db()
    fetcher = Fetcher()
    run_id = conn.execute(
        "INSERT INTO ingestion_runs (run_type, status) VALUES (?, ?)",
        ("priority_acts", "RUNNING"),
    ).lastrowid
    stats = {
        "acts_attempted": 0,
        "acts_downloaded": 0,
        "pdfs_downloaded": 0,
        "sections_extracted": 0,
        "pdf_texts_extracted": 0,
        "errors": 0,
    }
    try:
        acts = PRIORITY_ACTS[:limit] if limit else PRIORITY_ACTS
        for act in acts:
            stats["acts_attempted"] += 1
            try:
                act_url = discover_act_url(fetcher, act)
                if not act_url and not act.pdf_urls:
                    stats["errors"] += 1
                    continue
                document_id = None
                digest = None
                if act_url:
                    response = fetcher.get(act_url)
                    if response.status_code < 400 and b"Access Denied" not in response.content:
                        document_id = store_document(
                            conn,
                            response,
                            "INDIA_CODE",
                            "ACT_HTML",
                            title=act.act_name,
                        )
                        digest = sha256_bytes(response.content)
                conn.execute(
                    """
                    INSERT INTO statutes
                    (short_title, act_name, year, source_url, source_document_id, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(act_name, year, jurisdiction)
                    DO UPDATE SET source_url = excluded.source_url,
                                  source_document_id = excluded.source_document_id,
                                  content_hash = excluded.content_hash
                    """,
                    (
                        act.short_title,
                        act.act_name,
                        act.year,
                        act_url or (act.pdf_urls[0] if act.pdf_urls else None),
                        document_id,
                        digest,
                    ),
                )
                statute_id = int(
                    conn.execute(
                        "SELECT id FROM statutes WHERE act_name = ? AND year = ? AND jurisdiction = 'CENTRAL'",
                        (act.act_name, act.year),
                    ).fetchone()[0]
                )
                if document_id:
                    sections = extract_section_blocks(response.text)
                    for number, title, body in sections:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO sections
                            (statute_id, section_number, section_title, section_text, source_url,
                             source_document_id, content_hash)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                statute_id,
                                number,
                                title,
                                body,
                                act_url,
                                document_id,
                                hashlib.sha256(body.encode("utf-8")).hexdigest(),
                            ),
                        )
                    stats["sections_extracted"] += len(sections)
                    for link_url, link_text in discover_pdf_links(response.text, response.url)[:5]:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO discovered_links
                            (parent_document_id, source_url, link_url, link_text, link_type)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (document_id, response.url, link_url, link_text, "PDF_OR_DOWNLOAD"),
                        )
                    conn.execute(
                        "UPDATE source_documents SET parse_status = 'PARSED' WHERE id = ?",
                        (document_id,),
                    )
                for pdf_url in act.pdf_urls:
                    pdf_response = fetcher.get(pdf_url)
                    if pdf_response.status_code >= 400 or not pdf_response.content.startswith(b"%PDF"):
                        stats["errors"] += 1
                        continue
                    pdf_document_id = store_document(
                        conn,
                        pdf_response,
                        source_code_for_url(pdf_url),
                        "ACT_PDF",
                        title=act.act_name,
                    )
                    stats["pdfs_downloaded"] += 1
                    local_path = conn.execute(
                        "SELECT local_path FROM source_documents WHERE id = ?",
                        (pdf_document_id,),
                    ).fetchone()[0]
                    raw_text, clean_text, page_count, word_count = extract_pdf_text(Path(local_path))
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO document_texts
                        (source_document_id, extraction_method, page_count, word_count, raw_text, clean_text)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (pdf_document_id, "PYMUPDF", page_count, word_count, raw_text, clean_text),
                    )
                    stats["pdf_texts_extracted"] += 1
                    sections = extract_sections_from_text(clean_text)
                    for number, title, body in sections:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO sections
                            (statute_id, section_number, section_title, section_text, source_url,
                             source_document_id, content_hash)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                statute_id,
                                number,
                                title,
                                body,
                                pdf_url,
                                pdf_document_id,
                                hashlib.sha256(body.encode("utf-8")).hexdigest(),
                            ),
                        )
                    stats["sections_extracted"] += len(sections)
                    conn.execute(
                        "UPDATE source_documents SET parse_status = 'PARSED' WHERE id = ?",
                        (pdf_document_id,),
                    )
                conn.commit()
                stats["acts_downloaded"] += 1
            except Exception as exc:
                stats["errors"] += 1
                conn.execute(
                    """
                    INSERT INTO source_documents
                    (source_code, source_url, document_type, http_status, error_msg, parse_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("INDIA_CODE", act.url or act.act_name, "ACT_HTML", None, repr(exc), "FAILED"),
                )
                conn.commit()
        conn.execute(
            """
            UPDATE ingestion_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP, stats_json = ?
            WHERE id = ?
            """,
            ("DONE", json.dumps(stats), run_id),
        )
        conn.commit()
        return stats
    except Exception as exc:
        conn.execute(
            """
            UPDATE ingestion_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP, stats_json = ?, error_msg = ?
            WHERE id = ?
            """,
            ("FAILED", json.dumps(stats), repr(exc), run_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def ingest_sc_latest(limit: int = 25, judgment_only: bool = True) -> dict[str, int]:
    conn = init_db()
    fetcher = Fetcher()
    run_id = conn.execute(
        "INSERT INTO ingestion_runs (run_type, status) VALUES (?, ?)",
        ("sc_latest_judgments", "RUNNING"),
    ).lastrowid
    stats = {
        "links_found": 0,
        "links_attempted": 0,
        "pdfs_downloaded": 0,
        "texts_extracted": 0,
        "cases_inserted_or_seen": 0,
        "judgments_inserted_or_seen": 0,
        "errors": 0,
    }
    try:
        home = fetcher.get("https://www.sci.gov.in/")
        home_document_id = store_document(
            conn,
            home,
            "SCI",
            "HTML_PAGE",
            title="Supreme Court latest judgments page",
        )
        links = parse_latest_sc_links(home.text, home.url)
        if judgment_only:
            links = [link for link in links if link.get("type") == "j"]
        stats["links_found"] = len(links)
        for link in links[:limit]:
            stats["links_attempted"] += 1
            try:
                pdf_url = link["pdf_url"]
                if not pdf_url:
                    stats["errors"] += 1
                    continue
                pdf_response = fetcher.get(pdf_url)
                if pdf_response.status_code >= 400 or not pdf_response.content.startswith(b"%PDF"):
                    stats["errors"] += 1
                    continue
                pdf_document_id = store_document(
                    conn,
                    pdf_response,
                    "SCI",
                    "JUDGMENT_PDF",
                    title=link.get("title"),
                )
                stats["pdfs_downloaded"] += 1
                local_path = conn.execute(
                    "SELECT local_path FROM source_documents WHERE id = ?",
                    (pdf_document_id,),
                ).fetchone()[0]
                raw_text, clean_text, page_count, word_count = extract_pdf_text(Path(local_path))
                conn.execute(
                    """
                    INSERT OR REPLACE INTO document_texts
                    (source_document_id, extraction_method, page_count, word_count, raw_text, clean_text)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (pdf_document_id, "PYMUPDF", page_count, word_count, raw_text, clean_text),
                )
                stats["texts_extracted"] += 1
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cases
                    (source_code, court_code, diary_no, case_number, title, decision_date, source_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "SCI",
                        "SC",
                        link.get("diary_no"),
                        link.get("case_number"),
                        link.get("title"),
                        link.get("order_date"),
                        link.get("view_url"),
                    ),
                )
                case_id = int(
                    conn.execute(
                        """
                        SELECT id FROM cases
                        WHERE court_code = 'SC' AND source_url = ?
                        """,
                        (link.get("view_url"),),
                    ).fetchone()[0]
                )
                stats["cases_inserted_or_seen"] += 1
                conn.execute(
                    """
                    INSERT OR IGNORE INTO judgments
                    (case_id, source_document_id, judgment_type, judgment_date, pdf_url,
                     page_count, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        pdf_document_id,
                        "FINAL" if link.get("type") == "j" else "ORDER",
                        link.get("order_date"),
                        pdf_url,
                        page_count,
                        word_count,
                    ),
                )
                stats["judgments_inserted_or_seen"] += 1
                conn.execute(
                    "UPDATE source_documents SET parse_status = 'PARSED' WHERE id IN (?, ?)",
                    (home_document_id, pdf_document_id),
                )
                conn.commit()
            except Exception as exc:
                stats["errors"] += 1
                conn.execute(
                    """
                    INSERT INTO source_documents
                    (source_code, source_url, document_type, error_msg, parse_status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("SCI", str(link.get("pdf_url")), "JUDGMENT_PDF", repr(exc), "FAILED"),
                )
                conn.commit()
        conn.execute(
            """
            UPDATE ingestion_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP, stats_json = ?
            WHERE id = ?
            """,
            ("DONE", json.dumps(stats), run_id),
        )
        conn.commit()
        return stats
    except Exception as exc:
        conn.execute(
            """
            UPDATE ingestion_runs
            SET status = ?, finished_at = CURRENT_TIMESTAMP, stats_json = ?, error_msg = ?
            WHERE id = ?
            """,
            ("FAILED", json.dumps(stats), repr(exc), run_id),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def summarize() -> dict[str, int]:
    conn = init_db()
    try:
        result = {}
        for table in [
            "data_sources",
            "source_documents",
            "statutes",
            "sections",
            "document_texts",
            "discovered_links",
            "cases",
            "judgments",
        ]:
            result[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return result
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "ingest-priority-acts", "ingest-sc-latest", "summary"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-orders", action="store_true")
    args = parser.parse_args()

    if args.command == "init":
        init_db().close()
        print(json.dumps({"db": str(DB_PATH)}, indent=2))
    elif args.command == "ingest-priority-acts":
        print(json.dumps(ingest_priority_acts(limit=args.limit), indent=2))
    elif args.command == "ingest-sc-latest":
        print(
            json.dumps(
                ingest_sc_latest(limit=args.limit or 25, judgment_only=not args.include_orders),
                indent=2,
            )
        )
    else:
        print(json.dumps(summarize(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
