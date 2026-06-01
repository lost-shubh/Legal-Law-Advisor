from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
sys.path.insert(0, str(ROOT))

from legal_db.llm.ollama import OllamaChatClient


def tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]{3,}", value.lower()) if len(token) >= 3}


def retrieve_book_context(question: str, limit: int = 5) -> str:
    if not DB_PATH.exists():
        return ""
    terms = tokenize(question)
    if not terms:
        return ""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT b.title, c.chapter_title, bc.chunk_text
            FROM book_chunks bc
            JOIN legal_books b ON b.id = bc.book_id
            LEFT JOIN book_chapters c ON c.id = bc.chapter_id
            LIMIT 2000
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return ""
    finally:
        conn.close()

    scored: list[tuple[int, str]] = []
    for title, chapter_title, chunk_text in rows:
        chunk_terms = tokenize(chunk_text)
        score = len(terms & chunk_terms)
        if score:
            scored.append(
                (
                    score,
                    f"Source: {title} / {chapter_title or 'chapter'}\n{chunk_text}",
                )
            )
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n---\n\n".join(item[1] for item in scored[:limit])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--context-limit", type=int, default=5)
    args = parser.parse_args()

    context = retrieve_book_context(args.question, limit=args.context_limit)
    answer = OllamaChatClient().chat(args.question, context=context)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
