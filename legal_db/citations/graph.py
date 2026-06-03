from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.citations.parser import extract_citations
from legal_db.config import settings


@dataclass(frozen=True)
class CitationGraphSummary:
    database_available: bool
    judgments: int
    citation_strings: int
    citations: int
    resolved: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "judgments": self.judgments,
            "citation_strings": self.citation_strings,
            "citations": self.citations,
            "resolved": self.resolved,
            "errors": self.errors,
        }


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def normalize_citation(value: str) -> str:
    return " ".join(value.upper().split())


def citation_context(text_value: str, start: int, end: int, radius: int = 280) -> str:
    begin = max(start - radius, 0)
    finish = min(end + radius, len(text_value))
    return " ".join(text_value[begin:finish].split())


def resolve_cited_case(pg_conn: Any, citation_text: str) -> int | None:
    row = pg_conn.execute(
        sql_text(
            """
            SELECT id FROM cases
            WHERE lower(coalesce(neutral_citation, '')) = lower(:citation)
               OR lower(coalesce(case_number, '')) = lower(:citation)
            ORDER BY id
            LIMIT 1
            """
        ),
        {"citation": citation_text},
    ).fetchone()
    return int(row[0]) if row else None


def build_production_citation_graph(
    *,
    database_url: str | None = None,
    limit: int | None = None,
) -> CitationGraphSummary:
    errors: list[str] = []
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
    except Exception as exc:
        return CitationGraphSummary(False, 0, 0, 0, 0, [str(exc)])

    query = """
        SELECT j.id AS judgment_id, j.case_id, j.clean_text
        FROM judgments j
        WHERE j.clean_text IS NOT NULL
        ORDER BY j.id
    """
    if limit is not None:
        query += " LIMIT :limit"

    judgment_count = citation_string_count = citation_count = resolved_count = 0
    with engine.begin() as pg_conn:
        rows = pg_conn.execute(
            sql_text(query),
            {"limit": max(limit or 0, 0)} if limit is not None else {},
        ).mappings().all()
        for row in rows:
            judgment_count += 1
            case_id = int(row["case_id"])
            text_value = row["clean_text"] or ""
            pg_conn.execute(sql_text("DELETE FROM citations WHERE citing_case_id = :case_id"), {"case_id": case_id})
            pg_conn.execute(sql_text("DELETE FROM case_citations WHERE case_id = :case_id"), {"case_id": case_id})
            seen: set[str] = set()
            for match in extract_citations(text_value):
                normalized = normalize_citation(match.citation)
                if normalized in seen:
                    continue
                seen.add(normalized)
                cited_case_id = resolve_cited_case(pg_conn, normalized)
                if cited_case_id:
                    resolved_count += 1
                pg_conn.execute(
                    sql_text(
                        """
                        INSERT INTO citation_strings
                        (citation_text, case_id, normalized_text, reporter)
                        VALUES (:citation_text, :case_id, :normalized_text, :reporter)
                        ON CONFLICT (citation_text) DO UPDATE SET
                          case_id = COALESCE(citation_strings.case_id, EXCLUDED.case_id),
                          normalized_text = EXCLUDED.normalized_text,
                          reporter = EXCLUDED.reporter
                        """
                    ),
                    {
                        "citation_text": match.citation,
                        "case_id": cited_case_id,
                        "normalized_text": normalized,
                        "reporter": match.reporter,
                    },
                )
                citation_string_count += 1
                pg_conn.execute(
                    sql_text(
                        """
                        INSERT INTO citations
                        (citing_case_id, cited_case_id, citation_text, citation_type,
                         context_text, confidence)
                        VALUES (:citing_case_id, :cited_case_id, :citation_text,
                                'REFERRED', :context_text, :confidence)
                        """
                    ),
                    {
                        "citing_case_id": case_id,
                        "cited_case_id": cited_case_id,
                        "citation_text": match.citation,
                        "context_text": citation_context(text_value, match.start, match.end),
                        "confidence": 0.75 if cited_case_id else 0.45,
                    },
                )
                citation_count += 1
                pg_conn.execute(
                    sql_text(
                        """
                        INSERT INTO case_citations (case_id, citation, reporter, year)
                        VALUES (:case_id, :citation, :reporter, :year)
                        ON CONFLICT (case_id, citation) DO UPDATE SET
                          reporter = EXCLUDED.reporter,
                          year = EXCLUDED.year
                        """
                    ),
                    {
                        "case_id": case_id,
                        "citation": match.citation,
                        "reporter": match.reporter,
                        "year": match.year,
                    },
                )
        pg_conn.execute(
            sql_text(
                """
                UPDATE cases c
                SET citation_count = sub.count
                FROM (
                  SELECT cited_case_id, COUNT(*) AS count
                  FROM citations
                  WHERE cited_case_id IS NOT NULL
                  GROUP BY cited_case_id
                ) sub
                WHERE c.id = sub.cited_case_id
                """
            )
        )
    return CitationGraphSummary(True, judgment_count, citation_string_count, citation_count, resolved_count, errors)
