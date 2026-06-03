from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.bns_public_documents import (
    DEFAULT_OUTPUT_DIR,
    download_public_bns_documents,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download official/public BNS documents for local corpus ingestion."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replace", action="store_true", help="Re-download existing files.")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    summary = download_public_bns_documents(
        args.output_dir,
        dry_run=args.dry_run,
        replace=args.replace,
        timeout=args.timeout,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
