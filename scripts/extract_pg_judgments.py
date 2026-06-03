from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ai.production import extract_production_judgments, production_extraction_status
from legal_db.ai.extract import LOCAL_EXTRACTION_MODEL


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local production extraction over PostgreSQL judgments.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default=LOCAL_EXTRACTION_MODEL)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(production_extraction_status(args.database_url), indent=2, default=str))
        return 0

    summary = extract_production_judgments(
        database_url=args.database_url,
        limit=args.limit,
        model=args.model,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and summary.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
