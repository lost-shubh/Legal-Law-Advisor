# Build Plan

This project should be built as a legal data platform first and an AI product second.

## Phase 1: Infrastructure

- Keep all project files under `F:\indian-legal-database`.
- Use PostgreSQL with `pgvector` for structured data and semantic search.
- Use object storage for PDFs and OCR output.
- Use Redis/Celery queues for scraping, OCR and AI extraction.
- Keep database ports private in production.

## Phase 2: Core Database

Apply:

```powershell
psql $env:PG_DSN -f .\sql\001_schema.sql
psql $env:PG_DSN -f .\sql\002_indexes.sql
psql $env:PG_DSN -f .\sql\003_seed_reference.sql
```

The schema separates:

- public law and judgment corpus
- official source/provenance records
- extracted intelligence
- embeddings
- private user case files
- quality and canary checks

## Phase 3: Statutes

Start with India Code. Load the 15 priority Acts in `config/sources.yaml`, then add state Acts for the first target states.

Required fields:

- source URL
- India Code handle ID where available
- Act name and year
- section number, title and text
- content hash
- effective dates where known

## Phase 4: Gazette

Gazette data is required to know whether a provision has commenced, changed or been repealed.

Prioritize:

- BNS, BNSS and BSA commencement
- DPDP Act rules and commencement
- Consumer Protection Rules
- IT Act rules
- state amendments for target states

## Phase 5: Judgments

Collect judgments in this order:

1. Supreme Court/e-SCR.
2. Priority High Courts.
3. Selected district court disposed matters from eCourts.

Higher courts matter more for precedent. District court data is useful for factual patterns and procedural examples.

## Phase 6: OCR and Extraction

Every PDF should go through:

1. hash and dedupe
2. text PDF vs scanned PDF classification
3. extraction/OCR
4. cleaning
5. AI extraction
6. validation
7. embedding
8. citation parsing

## Phase 7: User Case Files

Private user files must go into `private_cases`, `private_case_files` and `private_case_analysis`.

Do not mix private files into public model training unless:

- explicit consent exists
- data is anonymized
- retention is defined
- audit records are kept

