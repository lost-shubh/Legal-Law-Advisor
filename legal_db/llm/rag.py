from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.retrieval.service import LegalRetrievalService
from legal_db.retrieval.staging import SearchResult


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


@dataclass(frozen=True)
class ChatReadiness:
    ready: bool
    model: dict[str, Any]
    corpus: dict[str, Any]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "model": self.model,
            "corpus": self.corpus,
            "reason": self.reason,
        }


class LocalLegalRagPipeline:
    """Retrieval-first answer generation over the legal corpus."""

    def __init__(
        self,
        retrieval_service: LegalRetrievalService | None = None,
        settings: OllamaSettings | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service or LegalRetrievalService()
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

    def readiness(self) -> ChatReadiness:
        model_status = OllamaChatClient(self.settings).status().to_dict()
        corpus = self.retrieval_service.progress()
        database_available = bool(corpus.get("database_available"))
        searchable_count = sum(
            int(corpus.get(key, 0) or 0)
            for key in ["sections", "book_chunks", "current_judgments"]
        )
        if not model_status["available"]:
            return ChatReadiness(
                ready=False,
                model=model_status,
                corpus=corpus,
                reason="No configured Ollama model is available.",
            )
        if not database_available:
            return ChatReadiness(
                ready=False,
                model=model_status,
                corpus=corpus,
                reason="The legal corpus database is not available.",
            )
        if searchable_count <= 0:
            return ChatReadiness(
                ready=False,
                model=model_status,
                corpus=corpus,
                reason="The legal corpus has no searchable sections, books or judgments.",
            )
        return ChatReadiness(
            ready=True,
            model=model_status,
            corpus=corpus,
            reason=None,
        )
