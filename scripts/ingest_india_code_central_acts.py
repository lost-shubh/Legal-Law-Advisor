from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.central_acts import (
    DEFAULT_SOURCE_CODE,
    DEFAULT_SOURCE_NAME,
    import_central_acts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import locally downloaded India Code Central Act PDFs into PostgreSQL "
            "source_documents/statutes/sections."
        )
    )
    parser.add_argument("folder", help="Folder containing manifest.csv and Central Act PDFs.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--source-code", default=DEFAULT_SOURCE_CODE)
    parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
    parser.add_argument("--manifest-name", default="manifest.csv")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-words", type=int, default=80)
    args = parser.parse_args()

    summary = import_central_acts(
        args.folder,
        database_url=args.database_url,
        source_code=args.source_code,
        source_name=args.source_name,
        manifest_name=args.manifest_name,
        dry_run=args.dry_run,
        limit=args.limit,
        min_words=args.min_words,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and not summary.error else 1


if __name__ == "__main__":
    raise SystemExit(main())
