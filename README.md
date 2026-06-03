# Indian Legal Database

Production-oriented starter project for building an Indian legal intelligence database.

The project is organized around three principles:

1. Use official sources as primary data: India Code, e-Gazette, Supreme Court/e-SCR, DOJ judgment search, High Courts, and eCourts.
2. Keep public legal data separate from private user case files.
3. Store provenance, hashes, model versions, and validation status for every derived record.

## Current Build Status

This repository is currently a working MVP foundation, not the finished 10,000-judgment production system.

Completed so far:

- Full monorepo structure for API, citizen web app, admin app, lawyer review app, services, shared packages, SQL, docs, tests and infrastructure.
- Production PostgreSQL schema for legal sources, statutes, sections, provisions, offences, books, cases, judgments, outcomes, citations, embeddings, private case files, ingestion jobs and quality checks.
- Local SQLite staging corpus and ingestion workflow for development before PostgreSQL/WSL is fully available.
- Priority statute and section ingestion scaffold, with current staging data including `16` statutes and `5,421` sections.
- Legal books/materials ingestion with chapters and chunks, currently `3` materials, `26` chapters and `332` chunks in staging.
- FastAPI vertical slice with search, chat, corpus progress, ingestion status, Ollama status, case analysis and similar-cases routes.
- Retrieval MVP over statutes, books and judgment text, with lexical, semantic and hybrid search modes.
- Local Ollama integration with configured `llama3.2:3b` default and `llama3.2:1b` fallback.
- Chat readiness status that checks both the selected Ollama model and legal corpus availability.
- Case analyzer MVP that detects issue tags, dates, evidence categories, missing documents, urgency warnings and related legal context.
- Judgment ingestion tracking with job/item status, manifest ingestion, PDF hashing, raw PDF storage path, case/judgment inserts and optional text extraction.
- Supreme Court/e-SCR manifest generator that parses saved SCR/e-SCR result HTML or accessible result pages into standard judgment manifests.
- Automated tests covering API routes, retrieval, local semantic search, similar cases, case intake, citation parsing, chunking, ingestion tracking, manifest ingestion and SCI/e-SCR manifest generation.

Current staging corpus snapshot:

```text
Statutes:          16
Sections:          5,421
Cases/Judgments:   25
Legal materials:   3
Book chapters:     26
Book chunks:       332
Document texts:    44
Embedding chunks:  649 local staging chunks
Test suite:        28 passing tests
```

Main work still left:

- Ingest the first `1,000` official judgments, then scale toward `10,000`.
- Build source-specific collectors for High Courts, DOJ judgment portal and district/eCourts data.
- Run OCR and AI extraction at scale.
- Replace local deterministic hash embeddings with production pgvector/OpenAI or local embedding models.
- Build the citizen frontend, lawyer review app and admin dashboard.
- Deploy the production PostgreSQL/pgvector stack and add operational monitoring.

## Folder Layout

```text
indian-legal-database/
  apps/                 API, citizen web app, admin app, lawyer review app
  services/             service ownership boundaries for ingestion/RAG/case intake
  packages/             shared contracts, prompts and utilities
  sql/                  PostgreSQL schema, indexes, and seed data
  legal_db/             Python package for ingestion and processing
  docs/                 Build plan, source notes, compliance, runbooks
  infra/                deployment and operations skeleton
  tests/                Small validation tests
  data/                 Local raw/processed/tmp storage, ignored by git
  logs/                 Runtime logs, ignored by git
```

See [FULL_PROJECT_STRUCTURE.md](docs/architecture/FULL_PROJECT_STRUCTURE.md) for the complete planned structure.

## Local Start

On this Windows machine, Docker Desktop has been installed, but Docker cannot run Linux containers until WSL/Virtual Machine Platform is enabled from an elevated administrator session. Until then, use the staging SQLite ingestion workflow in [STAGING_INGESTION.md](docs/STAGING_INGESTION.md).

1. Copy `.env.example` to `.env` and adjust values.
2. Start services:

```powershell
docker compose up -d
```

3. Apply schema:

```powershell
psql $env:DATABASE_URL -f .\sql\001_schema.sql
psql $env:DATABASE_URL -f .\sql\002_indexes.sql
psql $env:DATABASE_URL -f .\sql\003_seed_reference.sql
```

4. Install Python dependencies in a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

5. Run a sanity check:

```powershell
python -m legal_db.cli quality-sql
```

## Build Order

Start with the public corpus:

1. Load priority statutes from India Code.
2. Load commencement/amendment data from e-Gazette.
3. Load Supreme Court judgments.
4. Load selected High Court judgments.
5. Load selected district court orders/judgments from eCourts.
6. Run OCR/text extraction.
7. Run AI extraction with validation.
8. Create embeddings and citation graph.

## Corpus Target

The production target is not the current seed corpus. The target is:

- `10,000` judgments/orders with official provenance
- `2,000` Supreme Court judgments
- `5,000` High Court judgments
- `3,000` District Court public judgments/orders
- BNS offence/charge catalog, Constitution Articles, statute Sections, Rules and Regulations

Track progress:

```powershell
python .\scripts\corpus_progress.py
```

Build local deterministic staging embeddings:

```powershell
python .\scripts\build_staging_embeddings.py
```

Ingest judgment PDFs from a manifest:

```powershell
python .\scripts\generate_sc_manifest.py --html .\data\source_exports\scr_results.html --output .\data\manifests\sc_escr_manifest.local.json
python .\scripts\ingest_judgments.py --init-template .\data\judgment_manifest.local.json
python .\scripts\ingest_judgments.py .\data\judgment_manifest.local.json --limit 10
python .\scripts\ingest_judgments.py --status
```

See [JUDGMENT_INGESTION.md](docs/JUDGMENT_INGESTION.md).

Local chatbot prototype:

```powershell
python .\scripts\chat_local.py "What is the basic structure of Indian courts?"
```

Check the local Ollama model selection:

```powershell
python .\scripts\ollama_status.py
python .\scripts\chatbot_status.py
```

API vertical slice:

```powershell
$env:PYTHONPATH="F:\indian-legal-database;F:\indian-legal-database\apps\api\src"
uvicorn legal_api.main:app --reload --host 127.0.0.1 --port 8000
```

Useful API routes:

```text
GET  /v1/ingestion/status
GET  /v1/models/ollama
GET  /v1/chat/status
POST /v1/search
POST /v1/chat
POST /v1/cases/analyze
POST /v1/similar-cases
```

Private user files must use the `private_case_*` tables and must not be mixed into public training data unless explicit consent and anonymization are implemented.
