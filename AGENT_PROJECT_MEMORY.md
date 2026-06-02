# Legal Law Advisor - Agent Project Memory

Use this file before continuing project work. Do not repeatedly rediscover the same repo state.

## Working Rule

- When the user says "move ahead", "build further", or similar, continue from **Next Build Slice** below.
- Do not run `git status` at the start of every build turn.
- Only check git state right before staging/committing/pushing, or when a command fails because the repo state is unclear.
- Keep work in `F:\indian-legal-database`.
- Keep raw PDFs, local SQLite DBs, and `__pycache__` ignored and out of commits.

## Current Project State

- Repo: `https://github.com/lost-shubh/Legal-Law-Advisor.git`
- Branch: `main`
- Latest recorded pushed commit before issue #1 fix: `99cd2e3 Document current project build status`
- Local staging DB: `data/legal_corpus_staging.sqlite` is ignored.
- Current staging corpus:
  - 16 statutes
  - 5,421 sections
  - 25 cases/judgments
  - 3 legal books/materials
  - 26 book chapters
  - 332 book chunks
  - 44 document_texts

## Built So Far

- Full project scaffold:
  - `apps/api`
  - `apps/web`
  - `apps/admin`
  - `apps/lawyer`
  - `legal_db`
  - `services`
  - `packages`
  - `sql`
  - `docs`
  - `infra`
  - `tests`

- Production SQL schema:
  - courts, sources, source documents
  - statutes, sections, provisions, criminal offences
  - gazette notifications
  - legal books, chapters, chunks
  - cases, judgments, outcomes, citations
  - embeddings
  - private case tables
  - corpus targets, collection batches
  - ingestion jobs/items
  - quality/canary tables

- FastAPI routes:
  - `GET /health`
  - `GET /v1/corpus/progress`
  - `GET /v1/ingestion/status`
  - `GET /v1/models/ollama`
  - `GET /v1/chat/status`
  - `POST /v1/search`
  - `POST /v1/chat`
  - `POST /v1/cases/analyze`

- Local Ollama integration:
  - preferred/default model: `llama3.2:3b`
  - fallback: `llama3.2:1b`
  - actual installed model observed: `llama3.2:3b`
  - `llama3.2:2b` was not available as an Ollama tag
  - GitHub issue #1 "Lama version conflict" fixed by aligning defaults to installed `llama3.2:3b`
  - chatbot readiness exposed through `GET /v1/chat/status`
  - CLI readiness helper: `scripts/chatbot_status.py`

- Case analyzer MVP:
  - issue tags
  - dates
  - evidence categories
  - missing documents
  - urgent warnings
  - retrieved legal context
  - optional local LLM note

- Judgment ingestion tracking:
  - `legal_db/ingest/jobs.py`
  - `legal_db/ingest/judgments.py`
  - `scripts/ingest_judgments.py`
  - `config/judgment_manifest.example.json`
  - `docs/JUDGMENT_INGESTION.md`

- Supreme Court/e-SCR manifest generation:
  - `legal_db/ingest/escr.py`
  - `scripts/generate_sc_manifest.py`
  - parses saved SCR/e-SCR result HTML or directly accessible result URLs
  - outputs standard judgment manifest rows for existing ingestion pipeline
  - extracts title, PDF URL, neutral citation, case number, judgment date and source context
  - tests in `tests/test_escr_manifest.py`

## Verification Last Known Good

```powershell
python -m compileall apps legal_db scripts tests
python -m unittest discover -s tests -v
```

Last known test count: 18 passing.

## Next Build Slice

Create and ingest the first Supreme Court batch:

1. Generate a real SCR/e-SCR manifest into `data/manifests/sc_escr_manifest.local.json`.
2. Ingest first 25 official Supreme Court judgments with:
   - `scripts/generate_sc_manifest.py`
   - `scripts/ingest_judgments.py`
3. Keep downloaded PDFs in ignored `data/raw/judgments`.
4. Check `/v1/ingestion/status` and corpus progress.
5. If live e-SCR result access is blocked by CAPTCHA, use manually saved SCR result HTML or a manually curated official-PDF manifest.
6. Run compile/tests.
7. Commit source/docs changes only; do not commit raw PDFs or local SQLite.

## After That

1. Add `/v1/similar-cases`.
2. Add embeddings/semantic search.
3. Build basic frontend pages:
   - ask legal question
   - analyze case
   - search judgments
   - corpus progress
4. Add admin dashboard for ingestion jobs and corpus progress.
