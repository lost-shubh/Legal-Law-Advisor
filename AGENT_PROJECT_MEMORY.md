# Legal Law Advisor - Agent Project Memory

Use this file before continuing project work. Do not repeatedly rediscover the same repo state.

Tracked memory file: `AGENT_PROJECT_MEMORY.md`.
Last checked from Codex on 2026-06-10.

## Working Rule

- When the user says "move ahead", "build further", or similar, continue from **Next Build Slice** below.
- Do not run `git status` at the start of every build turn.
- Only check git state right before staging/committing/pushing, or when a command fails because the repo state is unclear.
- Live production/data operations checkout observed: `F:\indian-legal-database`.
- Canonical GitHub checkout also exists at `C:\Users\Admin\Legal-Law-Advisor`; keep it synced after pushed changes.
- Keep raw PDFs, local SQLite DBs, and `__pycache__` ignored and out of commits.
- If code-review-graph MCP tools are available, use them before file scanning. They were not exposed in the latest Codex session, so normal Git/file inspection was used.
- Do not upgrade/pull/configure `llama3.1:8b` on this machine. Keep the smaller local Ollama path because the user has RAM/storage limits.

## Current Project State

- Repo: `https://github.com/lost-shubh/Legal-Law-Advisor.git`
- Branch: `main`
- Canonical repo memory file: `AGENT_PROJECT_MEMORY.md`
- Latest recorded pushed commit before completed text-backfill status work: `8b975d0 Add production judgment text backfill`
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

