from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.sci_latest import (
    DEFAULT_OUTPUT,
    DEFAULT_SCI_HOME_URL,
    generate_latest_judgments_manifest,
)
from legal_db.ingest.base import PoliteFetcher


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 LegalLawAdvisorResearch/0.1"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a judgment manifest from the official SCI latest judgments list."
    )
    parser.add_argument("--url", default=DEFAULT_SCI_HOME_URL, help="SCI page to fetch.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for SCI, which blocks the generic project bot agent.",
    )
    args = parser.parse_args()

    path = generate_latest_judgments_manifest(
        source_url=args.url,
        output_path=args.output,
        fetcher=PoliteFetcher(user_agent=args.user_agent),
        limit=args.limit,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({"output": str(path), "judgments": len(data.get("judgments", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
