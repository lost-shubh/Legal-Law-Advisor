from __future__ import annotations

import argparse
import json
from pathlib import Path

from legal_db.citations.parser import extract_citations
from legal_db.evaluation.retrieval import RetrievalCase, evaluate_retrieval
from legal_db.logging_config import configure_logging
from legal_db.pdf.ocr import extract_pdf_text
from legal_db.quality.checks import quality_sql
from legal_db.retrieval.service import LegalRetrievalService


def cmd_quality_sql(_: argparse.Namespace) -> int:
    print(quality_sql())
    return 0


def cmd_parse_citations(args: argparse.Namespace) -> int:
    text = Path(args.path).read_text(encoding="utf-8")
    matches = [match.__dict__ for match in extract_citations(text)]
    print(json.dumps(matches, indent=2))
    return 0


def cmd_extract_pdf(args: argparse.Namespace) -> int:
    result = extract_pdf_text(Path(args.path), lang=args.lang)
    print(
        json.dumps(
            {
                "pdf_type": result.pdf_type,
                "page_count": result.page_count,
                "word_count": result.word_count,
                "extraction_method": result.extraction_method,
                "ocr_confidence": result.ocr_confidence,
                "page_spans": list(result.page_spans),
                "preview": result.clean_text[:1000],
            },
            indent=2,
        )
    )
    return 0


def cmd_evaluate_retrieval(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    cases = [RetrievalCase.from_dict(item) for item in payload.get("cases", [])]
    service = LegalRetrievalService()

    def search(query: str, limit: int, mode: str):
        return service.search(query, limit=limit, mode=mode)

    metrics = evaluate_retrieval(cases, search, k=payload.get("k", args.k))
    print(json.dumps(metrics.to_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="legal-db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    quality = subparsers.add_parser("quality-sql", help="Print SQL quality checks")
    quality.set_defaults(func=cmd_quality_sql)

    citations = subparsers.add_parser("parse-citations", help="Extract citations from a text file")
    citations.add_argument("path")
    citations.set_defaults(func=cmd_parse_citations)

    pdf = subparsers.add_parser("extract-pdf", help="Extract/OCR text from a PDF")
    pdf.add_argument("path")
    pdf.add_argument("--lang", default="eng+hin")
    pdf.set_defaults(func=cmd_extract_pdf)

    evaluation = subparsers.add_parser(
        "evaluate-retrieval", help="Evaluate retrieval against labelled query cases"
    )
    evaluation.add_argument("path", help="JSON evaluation case file")
    evaluation.add_argument("--k", type=int, default=10)
    evaluation.set_defaults(func=cmd_evaluate_retrieval)

    return parser


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

