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
POST /v1/chat
POST /v1/search
POST /v1/cases
POST /v1/cases/{case_id}/files
GET  /v1/cases/{case_id}/analysis
POST /v1/lawyer/reviews
GET  /v1/admin/corpus/progress
```

## Implementation Note

Use FastAPI for the Python MVP. Keep route handlers thin and call service modules under `services/` or `legal_db/`.

