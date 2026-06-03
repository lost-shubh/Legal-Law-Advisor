# API App

Backend API for the Legal Law Advisor platform.

## Responsibilities

- authenticated user sessions
- legal Q&A endpoint
- statute/judgment search endpoint
- case-file upload endpoint
- private case analysis endpoint
- lawyer review workflow endpoint
- admin ingestion status endpoint

## Planned Routes

```text
GET  /health
GET  /health/deep
POST /v1/chat
POST /v1/search
POST /v1/cases/analyze
POST /v1/similar-cases
GET  /v1/corpus/progress
GET  /v1/ingestion/status
GET  /v1/models/ollama
GET  /v1/models/extraction
GET  /v1/chat/status
GET  /v1/extractions/status
POST /v1/extractions/judgments
GET  /v1/admin/overview
GET  /v1/admin/panels
GET  /v1/admin/corpus
GET  /v1/admin/sources
GET  /v1/admin/quality
GET  /v1/admin/operations
POST /v1/gazette/notifications
```

## Implementation Note

Use FastAPI for the Python MVP. Keep route handlers thin and call service modules under `services/` or `legal_db/`.

