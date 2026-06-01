from __future__ import annotations

from legal_db.case_intake.pipeline import CaseIntakePipeline
from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.llm.rag import LocalLegalRagPipeline
from legal_db.retrieval.staging import StagingRetrievalService

from .schemas import (
    CaseAnalyzeRequest,
    CaseAnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ModelStatusResponse,
    SearchRequest,
    SearchResponse,
)


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

    @app.get("/v1/models/ollama", response_model=ModelStatusResponse)
    def ollama_status_route() -> ModelStatusResponse:
        status = OllamaChatClient(OllamaSettings()).status()
        return ModelStatusResponse(**status.to_dict())

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
        response = LocalLegalRagPipeline(retrieval_service=retrieval_service).answer(
            request.question,
            context_limit=request.context_limit,
            use_llm=request.use_llm,
        )
        return ChatResponse(
            question=request.question,
            answer=response.answer,
            model=response.model,
            model_status=response.model_status,
            retrieved_results=response.result_dicts(),
            error=response.error,
        )

    @app.post("/v1/cases/analyze", response_model=CaseAnalyzeResponse)
    def analyze_case_route(request: CaseAnalyzeRequest) -> CaseAnalyzeResponse:
        response = CaseIntakePipeline(retrieval_service=retrieval_service).analyze(
            request.case_text,
            context_limit=request.context_limit,
            use_llm=request.use_llm,
        )
        return CaseAnalyzeResponse(
            analysis=response.analysis_dict(),
            retrieved_results=response.result_dicts(),
            llm_note=response.llm_note,
            model=response.model,
            model_status=response.model_status,
            error=response.error,
        )

except ImportError:
    # FastAPI is an app runtime dependency. The pure function above keeps the
    # skeleton importable in the current data-pipeline environment.
    app = None