- Production Docker/PostgreSQL status from `F:\indian-legal-database` on 2026-06-03:
  - WSL2 was enabled by the user from elevated PowerShell
  - Docker Desktop engine is running
  - `legaldb-postgres`, `legaldb-redis` and `legaldb-minio` are running
  - PostgreSQL schema exists with 33 tables
  - staging migration completed successfully at commit `19e9c16`
  - production PostgreSQL now has 95 source documents, 13 data sources, 16 statutes, 5,421 sections, 25 cases and 25 judgments
  - production judgments have 442,053 total words and 0 missing `clean_text`
  - production embedding import completed successfully after commit `723919e`
  - production PostgreSQL now has 6,945 pgvector embeddings: 5,421 `SECTION`, 1,192 `JUDGMENT_CHUNK` and 332 `BOOK_CHUNK`
  - all production embeddings are 1536-dimensional local hash embeddings
  - legal book migration completed: 3 books, 26 chapters, 332 chunks
  - production extraction completed: 25 outcomes, 125 case issues, 221 case-section rows and 25 case facts
  - production citation graph completed: 344 citation strings, 348 case citations and 348 citation edges; 0 resolved-to-local cited cases in current 25-judgment corpus
  - local folder import from `C:\Users\Admin\Downloads\New folder (3)` completed:
    - 51 files scanned
    - 49 PDFs eligible
    - 35 PDFs imported as `LOCAL_LIBRARY`
    - 2 files skipped as unsupported/personal (`.vcf`, Spotify cover letter)
    - 14 PDFs left failed because embedded text extraction produced too few words; these need OCR if they must be searchable
    - PostgreSQL now has 38 legal books, 63 book chapters, 1,573 book chunks and 1,573 `BOOK_CHUNK` embeddings
  - official/public BNS import completed at commits `819691f` and `185a99a`:
    - downloader fetched 4 official/public documents from MHA/NCRB into ignored local data
    - imported as `BNS_PUBLIC`: MHA BNS Act PDF plus NCRB Sankalan BNS index, BNS-to-IPC section table, and chapters/sections HTML pages
    - live PostgreSQL now has 4 `BNS_PUBLIC` source documents/books, 82 BNS public chapters and 280 BNS public chunks
    - live PostgreSQL now has 42 total legal books, 1,853 total book chunks and 1,853 `BOOK_CHUNK` embeddings
    - quality checks remain 9/9 passing; search smoke tests return BNS/NCRB book chunks
  - India Code Central Acts import from `C:\Users\Admin\india-code-central-acts` completed at commits `fe641e9` and `e76e96d`:
    - 846 local India Code Central Act PDFs read from `manifest.csv`
    - 846 `INDIA_CODE_CENTRAL_ACTS` source documents imported
    - 846 Central Act statutes imported/updated
    - 35,712 Central Act sections extracted
    - live PostgreSQL now has 851 total statutes and 38,094 total sections
    - `SECTION` embeddings rebuilt successfully: 38,094 section embeddings
    - live PostgreSQL now has 41,139 total embeddings: 38,094 `SECTION`, 1,192 `JUDGMENT_CHUNK`, 1,853 `BOOK_CHUNK`
    - quality checks remain 9/9 passing; search smoke tests return imported Central Act sections
  - official/public new-criminal-laws import completed at commit `9f7a763`:
    - downloader fetched 21 official/public MHA/NCRB files into ignored local data
    - imported as `NEW_CRIMINAL_LAWS_PUBLIC`: MHA BNS/BSA/BNSS Act PDFs, NCRB Sankalan PDFs/HTML tables/schedules and Gazette PDFs
    - live PostgreSQL now has 21 `NEW_CRIMINAL_LAWS_PUBLIC` source documents/books, 282 chapters and 1,524 chunks
    - live PostgreSQL now has 63 total legal books and 3,377 total book chunks
    - `BOOK_CHUNK` embeddings rebuilt successfully: 3,377 book embeddings
    - live PostgreSQL now has 42,663 total embeddings: 38,094 `SECTION`, 1,192 `JUDGMENT_CHUNK`, 3,377 `BOOK_CHUNK`
    - quality checks remain 9/9 passing; case-brief smoke test for private-defence homicide returns BNS sections 34, 35, 37, 38 and 41 as leading sources
  - `scripts/corpus_progress.py` now prefers PostgreSQL production counts when available and reports the above live corpus numbers with `--database-url`
  - API search/admin/chat status now prefer PostgreSQL retrieval and fall back to SQLite only when PostgreSQL is unavailable
  - duplicate source-document/case checks returned 0
  - quality checks are clean: 0 judgments without text, 0 impossible dates, 0 decided cases without outcomes, 0 duplicate PDF hashes, 0 wrong-dimension embeddings, 0 unvalidated AI facts
  - backend operations completion added executable quality checks, admin/source/operations panels, Gazette notification persistence and a maintenance runner

- Production PostgreSQL status from `F:\indian-legal-database` on 2026-06-10 after completed AWS Supreme Court text backfill:
  - live PostgreSQL has 1,003 judgments and 1,003 cases
  - text backfill is complete: 1,003 judgments with `clean_text`/`word_count`, 0 pending text
  - local production extraction completed for all 1,003 text-backed judgments and produced 1,003 outcomes
  - production embeddings rebuilt successfully: 64,014 total embeddings
    - 38,094 `SECTION`
    - 22,543 `JUDGMENT_CHUNK`
    - 3,377 `BOOK_CHUNK`
  - production citation graph rebuilt over all 1,003 text-backed judgments:
    - 8,385 citation strings
    - 8,385 citation edges
    - 1,016 resolved-to-local cited cases in the current corpus
  - `scripts/run_quality_checks.py --database-url ...` reports 9/9 checks passing:
    - 0 judgments without text
    - 0 cases with impossible dates
    - 0 decided cases without outcomes
    - 0 duplicate PDF hashes
    - 0 wrong-dimension embeddings
    - 0 unvalidated AI facts
    - 0 sections without text
    - 0 duplicate source documents
    - 0 duplicate case sources
  - `scripts/corpus_progress.py --database-url ...` reports 1,003 / 10,000 judgments = 10.03%
  - API hybrid search smoke test returned HTTP 200 with 5 `JUDGMENT` results for an arbitration query

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

