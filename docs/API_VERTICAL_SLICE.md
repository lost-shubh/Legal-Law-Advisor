# API Vertical Slice

The API now has a working MVP slice over the local staging corpus.

## Run

```powershell
$env:PYTHONPATH="F:\indian-legal-database;F:\indian-legal-database\apps\api\src"
uvicorn legal_api.main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints

```text
GET  /health
GET  /v1/admin/overview
GET  /v1/corpus/progress
GET  /v1/ingestion/status
GET  /v1/models/ollama
GET  /v1/models/extraction
GET  /v1/chat/status
GET  /v1/extractions/status
POST /v1/search
POST /v1/chat
POST /v1/cases/analyze
POST /v1/cases/brief
POST /v1/similar-cases
POST /v1/extractions/judgments
```

## Search

```json
{
  "query": "constitution basic structure",
  "limit": 5,
  "source_types": ["SECTION", "BOOK_CHUNK", "JUDGMENT"],
  "mode": "lexical"
}
```

Search currently uses a local lightweight scorer over the staging SQLite corpus. Production should replace this with PostgreSQL full-text search + pgvector + reranking.

Supported modes:

- `lexical`: deterministic token matching over available staging tables. This is the default.
- `semantic`: local deterministic hash embeddings over staging judgment chunks. If embeddings are missing, it falls back to lexical search.
- `hybrid`: combines local semantic judgment search and lexical search.

Build local staging embeddings:

```powershell
python .\scripts\build_staging_embeddings.py
```

## Ingestion Status

```text
GET /v1/ingestion/status
```

Returns ingestion job totals, item status totals, and recent jobs. This powers the future admin corpus dashboard and is backed by the same tracker used by `scripts/ingest_judgments.py`.

## Admin Overview

```text
GET /v1/admin/overview
```

Read-only operations summary for the future admin UI. It combines corpus progress, ingestion status, extraction status, Ollama model status and extraction model status in one response. It is safe when the staging database or optional tables are missing.

## Chat

```json
{
  "question": "What are the basic features of the Constitution of India?",
  "context_limit": 3,
  "use_llm": true
}
```

The chat route retrieves legal context first. If `use_llm` is true, it calls Ollama using `OLLAMA_MODEL`, currently defaulted to `llama3.2:3b`, with configured fallbacks.

Set `use_llm` to false to test retrieval without waiting for the local model.

## Ollama Model Status

```powershell
python .\scripts\ollama_status.py
```

The API exposes the same check:

```text
GET /v1/models/ollama
```

The project is configured to prefer `llama3.2:3b`, which is the installed local Ollama model observed on this machine. If it is unavailable, it checks `OLLAMA_FALLBACK_MODELS`, currently `llama3.2:1b`.

## Chat Readiness

```text
GET /v1/chat/status
```

Returns whether the built-in chatbot is ready by checking both:

- installed/resolved Ollama model
- legal corpus staging database availability and searchable corpus counts

CLI equivalent:

```powershell
python .\scripts\chatbot_status.py
```

## Case Analysis

```json
{
  "case_text": "Cheque was dishonoured on 12/04/2025. Legal notice was sent and bank return memo is available.",
  "context_limit": 3,
  "use_llm": false
}
```

```text
POST /v1/cases/analyze
```

This route performs a deterministic first pass over the case text, detects likely legal domains, extracts dates and evidence categories, lists missing documents, retrieves related corpus material, and optionally asks the local Ollama model for a lawyer-ready intake note.

## Case Research Brief

```json
{
  "case_text": "Cheque was dishonoured on 12/04/2025. Legal notice was sent and bank return memo is available.",
  "context_limit": 6,
  "max_sources": 8
}
```

```text
POST /v1/cases/brief
```

This deterministic route builds a lawyer-ready research brief from the same case-analysis and retrieval pipeline. It returns issue tags, key dates, evidence mentioned, missing documents, research questions, next steps, a source digest and export-ready Markdown without requiring Ollama.

## Judgment Extraction Model

```text
GET  /v1/models/extraction
GET  /v1/extractions/status
POST /v1/extractions/judgments
```

The extraction backend has a local deterministic model, `local-rule-extractor-v1`, so staging judgment extraction can run without hosted model credentials. It extracts acts cited, sections cited, issue tags, timeline hints, allegations, defence/evidence/argument snippets, citations and outcome.

Run locally:

```powershell
python .\scripts\extract_staging_judgments.py
python .\scripts\extract_staging_judgments.py --status
```

The hosted extraction model path remains available through `extract_with_openai()` for production use once credentials and review workflows are configured.

## Similar Cases

```json
{
  "case_text": "Cheque was dishonoured and the complainant has a legal notice, bank return memo and proof of service.",
  "limit": 5
}
```

```text
POST /v1/similar-cases
```

This route searches only parsed judgment text in the staging SQLite database and returns case title, case number, decision date, source/PDF URLs, score and snippet. The current implementation is deterministic lexical similarity over the available public judgment corpus. Production should replace or augment this with embeddings, citation graph signals and reranking once the corpus is larger.
