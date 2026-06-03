from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.search.embeddings import (
    DEFAULT_STAGING_DB_PATH,
    LOCAL_HASH_EMBEDDING_MODEL,
    build_staging_judgment_embeddings,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local deterministic embeddings for the staging SQLite corpus."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_STAGING_DB_PATH))
    parser.add_argument("--dimensions", type=int, default=128)
    parser.add_argument("--model-name", default=LOCAL_HASH_EMBEDDING_MODEL)
    parser.add_argument("--chunk-size", type=int, default=450)
    parser.add_argument("--overlap", type=int, default=75)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    summary = build_staging_judgment_embeddings(
        args.db_path,
        dimensions=args.dimensions,
        model_name=args.model_name,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        limit=args.limit,
    )
    print(json.dumps(summary.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
