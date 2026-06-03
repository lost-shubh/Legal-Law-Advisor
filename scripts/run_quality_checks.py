from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.quality.production import quality_gate_passed, run_production_quality_checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run production PostgreSQL quality checks.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Exit non-zero when any WARN check also has non-zero findings.",
    )
    args = parser.parse_args()

    report = run_production_quality_checks(database_url=args.database_url)
    print(json.dumps(report, indent=2))
    if not quality_gate_passed(report):
        return 1
    if args.fail_on_warn and int(report.get("summary", {}).get("warn_failures") or 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
