from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ai.production import LOCAL_EXTRACTION_MODEL, extract_production_judgments
from legal_db.citations.graph import build_production_citation_graph
from legal_db.quality.production import quality_gate_passed, run_production_quality_checks
from legal_db.retrieval.staging import DEFAULT_DB_PATH
from legal_db.search.embeddings import build_production_embeddings
from scripts.migrate_staging_to_postgres import migrate


def append_step(report: dict[str, Any], name: str, payload: dict[str, Any], ok: bool) -> None:
    report["steps"].append({"name": name, "ok": ok, "payload": payload})
    if not ok:
        report["ok"] = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the production backend maintenance pipeline in order."
    )
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite staging DB path.")
    parser.add_argument("--include-migration", action="store_true")
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument("--skip-extraction", action="store_true")
    parser.add_argument("--skip-citations", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit per production processing step.")
    parser.add_argument("--replace-embeddings", action="store_true")
    parser.add_argument("--model", default=LOCAL_EXTRACTION_MODEL)
    args = parser.parse_args()

    report: dict[str, Any] = {"ok": True, "steps": []}

    if args.include_migration:
        summary = migrate(args.db_path, args.database_url, dry_run=False)
        payload = summary.to_dict()
        append_step(
            report,
            "migration",
            payload,
            bool(payload.get("postgres_available")) and not payload.get("errors"),
        )

    if not args.skip_embeddings:
        summary = build_production_embeddings(
            database_url=args.database_url,
            limit=args.limit,
            replace=args.replace_embeddings,
        )
        payload = summary.to_dict()
        append_step(
            report,
            "embeddings",
            payload,
            bool(payload.get("database_available")) and not payload.get("errors"),
        )

    if not args.skip_extraction:
        summary = extract_production_judgments(
            database_url=args.database_url,
            limit=args.limit,
            model=args.model,
        )
        payload = summary.to_dict()
        append_step(
            report,
            "extraction",
            payload,
            bool(payload.get("database_available")) and not payload.get("errors"),
        )

    if not args.skip_citations:
        summary = build_production_citation_graph(database_url=args.database_url, limit=args.limit)
        payload = summary.to_dict()
        append_step(
            report,
            "citations",
            payload,
            bool(payload.get("database_available")) and not payload.get("errors"),
        )

    if not args.skip_quality:
        payload = run_production_quality_checks(database_url=args.database_url)
        append_step(report, "quality", payload, quality_gate_passed(payload))

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
