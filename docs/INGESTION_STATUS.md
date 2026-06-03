# Ingestion Status

Last updated: 2026-06-03

## Runtime Status

Docker Desktop was installed, but PostgreSQL/pgvector containers cannot run yet because WSL/Virtual Machine Platform requires an elevated Windows administrator session to enable. A non-elevated DISM attempt on 2026-06-03 failed with `Error: 740`. The project is therefore using a staging SQLite database until Docker can run.

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
- production AI extraction fields in PostgreSQL
- production pgvector embeddings/vector search
- citation graph
- PostgreSQL/pgvector production import

## Next Steps

1. Enable WSL/Virtual Machine Platform in an elevated Windows administrator session.
2. Start Docker Desktop.
3. Run `docker compose up -d`.
4. Apply PostgreSQL schema from `sql/`.
5. Import staging SQLite records into PostgreSQL.
6. Generate DOJ/Delhi/Bombay manifests from saved official result HTML and ingest them.
7. Continue ingestion with Gazette, High Court live collectors, and eCourts pipelines.
