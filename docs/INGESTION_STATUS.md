# Ingestion Status

Last updated: 2026-06-03

## Runtime Status

WSL2 and Docker Desktop are now enabled on the Windows machine. From the `F:\indian-legal-database` checkout, Docker Compose is running:

- `legaldb-postgres`
- `legaldb-redis`
- `legaldb-minio`

PostgreSQL/pgvector schema is applied and the current staging corpus has been migrated into PostgreSQL.

Staging database:

```text
C:\Users\Admin\Legal-Law-Advisor\data\legal_corpus_staging.sqlite
```

Raw documents:

```text
C:\Users\Admin\Legal-Law-Advisor\data\raw
```

Older committed summaries may still reference `F:\indian-legal-database`; adapt those paths
to the active checkout when working from Codex.

## Loaded Into Staging

Current active Codex checkout staging counts:

- source documents: 25
- extracted document texts: 25
- Supreme Court cases: 25
- Supreme Court judgments: 25
- extracted judgment words: 239,258
- local staging embedding chunks: 649
- local staging judgment extractions: 25
- OCR/text quality gate: available in staging judgment ingestion
- SQLite-to-PostgreSQL judgment migration helper: available, dry-run supported
- DOJ/Delhi/Bombay saved-HTML manifest helper: available
- statutes: 0 in the active `C:\Users\Admin\Legal-Law-Advisor` staging DB
- legal books/materials: 0 in the active `C:\Users\Admin\Legal-Law-Advisor` staging DB

The older `F:\indian-legal-database` snapshot recorded in committed summaries had 16
statutes, 5,421 extracted statute sections, 3 legal books/materials, 26 chapters and
332 book chunks.

## Loaded Into PostgreSQL

Current production PostgreSQL counts after migration:

- data sources: 13
- source documents: 95
- statutes: 16
- sections: 5,421
- cases: 25
- judgments: 25
- judgment words: 442,053

Quality checks:

- judgments without text: 0
- cases with impossible dates: 0
- duplicate PDF hashes: 0
- duplicate source documents: 0
- duplicate migrated cases: 0
- decided cases without outcomes: 25

## Production Corpus Target

The production judgment target is now 10,000 judgments:

- 2,000 Supreme Court judgments
- 5,000 High Court judgments
- 3,000 District Court public judgments/orders

Current judgment progress: 25 / 10,000.

## Priority Acts Loaded In Older Snapshot

Official PDFs and extracted text were loaded in the older `F:\indian-legal-database`
snapshot for:

- BNS, 2023
- BNSS, 2023
- BSA, 2023
- Digital Personal Data Protection Act, 2023
- Negotiable Instruments Act, 1881
- Information Technology Act, 2000
- Consumer Protection Act, 2019
- Hindu Marriage Act, 1955
- Protection of Women from Domestic Violence Act, 2005
- Transfer of Property Act, 1882
- Constitution of India
- Motor Vehicles Act, 1988
- Industrial Disputes Act, 1947
- Indian Penal Code, 1860
- Code of Criminal Procedure, 1973
- Indian Evidence Act, 1872

## Supreme Court Judgments Loaded

The latest 25 official Supreme Court judgment PDFs visible on the Supreme Court homepage were downloaded through `sci.gov.in/sci-get-pdf`, extracted with PyMuPDF, and recorded in `cases`, `judgments`, `source_documents`, and `document_texts`.

## Not Yet Loaded

- Gazette commencement/amendment notifications
- High Court judgments
- District court/eCourts data
- BNS offence/charge catalog rows
- full Law Commission report corpus
- full OCR workflow for scanned High Court and district PDFs at scale
- production AI extraction/outcome rows in PostgreSQL
- production pgvector embeddings/vector search rows
- citation graph
- PostgreSQL/pgvector production import

## Next Steps

1. Build production embedding import for sections and judgment chunks.
2. Build production extraction/outcome import for migrated judgments.
3. Generate DOJ/Delhi/Bombay manifests from saved official result HTML and ingest them.
4. Continue ingestion with Gazette, High Court live collectors, and eCourts pipelines.
