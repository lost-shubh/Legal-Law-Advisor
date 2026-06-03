from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.citations.graph import build_production_citation_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Build production citation graph from PostgreSQL judgments.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    summary = build_production_citation_graph(database_url=args.database_url, limit=args.limit)
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and not summary.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
