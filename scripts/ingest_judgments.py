from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.base import PoliteFetcher
from legal_db.ingest.jobs import DEFAULT_DB_PATH, IngestionJobTracker
from legal_db.ingest.judgments import JudgmentManifestIngestionPipeline, copy_manifest_template


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest judgment PDFs from a JSON manifest.")
    parser.add_argument("manifest", nargs="?", help="Path to judgment manifest JSON.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-download", action="store_true", help="Skip remote downloads.")
    parser.add_argument("--no-extract-text", action="store_true", help="Store PDFs only.")
    parser.add_argument("--user-agent", help="Override User-Agent for portals that block bots.")
    parser.add_argument("--delay-seconds", type=int, help="Override delay between remote PDF requests.")
    parser.add_argument(
        "--init-template",
        help="Copy config/judgment_manifest.example.json to this path and exit.",
    )
    parser.add_argument("--status", action="store_true", help="Print ingestion job status and exit.")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if args.init_template:
        path = copy_manifest_template(args.init_template)
        print(f"Created manifest template: {path}")
        return 0

    if args.status:
        print(json.dumps(IngestionJobTracker(db_path).status(), indent=2))
        return 0

    if not args.manifest:
        parser.error("manifest is required unless --status or --init-template is used")

    fetcher = (
        PoliteFetcher(user_agent=args.user_agent, delay_seconds=args.delay_seconds)
        if args.user_agent or args.delay_seconds is not None
        else None
    )
    pipeline = JudgmentManifestIngestionPipeline(db_path=db_path, fetcher=fetcher)
    summary = pipeline.ingest_manifest(
        args.manifest,
        limit=args.limit,
        download=not args.no_download,
        extract_text=not args.no_extract_text,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
