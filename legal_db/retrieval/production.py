from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.config import settings
from legal_db.retrieval.staging import SearchResult, SimilarCaseResult, make_snippet, tokenize
from legal_db.search.embeddings import (
    LOCAL_HASH_EMBEDDING_MODEL,
    local_hash_embedding,
    vector_literal,
)


PRODUCTION_EMBEDDING_DIMENSIONS = 1536


def text(statement: str) -> Any:
    from sqlalchemy import text as sqlalchemy_text

    return sqlalchemy_text(statement)


def normalize_source_types(source_types: list[str] | None) -> set[str]:
    requested = {item.upper() for item in (source_types or ["SECTION", "BOOK_CHUNK", "JUDGMENT"])}
    normalized: set[str] = set()
    if "SECTION" in requested:
        normalized.add("SECTION")
    if "BOOK_CHUNK" in requested:
        normalized.add("BOOK_CHUNK")
    if "JUDGMENT" in requested or "JUDGMENT_CHUNK" in requested:
        normalized.add("JUDGMENT_CHUNK")
    return normalized


@dataclass(frozen=True)
class ProductionSearchRow:
    source_type: str
    source_id: int
    chunk_index: int
    title: str
    snippet_text: str
    score: float
    source_url: str | None
    metadata: dict[str, Any]

    def to_result(self, query_terms: set[str], result_type: str | None = None) -> SearchResult:
        return SearchResult(
            source_type=result_type or self.source_type,
            title=self.title,
            snippet=make_snippet(self.snippet_text or "", query_terms),
            score=round(float(self.score), 6),
            source_url=self.source_url,
            metadata=self.metadata,
        )


