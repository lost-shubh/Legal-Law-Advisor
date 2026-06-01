from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityCheck:
    name: str
    sql: str
    severity: str = "WARN"


QUALITY_CHECKS: list[QualityCheck] = [
    QualityCheck(
        "judgments_without_text",
        "SELECT COUNT(*) AS count FROM judgments WHERE clean_text IS NULL",
    ),
    QualityCheck(
        "cases_with_impossible_dates",
        "SELECT COUNT(*) AS count FROM cases WHERE decision_date < filing_date",
        "ERROR",
    ),
    QualityCheck(
        "decided_cases_without_outcome",
        """
        SELECT COUNT(*) AS count
        FROM cases c
        LEFT JOIN outcomes o ON c.id = o.case_id
        WHERE c.status IN ('DECIDED', 'DISPOSED') AND o.id IS NULL
        """,
    ),
    QualityCheck(
        "duplicate_pdf_hashes",
        """
        SELECT COUNT(*) AS count
        FROM (
          SELECT pdf_hash FROM judgments
          WHERE pdf_hash IS NOT NULL
          GROUP BY pdf_hash HAVING COUNT(*) > 1
        ) d
        """,
        "ERROR",
    ),
    QualityCheck(
        "embeddings_wrong_dimension",
        "SELECT COUNT(*) AS count FROM embeddings WHERE vector_dims(embedding) != 1536",
        "ERROR",
    ),
    QualityCheck(
        "unvalidated_ai_facts",
        "SELECT COUNT(*) AS count FROM case_facts WHERE validation_status = 'UNVALIDATED'",
    ),
]


def quality_sql() -> str:
    parts = []
    for check in QUALITY_CHECKS:
        parts.append(f"-- {check.severity}: {check.name}\n{check.sql.strip()};")
    return "\n\n".join(parts)