- Local folder ingestion for user-provided PDF/HTML/text libraries:
  - `legal_db.ingest.local_documents`
  - `scripts/ingest_local_documents.py`
  - imports documents into PostgreSQL `source_documents`, `legal_books`, `book_chapters` and `book_chunks`
  - supports dry-run before database writes
  - supports downloader manifests to preserve original public source URLs/titles
  - skips unsupported files and obvious personal/non-legal PDFs by default
  - raw PDFs stay local-only and must not be committed

- Official/public BNS document ingestion:
  - `legal_db.ingest.bns_public_documents`
  - `scripts/download_bns_public_documents.py`
  - downloads a curated official-source set from MHA and NCRB, not private commentary or paywalled Manupatra material
  - use `scripts/ingest_local_documents.py --manifest ... --source-code BNS_PUBLIC --official-source` to ingest

- Official/public new-criminal-laws document downloader:
  - `legal_db.ingest.new_criminal_laws_public_documents`
  - `scripts/download_new_criminal_laws_public_documents.py`
  - dry-run currently plans 21 MHA/NCRB documents across BNS, BNSS, BSA, NCRB Sankalan tables/schedules and Gazette PDFs
  - intended import source code: `NEW_CRIMINAL_LAWS_PUBLIC`
  - raw downloaded files stay ignored under `data/raw/new_criminal_laws_public`; do not commit PDFs/HTML exports

- India Code Central Acts ingestion:
  - `legal_db.ingest.central_acts`
  - `scripts/ingest_india_code_central_acts.py`
  - imports a local `manifest.csv` plus downloaded India Code Central Act PDFs into PostgreSQL `source_documents`, `statutes` and `sections`
  - extracts numeric and old Roman-numbered section headings while skipping arrangement-of-sections/front-matter and amendment-note footnotes
  - preserves existing referenced `sections` rows by updating in place and marking only referenced stale rows non-current
  - run `scripts/build_pg_embeddings.py --source-type SECTION --replace` after import

- FastAPI routes:
  - `GET /` local browser app
  - `GET /health`
  - `GET /health/deep`
  - `GET /v1/admin/overview`
  - `GET /v1/admin/panels`
  - `GET /v1/admin/corpus`
  - `GET /v1/admin/sources`
  - `GET /v1/admin/quality`
  - `GET /v1/admin/operations`
  - `GET /v1/corpus/progress`
  - `GET /v1/ingestion/status`
  - `GET /v1/models/ollama`
  - `GET /v1/models/extraction`
  - `GET /v1/chat/status`
  - `GET /v1/extractions/status`
  - `POST /v1/search`
  - `POST /v1/chat`
  - `POST /v1/cases/analyze`
  - `POST /v1/cases/brief`
  - `POST /v1/similar-cases`
  - `POST /v1/extractions/judgments`
  - `POST /v1/gazette/notifications`

- Local Ollama integration:
  - preferred/default model: `llama3.2:3b`
  - fallback: `llama3.2:1b`
  - actual installed model observed: `llama3.2:3b`
  - `llama3.1:8b` intentionally not used because of local storage/RAM limits
  - `llama3.2:2b` was not available as an Ollama tag
  - GitHub issue #1 "Lama version conflict" fixed by aligning defaults to installed `llama3.2:3b`
  - chatbot readiness exposed through `GET /v1/chat/status`
  - CLI readiness helper: `scripts/chatbot_status.py`

- Case analyzer MVP:
  - issue tags
  - high-stakes criminal anchors for murder/private-defence/night-house-breaking fact patterns
  - dates
  - evidence categories
  - missing documents
  - urgent warnings
  - retrieved legal context
  - optional local LLM note
  - `legal_db.case_intake.legal_anchors` prepends deterministic BNS/BSA/BNSS provisions before fuzzy search results for private-defence homicide cases

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

