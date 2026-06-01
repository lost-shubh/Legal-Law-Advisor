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
GET  /v1/corpus/progress
GET  /v1/models/ollama
POST /v1/search
POST /v1/chat
POST /v1/cases/analyze
```

## Search

```json
{
  "query": "constitution basic structure",
  "limit": 5,
  "source_types": ["SECTION", "BOOK_CHUNK", "JUDGMENT"]
}
```

Search currently uses a local lightweight scorer over the staging SQLite corpus. Production should replace this with PostgreSQL full-text search + pgvector + reranking.

## Chat

```json
{
  "question": "What are the basic features of the Constitution of India?",
  "context_limit": 3,
  "use_llm": true
}
```

The chat route retrieves legal context first. If `use_llm` is true, it calls Ollama using `OLLAMA_MODEL`, currently defaulted to `llama3.2:2b`, with configured fallbacks.

Set `use_llm` to false to test retrieval without waiting for the local model.

## Ollama Model Status

```powershell
python .\scripts\ollama_status.py
```

The API exposes the same check:

```text
GET /v1/models/ollama
```

The project is configured to prefer `llama3.2:2b`. If it is not installed, it checks `OLLAMA_FALLBACK_MODELS`, currently `llama3.2:3b,llama3.2:1b`.

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
