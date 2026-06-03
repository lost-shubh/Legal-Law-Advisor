from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ai.extract import (
    LOCAL_EXTRACTION_MODEL,
    extract_staging_judgments,
    staging_extraction_status,
)
from legal_db.ingest.jobs import DEFAULT_DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local deterministic extraction over staging judgment text."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--model", default=LOCAL_EXTRACTION_MODEL)
    parser.add_argument("--status", action="store_true", help="Print extraction status and exit.")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(staging_extraction_status(args.db_path), indent=2))
        return 0

    summary = extract_staging_judgments(
        args.db_path,
        limit=args.limit,
        model=args.model,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