class ProductionRetrievalService:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or settings.database_url
        self._engine: Any | None = None

    @property
    def engine(self) -> Any:
        if self._engine is None:
            from legal_db.db import make_engine

            self._engine = make_engine(self.database_url)
        return self._engine

    def is_available(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def has_corpus(self) -> bool:
        try:
            with self.engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                          (SELECT COUNT(*) FROM sections) AS sections,
                          (SELECT COUNT(*) FROM judgments) AS judgments,
                          (SELECT COUNT(*) FROM book_chunks) AS book_chunks
                        """
                    )
                ).mappings().one()
            return any(int(row[key] or 0) > 0 for key in ["sections", "judgments", "book_chunks"])
        except Exception:
            return False

    def progress(self) -> dict[str, Any]:
        try:
            with self.engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                          (SELECT COUNT(*) FROM statutes) AS statutes,
                          (SELECT COUNT(*) FROM sections) AS sections,
                          (SELECT COUNT(*) FROM legal_books) AS legal_books,
                          (SELECT COUNT(*) FROM book_chunks) AS book_chunks,
                          (SELECT COUNT(*) FROM cases) AS cases,
                          (SELECT COUNT(*) FROM judgments) AS current_judgments,
                          (SELECT COUNT(*) FROM embeddings) AS embeddings,
                          (SELECT COUNT(*) FROM embeddings WHERE source_type = 'SECTION') AS section_embeddings,
                          (SELECT COUNT(*) FROM embeddings WHERE source_type = 'JUDGMENT_CHUNK') AS judgment_embeddings,
                          (SELECT COUNT(*) FROM embeddings WHERE source_type = 'BOOK_CHUNK') AS book_embeddings
                        """
                    )
                ).mappings().one()
        except Exception as exc:
            return {
                "database_available": False,
                "database": "postgresql",
                "error": str(exc),
                "current_judgments": 0,
            }
        target_judgments = 10000
        current_judgments = int(row["current_judgments"] or 0)
        return {
            "database_available": True,
            "database": "postgresql",
            "target_judgments": target_judgments,
            "current_judgments": current_judgments,
            "remaining_judgments": max(target_judgments - current_judgments, 0),
            "judgment_progress_percent": round((current_judgments / target_judgments) * 100, 3),
            "statutes": int(row["statutes"] or 0),
            "sections": int(row["sections"] or 0),
            "legal_books": int(row["legal_books"] or 0),
            "book_chunks": int(row["book_chunks"] or 0),
            "cases": int(row["cases"] or 0),
            "embeddings": int(row["embeddings"] or 0),
            "section_embeddings": int(row["section_embeddings"] or 0),
            "judgment_embeddings": int(row["judgment_embeddings"] or 0),
            "book_embeddings": int(row["book_embeddings"] or 0),
        }

    def search(
        self,
        query: str,
        limit: int = 10,
        source_types: list[str] | None = None,
        mode: str = "lexical",
    ) -> list[SearchResult]:
        normalized_mode = mode.lower().strip()
        bounded_limit = max(min(limit, 50), 1)
        if normalized_mode == "semantic":
            results = self.semantic_search(query, limit=bounded_limit, source_types=source_types)
            return results or self.lexical_search(query, limit=bounded_limit, source_types=source_types)
        if normalized_mode == "hybrid":
            semantic = self.semantic_search(query, limit=bounded_limit * 2, source_types=source_types)
            lexical = self.lexical_search(query, limit=bounded_limit * 2, source_types=source_types)
            return self._merge_ranked_results(semantic + lexical, bounded_limit)
        return self.lexical_search(query, limit=bounded_limit, source_types=source_types)

    def retrieve_context(self, query: str, limit: int = 5) -> tuple[str, list[SearchResult]]:
        results = self.search(query, limit=limit, mode="hybrid")
        parts = [
            f"Source: {item.source_type} | {item.title}\nURL: {item.source_url or 'local'}\n{item.snippet}"
            for item in results
        ]
        return "\n\n---\n\n".join(parts), results

    def lexical_search(
        self,
        query: str,
        limit: int = 10,
        source_types: list[str] | None = None,
    ) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query.strip() or not query_terms:
            return []
        allowed = normalize_source_types(source_types)
        rows: list[ProductionSearchRow] = []
        with self.engine.connect() as conn:
            if "SECTION" in allowed:
                rows.extend(self._lexical_sections(conn, query, limit * 2))
            if "JUDGMENT_CHUNK" in allowed:
                rows.extend(self._lexical_judgments(conn, query, limit * 2))
            if "BOOK_CHUNK" in allowed:
                rows.extend(self._lexical_book_chunks(conn, query, limit * 2))
        results = [row.to_result(query_terms) for row in rows if row.score > 0]
        results.sort(key=lambda item: item.score, reverse=True)
        return results[: max(min(limit, 50), 1)]

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        source_types: list[str] | None = None,
        model_name: str = LOCAL_HASH_EMBEDDING_MODEL,
    ) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query.strip() or not query_terms:
            return []
        allowed = normalize_source_types(source_types)
        query_vector = vector_literal(local_hash_embedding(query, dimensions=PRODUCTION_EMBEDDING_DIMENSIONS))
        rows: list[ProductionSearchRow] = []
        with self.engine.connect() as conn:
            if "SECTION" in allowed:
                rows.extend(self._semantic_sections(conn, query_vector, model_name, limit * 2))
            if "JUDGMENT_CHUNK" in allowed:
                rows.extend(self._semantic_judgments(conn, query_vector, model_name, limit * 2))
            if "BOOK_CHUNK" in allowed:
                rows.extend(self._semantic_book_chunks(conn, query_vector, model_name, limit * 2))
        results = [
            row.to_result(query_terms, result_type=f"{row.source_type}_SEMANTIC")
            for row in rows
            if row.score > 0.02
        ]
        results.sort(key=lambda item: item.score, reverse=True)
        return results[: max(min(limit, 50), 1)]

    def similar_cases(self, case_text: str, limit: int = 10) -> list[SimilarCaseResult]:
        terms = tokenize(case_text)
        if not case_text.strip() or not terms:
            return []
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    WITH q AS (SELECT plainto_tsquery('english', :query) AS query)
                    SELECT
                      j.id AS judgment_id,
                      c.case_number,
                      c.neutral_citation,
                      c.decision_date,
                      c.source_url AS case_source_url,
                      j.pdf_url,
                      j.clean_text,
                      COALESCE(
                        NULLIF(CONCAT_WS(' v. ', c.petitioner, c.respondent), ''),
                        c.case_number,
                        c.neutral_citation,
                        'Court Judgment'
                      ) AS title,
                      ts_rank(
                        to_tsvector('english', coalesce(j.clean_text, '')),
                        q.query
                      ) AS score
                    FROM judgments j
                    JOIN cases c ON c.id = j.case_id
                    CROSS JOIN q
                    WHERE j.clean_text IS NOT NULL
                      AND to_tsvector('english', coalesce(j.clean_text, '')) @@ q.query
                    ORDER BY score DESC, j.judgment_date DESC NULLS LAST
                    LIMIT :limit
                    """
                ),
                {"query": case_text, "limit": max(min(limit, 50), 1)},
            ).mappings().all()
        return [
            SimilarCaseResult(
                case_title=row["title"],
                case_number=row["case_number"] or row["neutral_citation"],
                decision_date=str(row["decision_date"]) if row["decision_date"] else None,
                source_url=row["case_source_url"],
                pdf_url=row["pdf_url"],
                score=round(float(row["score"] or 0), 6),
                snippet=make_snippet(row["clean_text"] or "", terms),
                metadata={"judgment_id": row["judgment_id"], "database": "postgresql"},
            )
            for row in rows
        ]

    def _merge_ranked_results(self, results: list[SearchResult], limit: int) -> list[SearchResult]:
        merged: dict[tuple[str, str | None], SearchResult] = {}
        for result in results:
            key = (result.title, result.source_url)
            current = merged.get(key)
            if current is None or result.score > current.score:
                merged[key] = result
        ranked = list(merged.values())
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def _lexical_sections(self, conn: Any, query: str, limit: int) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="SECTION",
                source_id=int(row["source_id"]),
                chunk_index=0,
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={"section_number": row["section_number"], "act_name": row["act_name"]},
            )
            for row in conn.execute(
                text(
                    """
                    WITH q AS (SELECT plainto_tsquery('english', :query) AS query)
                    SELECT
                      s.id AS source_id,
                      s.section_number,
                      st.act_name,
                      st.source_url,
                      CONCAT(COALESCE(st.short_title, st.act_name), ' Section ', s.section_number,
                             CASE WHEN s.section_title IS NULL THEN '' ELSE CONCAT(': ', s.section_title) END) AS title,
                      s.section_text AS snippet_text,
                      ts_rank(
                        to_tsvector('english', coalesce(s.section_number, '') || ' ' ||
                                               coalesce(s.section_title, '') || ' ' ||
                                               coalesce(s.section_text, '')),
                        q.query
                      ) AS score
                    FROM sections s
                    JOIN statutes st ON st.id = s.statute_id
                    CROSS JOIN q
                    WHERE to_tsvector('english', coalesce(s.section_number, '') || ' ' ||
                                             coalesce(s.section_title, '') || ' ' ||
                                             coalesce(s.section_text, '')) @@ q.query
                    ORDER BY score DESC, s.id
                    LIMIT :limit
                    """
                ),
                {"query": query, "limit": max(limit, 1)},
            ).mappings()
        ]

    def _lexical_judgments(self, conn: Any, query: str, limit: int) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="JUDGMENT",
                source_id=int(row["source_id"]),
                chunk_index=0,
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={
                    "case_number": row["case_number"],
                    "decision_date": str(row["decision_date"]) if row["decision_date"] else None,
                },
            )
            for row in conn.execute(
                text(
                    """
                    WITH q AS (SELECT plainto_tsquery('english', :query) AS query)
                    SELECT
                      j.id AS source_id,
                      c.case_number,
                      c.decision_date,
                      j.pdf_url AS source_url,
                      COALESCE(
                        NULLIF(CONCAT_WS(' v. ', c.petitioner, c.respondent), ''),
                        c.case_number,
                        c.neutral_citation,
                        'Court Judgment'
                      ) AS title,
                      j.clean_text AS snippet_text,
                      ts_rank(to_tsvector('english', coalesce(j.clean_text, '')), q.query) AS score
                    FROM judgments j
                    JOIN cases c ON c.id = j.case_id
                    CROSS JOIN q
                    WHERE j.clean_text IS NOT NULL
                      AND to_tsvector('english', coalesce(j.clean_text, '')) @@ q.query
                    ORDER BY score DESC, j.judgment_date DESC NULLS LAST
                    LIMIT :limit
                    """
                ),
                {"query": query, "limit": max(limit, 1)},
            ).mappings()
        ]

    def _lexical_book_chunks(self, conn: Any, query: str, limit: int) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="BOOK_CHUNK",
                source_id=int(row["source_id"]),
                chunk_index=0,
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={"chapter_title": row["chapter_title"]},
            )
            for row in conn.execute(
                text(
                    """
                    WITH q AS (SELECT plainto_tsquery('english', :query) AS query)
                    SELECT
                      bc.id AS source_id,
                      b.source_url,
                      ch.chapter_title,
                      CONCAT(b.title, ' / ', COALESCE(ch.chapter_title, 'Full document')) AS title,
                      bc.chunk_text AS snippet_text,
                      ts_rank(to_tsvector('english', coalesce(bc.chunk_text, '')), q.query) AS score
                    FROM book_chunks bc
                    JOIN legal_books b ON b.id = bc.book_id
                    LEFT JOIN book_chapters ch ON ch.id = bc.chapter_id
                    CROSS JOIN q
                    WHERE to_tsvector('english', coalesce(bc.chunk_text, '')) @@ q.query
                    ORDER BY score DESC, bc.id
                    LIMIT :limit
                    """
                ),
                {"query": query, "limit": max(limit, 1)},
            ).mappings()
        ]

    def _semantic_sections(
        self, conn: Any, query_vector: str, model_name: str, limit: int
    ) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="SECTION",
                source_id=int(row["source_id"]),
                chunk_index=int(row["chunk_index"] or 0),
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={
                    "section_number": row["section_number"],
                    "act_name": row["act_name"],
                    "model_name": row["model_name"],
                },
            )
            for row in conn.execute(
                text(
                    """
                    SELECT
                      e.source_id,
                      e.chunk_index,
                      e.chunk_text AS snippet_text,
                      e.model_name,
                      s.section_number,
                      st.act_name,
                      st.source_url,
                      CONCAT(COALESCE(st.short_title, st.act_name), ' Section ', s.section_number,
                             CASE WHEN s.section_title IS NULL THEN '' ELSE CONCAT(': ', s.section_title) END) AS title,
                      1 - (e.embedding <=> CAST(:query_vector AS vector)) AS score
                    FROM embeddings e
                    JOIN sections s ON s.id = e.source_id
                    JOIN statutes st ON st.id = s.statute_id
                    WHERE e.source_type = 'SECTION'
                      AND e.model_name = :model_name
                    ORDER BY e.embedding <=> CAST(:query_vector AS vector)
                    LIMIT :limit
                    """
                ),
                {"query_vector": query_vector, "model_name": model_name, "limit": max(limit, 1)},
            ).mappings()
        ]

    def _semantic_judgments(
        self, conn: Any, query_vector: str, model_name: str, limit: int
    ) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="JUDGMENT",
                source_id=int(row["source_id"]),
                chunk_index=int(row["chunk_index"] or 0),
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={
                    "case_number": row["case_number"],
                    "decision_date": str(row["decision_date"]) if row["decision_date"] else None,
                    "chunk_index": row["chunk_index"],
                    "model_name": row["model_name"],
                },
            )
            for row in conn.execute(
                text(
                    """
                    SELECT
                      e.source_id,
                      e.chunk_index,
                      e.chunk_text AS snippet_text,
                      e.model_name,
                      c.case_number,
                      c.decision_date,
                      j.pdf_url AS source_url,
                      COALESCE(
                        NULLIF(CONCAT_WS(' v. ', c.petitioner, c.respondent), ''),
                        c.case_number,
                        c.neutral_citation,
                        'Court Judgment'
                      ) AS title,
                      1 - (e.embedding <=> CAST(:query_vector AS vector)) AS score
                    FROM embeddings e
                    JOIN judgments j ON j.id = e.source_id
                    JOIN cases c ON c.id = j.case_id
                    WHERE e.source_type = 'JUDGMENT_CHUNK'
                      AND e.model_name = :model_name
                    ORDER BY e.embedding <=> CAST(:query_vector AS vector)
                    LIMIT :limit
                    """
                ),
                {"query_vector": query_vector, "model_name": model_name, "limit": max(limit, 1)},
            ).mappings()
        ]

    def _semantic_book_chunks(
        self, conn: Any, query_vector: str, model_name: str, limit: int
    ) -> list[ProductionSearchRow]:
        return [
            ProductionSearchRow(
                source_type="BOOK_CHUNK",
                source_id=int(row["source_id"]),
                chunk_index=int(row["chunk_index"] or 0),
                title=row["title"],
                snippet_text=row["snippet_text"] or "",
                score=float(row["score"] or 0),
                source_url=row["source_url"],
                metadata={"chapter_title": row["chapter_title"], "model_name": row["model_name"]},
            )
            for row in conn.execute(
                text(
                    """
                    SELECT
                      e.source_id,
                      e.chunk_index,
                      e.chunk_text AS snippet_text,
                      e.model_name,
                      b.source_url,
                      ch.chapter_title,
                      CONCAT(b.title, ' / ', COALESCE(ch.chapter_title, 'Full document')) AS title,
                      1 - (e.embedding <=> CAST(:query_vector AS vector)) AS score
                    FROM embeddings e
                    JOIN book_chunks bc ON bc.id = e.source_id
                    JOIN legal_books b ON b.id = bc.book_id
                    LEFT JOIN book_chapters ch ON ch.id = bc.chapter_id
                    WHERE e.source_type = 'BOOK_CHUNK'
                      AND e.model_name = :model_name
                    ORDER BY e.embedding <=> CAST(:query_vector AS vector)
                    LIMIT :limit
                    """
                ),
                {"query_vector": query_vector, "model_name": model_name, "limit": max(limit, 1)},
            ).mappings()
        ]
