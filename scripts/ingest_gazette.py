from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.ingest.gazette import extract_gazette_signal, upsert_gazette_notification


def read_text(args: argparse.Namespace) -> str:
    if args.text_file:
        return Path(args.text_file).read_text(encoding=args.encoding)
    if args.text:
        return args.text
    raise ValueError("Provide --text-file or --text.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse and persist an e-Gazette notification.")
    parser.add_argument("--database-url", help="Override DATABASE_URL.")
    parser.add_argument("--text-file", help="Path to OCR/plain text notification content.")
    parser.add_argument("--text", help="Inline notification text.")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--source-url", help="Official e-Gazette/source URL for this notification.")
    parser.add_argument("--source-document-id", type=int, help="Existing source_documents.id.")
    parser.add_argument(
        "--no-update-effective-dates",
        action="store_true",
        help="Store notification only; do not update statute/section effective dates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the extracted notification signal.",
    )
    args = parser.parse_args()

    text = read_text(args)
    if args.dry_run:
        signal = extract_gazette_signal(text)
        print(
            json.dumps(
                {
                    "notification_number": signal.notification_number,
                    "notification_type": signal.notification_type,
                    "act_name": signal.act_name,
                    "date_text": signal.date_text,
                    "sections_affected": signal.sections_affected,
                },
                indent=2,
            )
        )
        return 0

    summary = upsert_gazette_notification(
        text=text,
        database_url=args.database_url,
        source_url=args.source_url,
        source_document_id=args.source_document_id,
        update_effective_dates=not args.no_update_effective_dates,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0 if summary.database_available and summary.error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
