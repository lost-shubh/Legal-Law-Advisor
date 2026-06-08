from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.case_intake.analyzer import CaseAnalysis, analyze_case_text, build_case_llm_prompt
from legal_db.case_intake.brief import CaseResearchBrief, build_case_research_brief
from legal_db.case_intake.legal_anchors import anchor_query_terms, anchor_results_for_analysis
from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.retrieval.service import LegalRetrievalService
from legal_db.retrieval.staging import SearchResult


@dataclass(frozen=True)
class CaseIntakeResponse:
    analysis: CaseAnalysis
    retrieved_results: list[SearchResult]
    llm_note: str | None
    model: str | None
    model_status: str
    error: str | None = None

    def analysis_dict(self) -> dict[str, Any]:
        return self.analysis.to_dict()

    def result_dicts(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.retrieved_results]


def build_case_retrieval_query(case_text: str, analysis: CaseAnalysis) -> str:
    query_parts = [
        *analysis.issue_tags,
        *analysis.evidence_found.keys(),
        *anchor_query_terms(analysis),
    ]
    query = " ".join(part for part in query_parts if str(part).strip())
    return query if query.strip() else case_text


def merge_case_results(anchor_results: list[SearchResult], retrieved: list[SearchResult]) -> list[SearchResult]:
    merged: list[SearchResult] = []
    seen: set[tuple[str, str | None]] = set()
    for result in [*anchor_results, *retrieved]:
        key = (result.title, result.source_url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(result)
    return merged


class CaseIntakePipeline:
    def __init__(
        self,
        retrieval_service: LegalRetrievalService | None = None,
        settings: OllamaSettings | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or LegalRetrievalService()
        self.settings = settings or OllamaSettings()

    def analyze(
        self,
        case_text: str,
        context_limit: int = 5,
        use_llm: bool = True,
    ) -> CaseIntakeResponse:
        analysis = analyze_case_text(case_text)
        anchor_results = anchor_results_for_analysis(analysis)
        retrieval_query = build_case_retrieval_query(case_text, analysis)
        context, results = self.retrieval_service.retrieve_context(
            retrieval_query,
            limit=context_limit,
        )
        results = merge_case_results(anchor_results, results)
        if anchor_results:
            anchor_context = "\n\n---\n\n".join(
                f"Source: {item.source_type} | {item.title}\nURL: {item.source_url or 'local'}\n{item.snippet}"
                for item in anchor_results
            )
            context = f"{anchor_context}\n\n---\n\n{context}" if context else anchor_context

        if not use_llm:
            return CaseIntakeResponse(
                analysis=analysis,
                retrieved_results=results,
                llm_note=None,
                model=None,
                model_status="skipped",
            )

        try:
            client = OllamaChatClient(self.settings)
            selected_model = client.resolve_model()
            llm_note = client.chat(
                build_case_llm_prompt(case_text, analysis, context),
                model=selected_model,
            )
            return CaseIntakeResponse(
                analysis=analysis,
                retrieved_results=results,
                llm_note=llm_note,
                model=selected_model,
                model_status="ok",
            )
        except Exception as exc:
            return CaseIntakeResponse(
                analysis=analysis,
                retrieved_results=results,
                llm_note=None,
                model=self.settings.model,
                model_status="error",
                error=str(exc),
            )

    def build_brief(
        self,
        case_text: str,
        context_limit: int = 6,
        max_sources: int = 8,
    ) -> CaseResearchBrief:
        response = self.analyze(
            case_text=case_text,
            context_limit=context_limit,
            use_llm=False,
        )
        return build_case_research_brief(
            response.analysis,
            response.retrieved_results,
            max_sources=max_sources,
        )
