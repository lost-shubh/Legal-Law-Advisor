# Legal Law Advisor - Agent Project Memory

Use this file before continuing project work. Do not repeatedly rediscover the same repo state.

Tracked memory file: `AGENT_PROJECT_MEMORY.md`.
Last checked from Codex on 2026-06-03.

## Working Rule

- When the user says "move ahead", "build further", or similar, continue from **Next Build Slice** below.
- Do not run `git status` at the start of every build turn.
- Only check git state right before staging/committing/pushing, or when a command fails because the repo state is unclear.
- Current Codex checkout path observed: `C:\Users\Admin\Legal-Law-Advisor`.
- Older docs/commands may mention `F:\indian-legal-database`; adapt those paths to the active checkout path.
- Keep raw PDFs, local SQLite DBs, and `__pycache__` ignored and out of commits.
- If code-review-graph MCP tools are available, use them before file scanning. They were not exposed in the latest Codex session, so normal Git/file inspection was used.

## Current Project State

- Repo: `https://github.com/lost-shubh/Legal-Law-Advisor.git`
- Branch: `main`
- Canonical repo memory file: `AGENT_PROJECT_MEMORY.md`
- Latest recorded pushed commit before issue #1 fix: `99cd2e3 Document current project build status`
- Local staging DB: `data/legal_corpus_staging.sqlite` is ignored.
- Active Codex checkout staging corpus at `C:\Users\Admin\Legal-Law-Advisor` after the
  2026-06-03 SCI latest-judgments batch:
  - 25 source documents
  - 25 cases
  - 25 judgments
  - 25 document_texts
  - 239,258 extracted words
  - 649 local deterministic staging embedding chunks
  - 25 local deterministic staging judgment extractions
  - 2 completed ingestion jobs; the first extraction pass failed before the PyMuPDF
    fallback was added, and the second pass populated text successfully
- Older `F:\indian-legal-database` staging snapshot recorded in committed docs/manifests:
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
  - `GET /v1/admin/overview`
  - `GET /v1/corpus/progress`
  - `GET /v1/ingestion/status`
  - `GET /v1/models/ollama`
  - `GET /v1/models/extraction`
  - `GET /v1/chat/status`
  - `GET /v1/extractions/status`
  - `POST /v1/search`
  - `POST /v1/chat`
  - `POST /v1/cases/analyze`
  - `POST /v1/similar-cases`
  - `POST /v1/extractions/judgments`

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

- Similar cases MVP:
  - `StagingRetrievalService.similar_cases()`
  - `POST /v1/similar-cases`
  - deterministic lexical similarity over parsed judgment text
  - returns case title, case number, decision date, source URL/PDF URL, score and snippet
  - safe empty result when the staging DB is missing or has a partial schema

- Semantic search MVP:
  - `scripts/build_staging_embeddings.py`
  - `legal_db.search.embeddings.build_staging_judgment_embeddings()`
  - local deterministic hash embeddings stored in the staging SQLite `staging_embeddings` table
  - `POST /v1/search` accepts `mode: "lexical"`, `mode: "semantic"` and `mode: "hybrid"`
  - semantic mode falls back to lexical search when embeddings are absent
  - active Codex checkout has 649 generated judgment embedding chunks in ignored SQLite data

- Local extraction model MVP:
  - `legal_db.ai.extract.local_extract_judgment()`
  - `scripts/extract_staging_judgments.py`
  - `GET /v1/models/extraction`
  - `GET /v1/extractions/status`
  - `POST /v1/extractions/judgments`
  - model name: `local-rule-extractor-v1`
  - prompt version: `judgment_v1`
  - extracts acts cited, sections cited, issue tags, timeline hints, citations, outcome and evidence/argument/reasoning snippets
  - active Codex checkout has 25 generated staging extractions in ignored SQLite data

- Admin/operations backend MVP:
  - `GET /v1/admin/overview`
  - read-only aggregate of corpus progress, ingestion status, extraction status, Ollama status and extraction model status
  - safe when optional staging tables are missing

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

- Supreme Court latest-judgments ingestion:
  - `legal_db/ingest/sci_latest.py`
  - `scripts/generate_sci_latest_manifest.py`
  - parses official `www.sci.gov.in` homepage latest `Judgments` anchors with `type=j`
  - converts `view-pdf` wrapper links to direct `sci-get-pdf` PDF URLs
  - emits standard manifest rows with `source_code: SCI`
  - `scripts/ingest_judgments.py` now accepts `--user-agent`; SCI blocks the default
    bot user-agent, so use the browser-compatible agent shown in `docs/JUDGMENT_INGESTION.md`
  - generated local manifests under `data/manifests/*.local.json` are ignored by git

- PDF text extraction:
  - `legal_db/pdf/ocr.py` now falls back to PyMuPDF when `pdfplumber` is not installed
  - the 25 SCI judgment PDFs were parsed through this PyMuPDF fallback in the active
    Codex checkout

## Verification Last Known Good

```powershell
python -m compileall apps legal_db scripts tests
python -m unittest discover -s tests -v
```

Last known test count: 34 passing on 2026-06-03.

## Next Build Slice

Build basic frontend pages:

1. Inspect `apps/web`, `apps/admin` and existing frontend scaffolding before adding files.
2. Build first usable pages for:
   - ask legal question
   - analyze case
   - search judgments
   - corpus progress
3. Keep the UI quiet and operational, not a landing page.
4. Start a local dev server if the frontend requires one, and verify in browser.
5. Keep API contracts aligned with current FastAPI routes.
6. Run compile/tests.
7. Commit source/docs changes only; do not commit raw PDFs, local manifests or SQLite.

## After That

1. Add admin dashboard for ingestion jobs, extraction status, model status and corpus progress.
2. Replace local deterministic hash embeddings/extraction with production pgvector/OpenAI or local embedding/extraction models.
