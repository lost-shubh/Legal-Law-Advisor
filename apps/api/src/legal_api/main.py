from __future__ import annotations

from legal_db.case_intake.pipeline import CaseIntakePipeline
from legal_db.ai.extract import (
    LOCAL_EXTRACTION_MODEL,
    PROMPT_VERSION,
    extract_staging_judgments,
    staging_extraction_status,
)
from legal_db.config import settings as legal_settings
from legal_db.ingest.jobs import IngestionJobTracker
from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.llm.rag import LocalLegalRagPipeline
from legal_db.retrieval.staging import StagingRetrievalService

from .schemas import (
    AdminOverviewResponse,
    CaseAnalyzeRequest,
    CaseAnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
    ExtractionModelStatusResponse,
    ExtractionRunRequest,
    ExtractionRunResponse,
    ExtractionStatusResponse,
    IngestionStatusResponse,
    ModelStatusResponse,
    SearchRequest,
    SearchResponse,
    SimilarCasesRequest,
    SimilarCasesResponse,
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

    @app.get("/v1/admin/overview", response_model=AdminOverviewResponse)
    def admin_overview_route() -> AdminOverviewResponse:
        ollama_status = OllamaChatClient(OllamaSettings()).status().to_dict()
        extraction_model = {
            "local_model": LOCAL_EXTRACTION_MODEL,
            "local_available": True,
            "hosted_model": legal_settings.openai_extraction_model,
            "hosted_configured": bool(legal_settings.openai_api_key),
            "prompt_version": PROMPT_VERSION,
        }
        return AdminOverviewResponse(
            corpus=retrieval_service.progress(),
            ingestion=IngestionJobTracker().status(),
            extraction=staging_extraction_status(),
            models={
                "ollama": ollama_status,
                "extraction": extraction_model,
            },
        )

    @app.get("/v1/ingestion/status", response_model=IngestionStatusResponse)
    def ingestion_status_route() -> IngestionStatusResponse:
        status = IngestionJobTracker().status()
        return IngestionStatusResponse(**status)

    @app.get("/v1/models/ollama", response_model=ModelStatusResponse)
    def ollama_status_route() -> ModelStatusResponse:
        status = OllamaChatClient(OllamaSettings()).status()
        return ModelStatusResponse(**status.to_dict())

    @app.get("/v1/models/extraction", response_model=ExtractionModelStatusResponse)
    def extraction_model_status_route() -> ExtractionModelStatusResponse:
        return ExtractionModelStatusResponse(
            local_model=LOCAL_EXTRACTION_MODEL,
            local_available=True,
            hosted_model=legal_settings.openai_extraction_model,
            hosted_configured=bool(legal_settings.openai_api_key),
            prompt_version=PROMPT_VERSION,
        )

    @app.get("/v1/chat/status", response_model=ChatStatusResponse)
    def chat_status_route() -> ChatStatusResponse:
        readiness = LocalLegalRagPipeline(retrieval_service=retrieval_service).readiness()
        return ChatStatusResponse(**readiness.to_dict())

    @app.get("/v1/extractions/status", response_model=ExtractionStatusResponse)
    def extraction_status_route() -> ExtractionStatusResponse:
        return ExtractionStatusResponse(**staging_extraction_status())

    @app.post("/v1/extractions/judgments", response_model=ExtractionRunResponse)
    def extract_judgments_route(request: ExtractionRunRequest) -> ExtractionRunResponse:
        summary = extract_staging_judgments(
            limit=request.limit,
            model=request.model or LOCAL_EXTRACTION_MODEL,
        )
        return ExtractionRunResponse(**summary.to_dict())

    @app.post("/v1/search", response_model=SearchResponse)
    def search_route(request: SearchRequest) -> SearchResponse:
        results = retrieval_service.search(
            request.query,
            limit=request.limit,
            source_types=request.source_types,
            mode=request.mode,
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

    @app.post("/v1/similar-cases", response_model=SimilarCasesResponse)
    def similar_cases_route(request: SimilarCasesRequest) -> SimilarCasesResponse:
        results = retrieval_service.similar_cases(request.case_text, limit=request.limit)
        return SimilarCasesResponse(results=[item.to_dict() for item in results])

except ImportError:
    # FastAPI is an app runtime dependency. The pure function above keeps the
    # skeleton importable in the current data-pipeline environment.
    app = None
