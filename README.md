# Indian Legal Database

Production-oriented starter project for building an Indian legal intelligence database.

The project is organized around three principles:

1. Use official sources as primary data: India Code, e-Gazette, Supreme Court/e-SCR, DOJ judgment search, High Courts, and eCourts.
2. Keep public legal data separate from private user case files.
3. Store provenance, hashes, model versions, and validation status for every derived record.

## Folder Layout

```text
indian-legal-database/
  sql/                  PostgreSQL schema, indexes, and seed data
  legal_db/             Python package for ingestion and processing
  docs/                 Build plan, source notes, compliance, runbooks
  tests/                Small validation tests
  data/                 Local raw/processed/tmp storage, ignored by git
  logs/                 Runtime logs, ignored by git
```

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

Private user files must use the `private_case_*` tables and must not be mixed into public training data unless explicit consent and anonymization are implemented.
