from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.judgment_collectors import COLLECTORS, generate_manifest_from_html_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a standard judgment manifest from saved DOJ/High Court result HTML."
    )
    parser.add_argument(
        "--collector",
        required=True,
        choices=sorted(COLLECTORS),
        help="Collector parser to use.",
    )
    parser.add_argument("--html", action="append", required=True, help="Saved result HTML file.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    path = generate_manifest_from_html_files(
        args.html,
        collector=args.collector,
        output_path=args.output,
        limit=args.limit,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({"output": str(path), "judgments": len(data.get("judgments", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
