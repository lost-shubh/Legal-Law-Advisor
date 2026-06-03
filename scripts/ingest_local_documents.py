from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.local_documents import ingest_local_library


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest a local folder of PDF legal documents into PostgreSQL legal_books/book_chunks."
    )
    parser.add_argument("folder", help="Local folder containing PDFs.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--source-code", default="LOCAL_LIBRARY")
    parser.add_argument("--source-name", default="Local User Document Library")
    parser.add_argument("--include-personal", action="store_true", help="Do not skip personal-looking PDFs.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-words", type=int, default=80)
    args = parser.parse_args()

    summary = ingest_local_library(
        args.folder,
        database_url=args.database_url,
        source_code=args.source_code,
        source_name=args.source_name,
        include_personal=args.include_personal,
        dry_run=args.dry_run,
        limit=args.limit,
        min_words=args.min_words,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and not summary.error else 1


if __name__ == "__main__":
    raise SystemExit(main())
