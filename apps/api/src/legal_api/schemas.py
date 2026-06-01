from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    limit: int = Field(default=10, ge=1, le=50)
    source_types: list[str] | None = None


class SearchResultModel(BaseModel):
    source_type: str
    title: str
    snippet: str
    score: float
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultModel]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    context_limit: int = Field(default=5, ge=1, le=10)
    use_llm: bool = True


class ChatResponse(BaseModel):
    question: str
    answer: str | None
    model: str | None = None
    model_status: str
    retrieved_results: list[SearchResultModel]
    error: str | None = None


class ModelStatusResponse(BaseModel):
    configured_model: str
    selected_model: str | None
    installed_models: list[str]
    available: bool
    base_url: str


class CaseAnalyzeRequest(BaseModel):
    case_text: str = Field(..., min_length=20)
    context_limit: int = Field(default=5, ge=1, le=10)
    use_llm: bool = True


class CaseAnalyzeResponse(BaseModel):
    analysis: dict[str, Any]
    retrieved_results: list[SearchResultModel]
    llm_note: str | None = None
    model: str | None = None
    model_status: str
    error: str | None = None
