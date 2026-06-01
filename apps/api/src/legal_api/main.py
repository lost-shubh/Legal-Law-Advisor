from __future__ import annotations

from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.retrieval.staging import StagingRetrievalService

from .schemas import ChatRequest, ChatResponse, SearchRequest, SearchResponse


retrieval_service = StagingRetrievalService()


def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "legal-api",
        "staging_database": "available" if retrieval_service.is_available() else "missing",
    }


try:
    from fastapi import FastAPI

    app = FastAPI(title="Legal Law Advisor API", version="0.1.0")

    @app.get("/health")
    def health_route() -> dict[str, str]:
        return health()

    @app.get("/v1/corpus/progress")
    def corpus_progress_route() -> dict:
        return retrieval_service.progress()

    @app.post("/v1/search", response_model=SearchResponse)
    def search_route(request: SearchRequest) -> SearchResponse:
        results = retrieval_service.search(
            request.query,
            limit=request.limit,
            source_types=request.source_types,
        )
        return SearchResponse(query=request.query, results=[item.to_dict() for item in results])

    @app.post("/v1/chat", response_model=ChatResponse)
    def chat_route(request: ChatRequest) -> ChatResponse:
        context, results = retrieval_service.retrieve_context(
            request.question,
            limit=request.context_limit,
        )
        result_dicts = [item.to_dict() for item in results]
        if not request.use_llm:
            return ChatResponse(
                question=request.question,
                answer=None,
                model=None,
                model_status="skipped",
                retrieved_results=result_dicts,
            )
        settings = OllamaSettings()
        try:
            answer = OllamaChatClient(settings).chat(request.question, context=context)
            return ChatResponse(
                question=request.question,
                answer=answer,
                model=settings.model,
                model_status="ok",
                retrieved_results=result_dicts,
            )
        except Exception as exc:
            return ChatResponse(
                question=request.question,
                answer=None,
                model=settings.model,
                model_status="error",
                retrieved_results=result_dicts,
                error=str(exc),
            )

except ImportError:
    # FastAPI is an app runtime dependency. The pure function above keeps the
    # skeleton importable in the current data-pipeline environment.
    app = None
