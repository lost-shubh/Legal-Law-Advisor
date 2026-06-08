from __future__ import annotations

from pathlib import Path

from legal_db.case_intake.pipeline import CaseIntakePipeline
from legal_db.admin.production import (
    production_admin_panels,
    production_corpus_summary,
    production_operations_status,
    production_source_health,
)
from legal_db.ai.extract import (
    LOCAL_EXTRACTION_MODEL,
    PROMPT_VERSION,
    extract_staging_judgments,
    staging_extraction_status,
)
from legal_db.ai.production import extract_production_judgments, production_extraction_status
from legal_db.config import settings as legal_settings
from legal_db.ingest.gazette import upsert_gazette_notification
from legal_db.ingest.jobs import IngestionJobTracker
from legal_db.llm.ollama import OllamaChatClient, OllamaSettings
from legal_db.llm.rag import LocalLegalRagPipeline
from legal_db.quality.production import quality_gate_passed, run_production_quality_checks
from legal_db.retrieval.service import LegalRetrievalService

from .schemas import (
    AdminPanelResponse,
    AdminOverviewResponse,
    CaseAnalyzeRequest,
    CaseAnalyzeResponse,
    CaseBriefRequest,
    CaseBriefResponse,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
    ExtractionModelStatusResponse,
    ExtractionRunRequest,
    ExtractionRunResponse,
    ExtractionStatusResponse,
    GazetteIngestRequest,
    GazetteIngestResponse,
    IngestionStatusResponse,
    ModelStatusResponse,
    SearchRequest,
    SearchResponse,
    SimilarCasesRequest,
    SimilarCasesResponse,
)


retrieval_service = LegalRetrievalService()


def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "legal-api",
        "staging_database": "available" if retrieval_service.is_available() else "missing",
    }


try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="Legal Law Advisor API", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def local_app_route() -> HTMLResponse:
        index_path = Path(__file__).resolve().parent / "ui" / "index.html"
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    @app.get("/health")
    def health_route() -> dict[str, str]:
        return health()

    @app.get("/v1/corpus/progress")
    def corpus_progress_route() -> dict:
        return retrieval_service.progress()

    @app.get("/health/deep")
    def deep_health_route() -> dict:
        quality = run_production_quality_checks()
        production_available = retrieval_service.use_production()
        return {
            "status": "ok" if retrieval_service.is_available() else "degraded",
            "service": "legal-api",
            "production_database": "available" if production_available else "missing_or_empty",
            "retrieval_available": retrieval_service.is_available(),
            "quality_gate_passed": quality_gate_passed(quality),
            "corpus": retrieval_service.progress(),
            "quality": quality,
        }

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
            extraction=(
                production_extraction_status()
                if retrieval_service.use_production()
                else staging_extraction_status()
            ),
            models={
                "ollama": ollama_status,
                "extraction": extraction_model,
            },
            quality=run_production_quality_checks(),
            sources=production_source_health(),
            operations=production_operations_status(),
        )

    @app.get("/v1/admin/panels", response_model=AdminPanelResponse)
    def admin_panels_route() -> AdminPanelResponse:
        return AdminPanelResponse(**production_admin_panels())

    @app.get("/v1/admin/corpus")
    def admin_corpus_route() -> dict:
        return production_corpus_summary()

    @app.get("/v1/admin/sources")
    def admin_sources_route() -> dict:
        return production_source_health()

    @app.get("/v1/admin/quality")
    def admin_quality_route() -> dict:
        return run_production_quality_checks()

    @app.get("/v1/admin/operations")
    def admin_operations_route() -> dict:
        return production_operations_status()

    @app.post("/v1/gazette/notifications", response_model=GazetteIngestResponse)
    def ingest_gazette_notification_route(request: GazetteIngestRequest) -> GazetteIngestResponse:
        summary = upsert_gazette_notification(
            text=request.text,
            source_url=request.source_url,
            source_document_id=request.source_document_id,
            update_effective_dates=request.update_effective_dates,
        )
        return GazetteIngestResponse(**summary.to_dict())

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
        status = (
            production_extraction_status()
            if retrieval_service.use_production()
            else staging_extraction_status()
        )
        return ExtractionStatusResponse(**status)

    @app.post("/v1/extractions/judgments", response_model=ExtractionRunResponse)
    def extract_judgments_route(request: ExtractionRunRequest) -> ExtractionRunResponse:
        if retrieval_service.use_production():
            summary = extract_production_judgments(
                limit=request.limit,
                model=request.model or LOCAL_EXTRACTION_MODEL,
            )
        else:
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

    @app.post("/v1/cases/brief", response_model=CaseBriefResponse)
    def case_brief_route(request: CaseBriefRequest) -> CaseBriefResponse:
        brief = CaseIntakePipeline(retrieval_service=retrieval_service).build_brief(
            request.case_text,
            context_limit=request.context_limit,
            max_sources=request.max_sources,
        )
        return CaseBriefResponse(**brief.to_dict())

    @app.post("/v1/similar-cases", response_model=SimilarCasesResponse)
    def similar_cases_route(request: SimilarCasesRequest) -> SimilarCasesResponse:
        results = retrieval_service.similar_cases(request.case_text, limit=request.limit)
        return SimilarCasesResponse(results=[item.to_dict() for item in results])

except ImportError:
    # FastAPI is an app runtime dependency. The pure function above keeps the
    # skeleton importable in the current data-pipeline environment.
    app = None
