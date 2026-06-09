from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.aws_sc_open_data import (
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE_CODE,
    generate_aws_sc_open_data_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a judgment manifest from AWS Open Data Supreme Court judgments."
    )
    parser.add_argument("--years", nargs="+", type=int, required=True, help="Years to include, in order.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, help="Maximum rows across all requested years.")
    parser.add_argument("--offset", type=int, default=0, help="Skip this many rows before writing.")
    parser.add_argument("--source-code", default=DEFAULT_SOURCE_CODE)
    parser.add_argument("--no-metadata", action="store_true", help="Do not fetch per-judgment metadata JSON.")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    summary = generate_aws_sc_open_data_manifest(
        years=args.years,
        output_path=args.output,
        limit=args.limit,
        offset=args.offset,
        source_code=args.source_code,
        include_metadata=not args.no_metadata,
        timeout=args.timeout,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
