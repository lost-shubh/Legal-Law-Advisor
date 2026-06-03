from __future__ import annotations

from pathlib import Path
from typing import Any

from legal_db.retrieval.production import ProductionRetrievalService
from legal_db.retrieval.staging import (
    DEFAULT_DB_PATH,
    SearchResult,
    SimilarCaseResult,
    StagingRetrievalService,
)


class LegalRetrievalService:
    def __init__(
        self,
        *,
        database_url: str | None = None,
        staging_db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.production = ProductionRetrievalService(database_url=database_url)
        self.staging = StagingRetrievalService(staging_db_path)

    def use_production(self) -> bool:
        return self.production.has_corpus()

    def is_available(self) -> bool:
        return self.use_production() or self.staging.is_available()

    def progress(self) -> dict[str, Any]:
        if self.use_production():
            return self.production.progress()
        return self.staging.progress()

    def search(
        self,
        query: str,
        limit: int = 10,
        source_types: list[str] | None = None,
        mode: str = "lexical",
    ) -> list[SearchResult]:
        if self.use_production():
            try:
                return self.production.search(
                    query,
                    limit=limit,
                    source_types=source_types,
                    mode=mode,
                )
            except Exception:
                return self.staging.search(
                    query,
                    limit=limit,
                    source_types=source_types,
                    mode=mode,
                )
        return self.staging.search(query, limit=limit, source_types=source_types, mode=mode)

    def retrieve_context(self, query: str, limit: int = 5) -> tuple[str, list[SearchResult]]:
        if self.use_production():
            try:
                return self.production.retrieve_context(query, limit=limit)
            except Exception:
                return self.staging.retrieve_context(query, limit=limit)
        return self.staging.retrieve_context(query, limit=limit)

    def similar_cases(self, case_text: str, limit: int = 10) -> list[SimilarCaseResult]:
        if self.use_production():
            try:
                return self.production.similar_cases(case_text, limit=limit)
            except Exception:
                return self.staging.similar_cases(case_text, limit=limit)
        return self.staging.similar_cases(case_text, limit=limit)
