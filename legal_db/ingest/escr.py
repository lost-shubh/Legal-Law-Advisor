from __future__ import annotations

import re
from dataclasses import dataclass


NEUTRAL_CITATION_RE = re.compile(r"\b(20\d{2})\s+INSC\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SupremeCourtCitation:
    citation: str
    year: int
    number: int


def extract_neutral_citations(text: str) -> list[SupremeCourtCitation]:
    citations: list[SupremeCourtCitation] = []
    for year, number in NEUTRAL_CITATION_RE.findall(text):
        citations.append(
            SupremeCourtCitation(
                citation=f"{year} INSC {int(number)}",
                year=int(year),
                number=int(number),
            )
        )
    return citations

