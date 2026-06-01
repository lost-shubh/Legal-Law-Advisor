from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CitationMatch:
    citation: str
    reporter: str
    year: int | None
    start: int
    end: int


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("INSC", re.compile(r"\b(20\d{2})\s+INSC\s+\d+\b", re.IGNORECASE)),
    ("SCC", re.compile(r"\(\s*(\d{4})\s*\)\s*\d+\s+SCC\s+\d+\b", re.IGNORECASE)),
    ("AIR_SC", re.compile(r"\bAIR\s+(\d{4})\s+SC\s+\d+\b", re.IGNORECASE)),
    ("SCR", re.compile(r"\b(\d{4})\s+SCR\s+\(?\d+\)?\s+\d+\b", re.IGNORECASE)),
    ("CRILJ", re.compile(r"\b(\d{4})\s+CriLJ\s+\d+\b", re.IGNORECASE)),
]


def extract_citations(text: str) -> list[CitationMatch]:
    matches: list[CitationMatch] = []
    for reporter, pattern in PATTERNS:
        for match in pattern.finditer(text):
            year = int(match.group(1)) if match.groups() else None
            matches.append(
                CitationMatch(
                    citation=match.group(0),
                    reporter=reporter,
                    year=year,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return sorted(matches, key=lambda item: item.start)

