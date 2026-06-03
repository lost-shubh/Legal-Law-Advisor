from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.search.embeddings import build_production_embeddings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local deterministic 1536-d embeddings in PostgreSQL/pgvector."
    )
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument(
        "--source-type",
        action="append",
        choices=["SECTION", "JUDGMENT_CHUNK", "BOOK_CHUNK"],
        help="Source type to embed. Repeat to include multiple. Defaults to all supported types.",
    )
    parser.add_argument("--limit", type=int, help="Limit source rows per source type.")
    parser.add_argument("--replace", action="store_true", help="Delete existing rows for selected types/model first.")
    args = parser.parse_args()

    summary = build_production_embeddings(
        database_url=args.database_url,
        source_types=args.source_type,
        limit=args.limit,
        replace=args.replace,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
