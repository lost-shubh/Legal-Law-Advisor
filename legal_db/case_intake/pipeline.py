from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.case_intake.analyzer import CaseAnalysis, analyze_case_text, build_case_llm_prompt
from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.retrieval.staging import SearchResult, StagingRetrievalService


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


class CaseIntakePipeline:
    def __init__(
        self,
        retrieval_service: StagingRetrievalService | None = None,
        settings: OllamaSettings | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or StagingRetrievalService()
        self.settings = settings or OllamaSettings()

    def analyze(
        self,
        case_text: str,
        context_limit: int = 5,
        use_llm: bool = True,
    ) -> CaseIntakeResponse:
        analysis = analyze_case_text(case_text)
        retrieval_query = " ".join(analysis.issue_tags + list(analysis.evidence_found.keys()))
        context, results = self.retrieval_service.retrieve_context(
            retrieval_query if retrieval_query.strip() else case_text,
            limit=context_limit,
        )

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
