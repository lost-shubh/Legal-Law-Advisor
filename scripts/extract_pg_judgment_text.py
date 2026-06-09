from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.pg_judgment_text import backfill_production_judgment_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill PostgreSQL judgment clean_text/raw_text from locally downloaded PDFs."
    )
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--limit", type=int, help="Maximum pending judgments to process.")
    args = parser.parse_args()

    summary = backfill_production_judgment_text(
        database_url=args.database_url,
        limit=args.limit,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and summary.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
