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
POST /v1/search
POST /v1/chat
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

The chat route retrieves legal context first. If `use_llm` is true, it calls Ollama using `OLLAMA_MODEL`, currently defaulted to `llama3.2:3b`.

Set `use_llm` to false to test retrieval without waiting for the local model.