- Production pgvector retrieval:
  - `scripts/build_pg_embeddings.py`
  - `legal_db.search.embeddings.build_production_embeddings()`
  - `legal_db.retrieval.production.ProductionRetrievalService`
  - `legal_db.retrieval.service.LegalRetrievalService`
  - local deterministic 1536-dimensional embeddings in PostgreSQL `embeddings`
  - production full-text lexical search over sections, judgments and book chunks
  - production pgvector semantic search over section, judgment chunk and book chunk embeddings
  - hybrid search merges production lexical and semantic results
  - active `F:\indian-legal-database` PostgreSQL has 64,014 production embeddings

- Production extraction/outcomes:
  - `legal_db.ai.production.extract_production_judgments()`
  - `scripts/extract_pg_judgments.py`
  - populates `outcomes`, `case_issues`, `case_sections`, `case_facts` and `extraction_runs`
  - active `F:\indian-legal-database` PostgreSQL has 1,003 extracted judgments and 1,003 outcomes

- Production citation graph:
  - `legal_db.citations.graph.build_production_citation_graph()`
  - `scripts/build_pg_citations.py`
  - populates `citation_strings`, `case_citations` and `citations`
  - active `F:\indian-legal-database` PostgreSQL has 8,385 citation edges, with 1,016 resolved locally

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
  - read-only aggregate of corpus progress, ingestion status, extraction status, Ollama status, extraction model status, source health, operations queues and quality checks
  - `GET /v1/admin/panels`, `/v1/admin/corpus`, `/v1/admin/sources`, `/v1/admin/quality` and `/v1/admin/operations`
  - `legal_db.admin.production` centralizes PostgreSQL admin panel queries
  - `legal_db.quality.production` executes PostgreSQL quality checks and reports pass/fail/error summaries
  - `scripts/run_quality_checks.py`
  - `scripts/run_backend_maintenance.py`
  - safe when optional staging tables are missing

- Local browser app:
  - served directly by FastAPI at `GET /`
  - source file: `apps/api/src/legal_api/ui/index.html`
  - case analyzer screen calls `/v1/cases/analyze` and `/v1/similar-cases`
  - brief screen calls `/v1/cases/brief` and can download the deterministic Markdown research brief
  - search screen calls `/v1/search` with lexical, semantic and hybrid modes
  - chat screen calls `/v1/chat/status` and `/v1/chat`
  - admin screen calls `/v1/admin/panels`
  - Gazette screen calls `/v1/gazette/notifications`
  - no Node/Vite frontend server is required for the current local MVP UI

- Gazette backend:
  - `legal_db.ingest.gazette.upsert_gazette_notification()`
  - `scripts/ingest_gazette.py`
  - `POST /v1/gazette/notifications`
  - parses notification number, type, act name, commencement/effective date and affected sections from OCR/plain text
  - stores rows in `gazette_notifications`, ensures an `EGAZETTE` source document when a source URL is provided and can update statute commencement/effective dates
  - live e-Gazette harvesting is still a source/data task; the backend persistence path exists

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

  - AWS Open Data Supreme Court corpus ingestion:
  - `legal_db.ingest.aws_sc_open_data`
  - `scripts/generate_aws_sc_manifest.py`
  - source code: `SC_AWS_OPEN_DATA`
  - generates standard judgment manifests from the public AWS Open Data Indian Supreme Court Judgments yearly indexes and metadata JSON
  - use `scripts/ingest_judgments.py --delay-seconds 0` for AWS batches, then `scripts/migrate_staging_to_postgres.py --only judgments`
  - `scripts/extract_pg_judgment_text.py` backfills PostgreSQL `raw_text`/`clean_text` from already downloaded local PDFs without re-downloading
  - 5-row smoke batch for 2025 completed successfully: PostgreSQL reached 30 judgments and stayed at 38,094 sections after duplicate cleanup
  - 970-row + 10-row top-off run completed from AWS Open Data in the live `F:\indian-legal-database` checkout:
    - PostgreSQL reached 1,003 judgments and 1,003 cases
    - source document coverage: 978 `SC_AWS_OPEN_DATA`, 26 `SCI`
    - 1,003 judgments currently have extracted/searchable text, 0 raw-downloaded judgments remain pending text backfill
    - `JUDGMENT_CHUNK` embeddings rebuilt: 22,543 judgment chunk embeddings
    - local production extraction completed for all 1,003 text-backed judgments and produced 1,003 outcomes
    - citation graph rebuilt over all 1,003 text-backed judgments: 8,385 citation strings/edges, 1,016 resolved locally
    - `scripts/corpus_progress.py --database-url ...` reports 1,003 / 10,000 judgments = 10.03%
    - quality checks are clean: 9/9 checks passing, 0 WARN/ERROR failures
  - do not use normal `migrate_staging_to_postgres.py` without `--only judgments` for judgment batches; full migration can reprocess old staging statute rows

