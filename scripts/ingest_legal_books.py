from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ingest_staging import (
    DB_PATH,
    Fetcher,
    extract_pdf_text,
    init_db,
    normalize_space,
    store_document,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "legal_books_sources.json"


BOOK_SCHEMA = """
CREATE TABLE IF NOT EXISTS legal_books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  material_type TEXT NOT NULL,
  source_code TEXT NOT NULL,
  jurisdiction TEXT DEFAULT 'INDIA',
  subject_tags TEXT,
  source_url TEXT NOT NULL,
  source_document_id INTEGER,
  content_hash TEXT,
  rights_note TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(title, source_url)
);

CREATE TABLE IF NOT EXISTS book_chapters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  chapter_number TEXT,
  chapter_title TEXT,
  start_char INTEGER,
  end_char INTEGER,
  chapter_text TEXT,
  content_hash TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(book_id, chapter_number, chapter_title)
);

CREATE TABLE IF NOT EXISTS book_chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER NOT NULL,
  chapter_id INTEGER,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  word_count INTEGER,
  content_hash TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(book_id, chapter_id, chunk_index)
);
"""


SOURCE_BASE_URLS = {
    "CBSE": "https://cbseacademic.nic.in/",
    "LAW_COMMISSION": "https://lawcommissionofindia.nic.in/",
    "NALSA": "https://nalsa.gov.in/",
}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(BOOK_SCHEMA)
    for source_code, base_url in SOURCE_BASE_URLS.items():
        conn.execute(
            "INSERT OR IGNORE INTO data_sources (source_code, base_url) VALUES (?, ?)",
            (source_code, base_url),
        )
    conn.commit()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def chunk_words(text_value: str, chunk_size: int = 750, overlap: int = 100) -> list[str]:
    words = text_value.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if len(chunk.split()) >= 30:
            chunks.append(chunk)
    return chunks


CHAPTER_RE = re.compile(
    r"(?im)^\s*(?:Chapter|CHAPTER)\s+([0-9IVXLC]+)\s*[:.\-]?\s*(.{0,140})$"
)


def split_chapters(clean_text: str) -> list[dict[str, object]]:
    matches = list(CHAPTER_RE.finditer(clean_text))
    if not matches:
        return [
            {
                "chapter_number": "FULL",
                "chapter_title": "Full document",
                "start_char": 0,
                "end_char": len(clean_text),
                "chapter_text": clean_text,
            }
        ]

    chapters: list[dict[str, object]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean_text)
        chapter_text = clean_text[start:end].strip()
        if len(chapter_text.split()) < 50:
            continue
        chapters.append(
            {
                "chapter_number": match.group(1).strip(),
                "chapter_title": normalize_space(match.group(2)) or f"Chapter {match.group(1)}",
                "start_char": start,
                "end_char": end,
                "chapter_text": chapter_text,
            }
        )
    return chapters or [
        {
            "chapter_number": "FULL",
            "chapter_title": "Full document",
            "start_char": 0,
            "end_char": len(clean_text),
            "chapter_text": clean_text,
        }
    ]


def insert_book_from_pdf(
    conn: sqlite3.Connection,
    fetcher: Fetcher,
    *,
    title: str,
    material_type: str,
    source_code: str,
    jurisdiction: str,
    subject_tags: list[str],
    url: str,
    rights_note: str,
) -> dict[str, int]:
    response = fetcher.get(url)
    if response.status_code >= 400 or not response.content.startswith(b"%PDF"):
        raise RuntimeError(f"PDF fetch failed for {url}: {response.status_code}")

    document_id = store_document(conn, response, source_code, f"{material_type}_PDF", title=title)
    local_path = conn.execute(
        "SELECT local_path, content_hash FROM source_documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    raw_text, clean_text, page_count, word_count = extract_pdf_text(Path(local_path[0]))
    conn.execute(
        """
        INSERT OR REPLACE INTO document_texts
        (source_document_id, extraction_method, page_count, word_count, raw_text, clean_text)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, "PYMUPDF", page_count, word_count, raw_text, clean_text),
    )
    conn.execute(
        """
        INSERT INTO legal_books
        (title, material_type, source_code, jurisdiction, subject_tags, source_url,
         source_document_id, content_hash, rights_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(title, source_url)
        DO UPDATE SET source_document_id = excluded.source_document_id,
                      content_hash = excluded.content_hash
        """,
        (
            title,
            material_type,
            source_code,
            jurisdiction,
            json.dumps(subject_tags),
            url,
            document_id,
            local_path[1],
            rights_note,
        ),
    )
    book_id = int(
        conn.execute(
            "SELECT id FROM legal_books WHERE title = ? AND source_url = ?",
            (title, url),
        ).fetchone()[0]
    )
    chapters = split_chapters(clean_text)
    chunk_count = 0
    for chapter in chapters:
        chapter_text = str(chapter["chapter_text"])
        conn.execute(
            """
            INSERT OR IGNORE INTO book_chapters
            (book_id, chapter_number, chapter_title, start_char, end_char, chapter_text, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                book_id,
                chapter["chapter_number"],
                chapter["chapter_title"],
                chapter["start_char"],
                chapter["end_char"],
                chapter_text,
                sha256_text(chapter_text),
            ),
        )
        chapter_id = int(
            conn.execute(
                """
                SELECT id FROM book_chapters
                WHERE book_id = ? AND chapter_number = ? AND chapter_title = ?
                """,
                (book_id, chapter["chapter_number"], chapter["chapter_title"]),
            ).fetchone()[0]
        )
        for idx, chunk in enumerate(chunk_words(chapter_text)):
            conn.execute(
                """
                INSERT OR IGNORE INTO book_chunks
                (book_id, chapter_id, chunk_index, chunk_text, word_count, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (book_id, chapter_id, idx, chunk, len(chunk.split()), sha256_text(chunk)),
            )
            chunk_count += 1
    conn.execute("UPDATE source_documents SET parse_status = 'PARSED' WHERE id = ?", (document_id,))
    conn.commit()
    return {"books": 1, "chapters": len(chapters), "chunks": chunk_count}


def discover_law_commission_reports(
    fetcher: Fetcher,
    page_url: str,
    *,
    max_reports: int,
    material_type: str,
    source_code: str,
    jurisdiction: str,
    subject_tags: list[str],
) -> list[dict[str, object]]:
    response = fetcher.get(page_url)
    soup = BeautifulSoup(response.text, "lxml")
    books: list[dict[str, object]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        if ".pdf" not in href.lower() and "uploads/" not in href.lower():
            continue
        url = urljoin(response.url, href)
        if url in seen:
            continue
        seen.add(url)
        row = anchor.find_parent("tr")
        row_text = normalize_space(row.get_text(" ", strip=True)) if row else ""
        if not row_text:
            row_text = normalize_space(anchor.get_text(" ", strip=True)) or "Law Commission Report"
        title = row_text
        if len(title) > 220:
            title = title[:220].rstrip()
        books.append(
            {
                "title": f"Law Commission: {title}",
                "material_type": material_type,
                "source_code": source_code,
                "jurisdiction": jurisdiction,
                "subject_tags": subject_tags,
                "url": url,
                "rights_note": "Official Law Commission of India report. Store source URL and do not redistribute raw PDF from repository.",
            }
        )
        if len(books) >= max_reports:
            break
    return books


def load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def ingest(limit: int | None = None) -> dict[str, int]:
    config = load_config()
    conn = init_db()
    ensure_schema(conn)
    fetcher = Fetcher()
    stats = {"attempted": 0, "books": 0, "chapters": 0, "chunks": 0, "errors": 0}
    candidates: list[dict[str, object]] = list(config.get("direct_books", []))
    for collection in config.get("law_commission_collections", []):
        candidates.extend(
            discover_law_commission_reports(
                fetcher,
                str(collection["page_url"]),
                max_reports=int(collection.get("max_reports", 5)),
                material_type=str(collection["material_type"]),
                source_code=str(collection["source_code"]),
                jurisdiction=str(collection.get("jurisdiction", "INDIA")),
                subject_tags=list(collection.get("subject_tags", [])),
            )
        )
    if limit:
        candidates = candidates[:limit]

    for book in candidates:
        stats["attempted"] += 1
        try:
            result = insert_book_from_pdf(
                conn,
                fetcher,
                title=str(book["title"]),
                material_type=str(book["material_type"]),
                source_code=str(book["source_code"]),
                jurisdiction=str(book.get("jurisdiction", "INDIA")),
                subject_tags=list(book.get("subject_tags", [])),
                url=str(book["url"]),
                rights_note=str(book.get("rights_note", "")),
            )
            stats["books"] += result["books"]
            stats["chapters"] += result["chapters"]
            stats["chunks"] += result["chunks"]
        except Exception as exc:
            stats["errors"] += 1
            conn.execute(
                """
                INSERT INTO source_documents
                (source_code, source_url, document_type, error_msg, parse_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(book.get("source_code", "UNKNOWN")),
                    str(book.get("url", "")),
                    "BOOK_PDF",
                    repr(exc),
                    "FAILED",
                ),
            )
            conn.commit()
    conn.close()
    return stats


def summary() -> dict[str, int]:
    conn = init_db()
    ensure_schema(conn)
    try:
        return {
            "legal_books": int(conn.execute("SELECT COUNT(*) FROM legal_books").fetchone()[0]),
            "book_chapters": int(conn.execute("SELECT COUNT(*) FROM book_chapters").fetchone()[0]),
            "book_chunks": int(conn.execute("SELECT COUNT(*) FROM book_chunks").fetchone()[0]),
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["ingest", "summary"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.command == "ingest":
        print(json.dumps(ingest(limit=args.limit), indent=2))
    else:
        print(json.dumps(summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

