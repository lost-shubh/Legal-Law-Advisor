from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legal_db.llm.ollama import OllamaChatClient


def main() -> int:
    status = OllamaChatClient().status().to_dict()
    print(json.dumps(status, indent=2))
    if not status["available"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
