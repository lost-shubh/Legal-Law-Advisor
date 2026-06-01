from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from legal_db.config import settings


ALLOWED_OUTCOMES = {
    "ALLOWED",
    "DISMISSED",
    "PARTLY_ALLOWED",
    "CONVICTED",
    "ACQUITTED",
    "BAIL_GRANTED",
    "BAIL_REJECTED",
    "SETTLED",
    "REMANDED",
    "COMPENSATION_AWARDED",
    "UNKNOWN",
}


@dataclass(frozen=True)
class ExtractionResult:
    payload: dict[str, Any]
    model: str
    validation_errors: list[str]


def build_extraction_prompt(clean_text: str) -> str:
    clipped = clean_text[:12000]
    return f"""
Extract structured information from this Indian court judgment.
Return only valid JSON with these keys:
acts_cited, outcome, issue_tags, dispute_summary, timeline, key_evidence,
allegations, defence, key_arguments, reasoning, compensation_awarded.

Use null when a field is unavailable. Do not guess values not supported by text.

JUDGMENT TEXT:
{clipped}
""".strip()


def validate_payload(payload: dict[str, Any], source_text: str) -> list[str]:
    errors: list[str] = []
    outcome = payload.get("outcome")
    if outcome and outcome not in ALLOWED_OUTCOMES:
        errors.append(f"Unsupported outcome: {outcome}")
    amount = payload.get("compensation_awarded")
    if amount not in (None, "") and str(amount).replace(",", "") not in source_text.replace(",", ""):
        errors.append("Compensation amount does not appear literally in source text")
    if not isinstance(payload.get("issue_tags", []), list):
        errors.append("issue_tags must be a list")
    if not isinstance(payload.get("acts_cited", []), list):
        errors.append("acts_cited must be a list")
    return errors


def extract_with_openai(clean_text: str, model: str | None = None) -> ExtractionResult:
    from openai import OpenAI

    selected_model = model or settings.openai_extraction_model
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=selected_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a legal data extraction assistant for Indian courts. "
                    "Return only valid JSON."
                ),
            },
            {"role": "user", "content": build_extraction_prompt(clean_text)},
        ],
    )
    raw = response.output_text
    payload = json.loads(raw)
    return ExtractionResult(
        payload=payload,
        model=selected_model,
        validation_errors=validate_payload(payload, clean_text),
    )

