# Ingestion Status

Last updated: 2026-06-01

## Runtime Status

Docker Desktop was installed, but PostgreSQL/pgvector containers cannot run yet because WSL/Virtual Machine Platform requires an elevated Windows administrator session to enable. The project is therefore using a staging SQLite database until Docker can run.

Staging database:

```text
F:\indian-legal-database\data\legal_corpus_staging.sqlite
```

Raw documents:

```text
F:\indian-legal-database\data\raw
```

## Loaded Into Staging

Current staging counts:

- data sources: 9
- source documents: 91
- statutes: 16
- extracted statute sections: 5421
- extracted document texts: 41
- Supreme Court cases: 25
- Supreme Court judgments: 25

## Priority Acts Loaded

Official PDFs and extracted text are loaded for:

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
- OCR for scanned judgment PDFs
- AI extraction fields
- embeddings/vector search
- citation graph
- PostgreSQL/pgvector production import

## Next Steps

1. Enable WSL/Virtual Machine Platform in an elevated Windows administrator session.
2. Start Docker Desktop.
3. Run `docker compose up -d`.
4. Apply PostgreSQL schema from `sql/`.
5. Import staging SQLite records into PostgreSQL.
6. Continue ingestion with Gazette, High Court, and eCourts pipelines.