- PDF text extraction:
  - `legal_db/pdf/ocr.py` now falls back to PyMuPDF when `pdfplumber` is not installed
  - `estimate_text_quality()` produces an `ocr_quality` score for extracted text
  - judgment ingestion stores `ocr_quality` in the staging `judgments` table
  - batch extraction skips text below 100 words or with `ocr_quality < 0.6`
  - the 25 SCI judgment PDFs were parsed through this PyMuPDF fallback in the active
    Codex checkout

- Production migration helper:
  - `scripts/migrate_staging_to_postgres.py`
  - `--dry-run` reports staging counts without requiring PostgreSQL dependencies
  - actual migration targets staging `source_documents`, `statutes`, `sections`, `cases`, `judgments` and associated `document_texts`
  - PostgreSQL/pgvector import is still blocked until WSL/Docker are live

- DOJ/High Court saved-HTML manifest helper:
  - `legal_db/ingest/judgment_collectors.py`
  - `scripts/generate_hc_manifest.py`
  - supported collectors: `doj`, `delhi`, `bombay`
  - parses saved official result HTML into the standard judgment manifest shape for `scripts/ingest_judgments.py`
  - live portal automation is still future work

## Current Blockers And Constraints

- WSL/Docker/PostgreSQL are now unblocked in the `F:\indian-legal-database` checkout.
- PostgreSQL/pgvector production import for current staging statutes/sections/judgments is complete.
- Do not pull `llama3.1:8b`; continue with `llama3.2:3b` default and `llama3.2:1b` fallback.
- Remaining production gaps: High Court collectors at scale, live e-Gazette source harvesting/input files, frontend/admin UI, live deployment/monitoring and much larger corpus scale.

## Verification Last Known Good

```powershell
python -m compileall apps legal_db scripts tests
python -m unittest discover -s tests -v
```

Last known test count: 80 passing on 2026-06-08.
Last known production quality check: 9/9 passing on 2026-06-10.
Last known API search smoke test: HTTP 200 with 5 judgment results on 2026-06-10.

## Next Build Slice

Continue the data/UI scale path:

1. Start High Court/DOJ corpus expansion toward the 10,000-judgment target.
2. Collect saved official DOJ/Delhi/Bombay result HTML and generate manifests with `scripts/generate_hc_manifest.py`.
3. Ingest generated manifests with `scripts/ingest_judgments.py`.
4. Run production migration/text backfill, extraction, citation and embedding scripts over each expanded corpus batch.
5. Feed official e-Gazette OCR/plain text into `scripts/ingest_gazette.py` for BNS/BNSS/BSA and other priority commencement/amendment notices.
6. Improve the browser app/admin UI around the now-complete 1,003-judgment MVP corpus.
7. Keep source/docs changes only; do not commit raw PDFs, local manifests or SQLite.

## After That

1. Add live source collectors for DOJ, High Courts and eCourts when portal behavior is known.
2. Build basic citizen/admin frontend pages after the corpus reaches a useful size.
3. Replace deterministic local production embeddings/extraction with stronger OpenAI or local models where practical.
