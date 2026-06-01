from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.retrieval.staging import SearchResult, StagingRetrievalService


@dataclass(frozen=True)
class RagResponse:
    prompt: str
    answer: str | None
    model: str | None
    model_status: str
    retrieved_results: list[SearchResult]
    error: str | None = None

    def result_dicts(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.retrieved_results]


class LocalLegalRagPipeline:
    """Retrieval-first answer generation over the local staging corpus."""

    def __init__(
        self,
        retrieval_service: StagingRetrievalService | None = None,
        settings: OllamaSettings | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or StagingRetrievalService()
        self.settings = settings or OllamaSettings()

    def answer(self, question: str, context_limit: int = 5, use_llm: bool = True) -> RagResponse:
        context, results = self.retrieval_service.retrieve_context(question, limit=context_limit)
        if not use_llm:
            return RagResponse(
                prompt=question,
                answer=None,
                model=None,
                model_status="skipped",
                retrieved_results=results,
            )

        try:
            client = OllamaChatClient(self.settings)
            selected_model = client.resolve_model()
            answer = client.chat(question, context=context, model=selected_model)
            return RagResponse(
                prompt=question,
                answer=answer,
                model=selected_model,
                model_status="ok",
                retrieved_results=results,
            )
        except Exception as exc:
            return RagResponse(
                prompt=question,
                answer=None,
                model=self.settings.model,
                model_status="error",
                retrieved_results=results,
                error=str(exc),
            )
