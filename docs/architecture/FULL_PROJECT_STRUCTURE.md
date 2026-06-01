# Full Project Structure

```text
Legal-Law-Advisor/
  apps/
    api/                  FastAPI backend API
    web/                  citizen-facing web app
    admin/                internal corpus/admin dashboard
    lawyer/               advocate review workspace

  services/
    ingestion/            official source collection
    document-ai/          PDF/OCR/text extraction
    legal-extraction/     law, offence, judgment intelligence extraction
    retrieval/            hybrid search, embeddings and reranking
    chat/                 RAG answer generation
    case-intake/          private user case-file analysis
    review/               human validation and advocate review
    compliance/           consent, retention, audit and safety

  legal_db/               current Python implementation package
    ingest/               source clients
    pdf/                  OCR/PDF helpers
    ai/                   extraction helpers
    search/               embedding helpers
    citations/            citation parser
    llm/                  Ollama/local model client
    quality/              data quality checks

  packages/
    contracts/            API/event schemas
    shared/               shared constants/utilities
    prompts/              versioned prompts

  sql/                    PostgreSQL schema, indexes, seed data
  scripts/                operational scripts
  config/                 source and target configs
  manifests/              committed ingestion summaries
  data/                   local generated data, ignored by git
  infra/                  deployment and operations
  docs/                   product, data and architecture docs
  tests/                  unit tests
```

## Build Sequence

1. Finish corpus ingestion and schema population.
2. Implement retrieval service over PostgreSQL/pgvector.
3. Implement API routes around retrieval and case intake.
4. Implement citizen web app.
5. Implement admin validation dashboard.
6. Implement lawyer review app.
7. Add production infra.

