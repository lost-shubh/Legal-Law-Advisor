from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GazetteSignal:
    notification_number: str | None
    notification_type: str
    act_name: str | None
    date_text: str | None
    sections_affected: list[str]


NOTIFICATION_RE = re.compile(r"\b(?:S\.O\.|G\.S\.R\.)\s*\d+\s*\(E\)", re.IGNORECASE)
SECTION_RE = re.compile(r"\bsection[s]?\s+([0-9A-Za-z(),\s.-]+)", re.IGNORECASE)


def classify_notification(text: str) -> str:
    lowered = text.lower()
    if "come into force" in lowered or "shall come into force" in lowered:
        return "COMMENCEMENT"
    if "amend" in lowered or "substituted" in lowered or "inserted" in lowered:
        return "AMENDMENT"
    if "repeal" in lowered:
        return "REPEAL"
    if "rules" in lowered:
        return "RULES"
    return "OTHER"


def extract_gazette_signal(text: str) -> GazetteSignal:
    notification_match = NOTIFICATION_RE.search(text)
    sections: list[str] = []
    for match in SECTION_RE.findall(text[:5000]):
        sections.extend([part.strip() for part in re.split(r",|and", match) if part.strip()])
    act_match = re.search(r"The\s+([A-Z][A-Za-z\s(),.-]+Act,\s*\d{4})", text)
    date_match = re.search(r"\b\d{1,2}(?:st|nd|rd|th)?\s+day\s+of\s+[A-Za-z]+,\s+\d{4}\b", text)
    return GazetteSignal(
        notification_number=notification_match.group(0) if notification_match else None,
        notification_type=classify_notification(text),
        act_name=act_match.group(0) if act_match else None,
        date_text=date_match.group(0) if date_match else None,
        sections_affected=sections,
    )

