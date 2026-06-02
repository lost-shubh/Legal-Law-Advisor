from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.escr import generate_manifest_from_html_files, generate_manifest_from_urls


DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "sc_escr_manifest.local.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a judgment manifest from Supreme Court/e-SCR result pages."
    )
    parser.add_argument("--html", action="append", default=[], help="Saved e-SCR/SCR result HTML.")
    parser.add_argument("--url", action="append", default=[], help="e-SCR/SCR result URL to fetch.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--base-url",
        default="https://scr.sci.gov.in/scrsearch/",
        help="Base URL used to resolve relative PDF links in saved HTML.",
    )
    args = parser.parse_args()

    if not args.html and not args.url:
        parser.error("Provide at least one --html file or --url.")
    if args.html and args.url:
        parser.error("Use either --html files or --url values in one run, not both.")

    output_path = Path(args.output)
    if args.html:
        path = generate_manifest_from_html_files(
            args.html,
            output_path=output_path,
            base_url=args.base_url,
            limit=args.limit,
        )
    else:
        path = generate_manifest_from_urls(
            args.url,
            output_path=output_path,
            limit=args.limit,
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({"output": str(path), "judgments": len(data.get("judgments", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
