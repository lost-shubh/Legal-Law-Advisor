from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
TARGET_PATH = ROOT / "config" / "case_corpus_targets.json"


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "what",
    "when",
    "where",
    "which",
    "under",
    "about",
    "into",
    "case",
    "law",
}


@dataclass(frozen=True)
class SearchResult:
    source_type: str
    title: str
    snippet: str
    score: float
    source_url: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "source_url": self.source_url,
            "metadata": self.metadata or {},
        }


def tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]{2,}", value.lower())
        if token not in STOPWORDS
    }


def make_snippet(text: str, terms: set[str], max_chars: int = 700) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars:
        return clean
    lowered = clean.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    start = max(min(positions) - max_chars // 3, 0) if positions else 0
    end = min(start + max_chars, len(clean))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end].strip()}{suffix}"


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()[0]
        > 0
    )


def count_if_exists(conn: sqlite3.Connection, table_name: str) -> int:
    if not table_exists(conn, table_name):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


class StagingRetrievalService:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def is_available(self) -> bool:
        return self.db_path.exists()

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Staging database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def progress(self) -> dict[str, Any]:
        targets = json.loads(TARGET_PATH.read_text(encoding="utf-8")) if TARGET_PATH.exists() else {}
        target_judgments = int(targets.get("target_judgments", 0) or 0)
        if not self.db_path.exists():
            return {
                "database_available": False,
                "target_judgments": target_judgments,
                "current_judgments": 0,
                "remaining_judgments": target_judgments,
                "judgment_progress_percent": 0,
            }
        with self._connect() as conn:
            current_judgments = count_if_exists(conn, "judgments")
            return {
                "database_available": True,
                "target_judgments": target_judgments,
                "current_judgments": current_judgments,
                "remaining_judgments": max(target_judgments - current_judgments, 0),
                "judgment_progress_percent": round(
                    (current_judgments / target_judgments) * 100, 3
                )
                if target_judgments
                else None,
                "statutes": count_if_exists(conn, "statutes"),
                "sections": count_if_exists(conn, "sections"),
                "document_texts": count_if_exists(conn, "document_texts"),
                "legal_books": count_if_exists(conn, "legal_books"),
                "book_chunks": count_if_exists(conn, "book_chunks"),
                "cases": count_if_exists(conn, "cases"),
            }

    def search(self, query: str, limit: int = 10, source_types: list[str] | None = None) -> list[SearchResult]:
        terms = tokenize(query)
        if not terms or not self.db_path.exists():
            return []
        allowed = set(source_types or ["SECTION", "BOOK_CHUNK", "JUDGMENT"])
        with self._connect() as conn:
            results: list[SearchResult] = []
            if "SECTION" in allowed and table_exists(conn, "sections"):
                results.extend(self._search_sections(conn, terms, query))
            if "BOOK_CHUNK" in allowed and table_exists(conn, "book_chunks"):
                results.extend(self._search_book_chunks(conn, terms))
            if "JUDGMENT" in allowed and table_exists(conn, "judgments"):
                results.extend(self._search_judgments(conn, terms))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[: max(min(limit, 50), 1)]

    def retrieve_context(self, query: str, limit: int = 5) -> tuple[str, list[SearchResult]]:
        results = self.search(query, limit=limit)
        parts = [
            f"Source: {item.source_type} | {item.title}\nURL: {item.source_url or 'local'}\n{item.snippet}"
            for item in results
        ]
        return "\n\n---\n\n".join(parts), results

    def _score(self, text: str, terms: set[str], exact_bonus: float = 0) -> float:
        lowered = text.lower()
        score = sum(1 for term in terms if term in lowered)
        return float(score) + exact_bonus

    def _search_sections(
        self, conn: sqlite3.Connection, terms: set[str], query: str
    ) -> list[SearchResult]:
        rows = conn.execute(
            """
            SELECT s.section_number, s.section_title, s.section_text, s.source_url,
                   st.short_title, st.act_name
            FROM sections s
            JOIN statutes st ON st.id = s.statute_id
            WHERE s.section_text IS NOT NULL
            """
        ).fetchall()
        results = []
        for number, title, text, source_url, short_title, act_name in rows:
            haystack = f"{number} {title or ''} {text}"
            exact_bonus = 3 if str(number).lower() in query.lower() else 0
            score = self._score(haystack, terms, exact_bonus=exact_bonus)
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_type="SECTION",
                    title=f"{short_title or act_name} Section {number}: {title or ''}".strip(),
                    snippet=make_snippet(text or "", terms),
                    score=score,
                    source_url=source_url,
                    metadata={"section_number": number, "act_name": act_name},
                )
            )
        return results

    def _search_book_chunks(
        self, conn: sqlite3.Connection, terms: set[str]
    ) -> list[SearchResult]:
        rows = conn.execute(
            """
            SELECT b.title, c.chapter_title, bc.chunk_text, b.source_url
            FROM book_chunks bc
            JOIN legal_books b ON b.id = bc.book_id
            LEFT JOIN book_chapters c ON c.id = bc.chapter_id
            """
        ).fetchall()
        results = []
        for title, chapter, chunk_text, source_url in rows:
            score = self._score(chunk_text, terms)
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_type="BOOK_CHUNK",
                    title=f"{title} / {chapter or 'Full document'}",
                    snippet=make_snippet(chunk_text, terms),
                    score=score,
                    source_url=source_url,
                    metadata={"chapter_title": chapter},
                )
            )
        return results

    def _search_judgments(
        self, conn: sqlite3.Connection, terms: set[str]
    ) -> list[SearchResult]:
        rows = conn.execute(
            """
            SELECT c.title, c.case_number, c.decision_date, j.pdf_url, dt.clean_text
            FROM judgments j
            JOIN cases c ON c.id = j.case_id
            JOIN document_texts dt ON dt.source_document_id = j.source_document_id
            WHERE dt.clean_text IS NOT NULL
            """
        ).fetchall()
        results = []
        for title, case_number, decision_date, pdf_url, clean_text in rows:
            score = self._score(clean_text, terms)
            if score <= 0:
                continue
            results.append(
                SearchResult(
                    source_type="JUDGMENT",
                    title=f"{title or 'Supreme Court Judgment'} ({case_number or 'case number unavailable'})",
                    snippet=make_snippet(clean_text, terms),
                    score=score,
                    source_url=pdf_url,
                    metadata={"decision_date": decision_date, "case_number": case_number},
                )
            )
        return results
