# Staging Ingestion

Docker/PostgreSQL needs WSL/administrator setup on this Windows machine. Until that is available, the project uses a staging SQLite database:

```text
F:\indian-legal-database\data\legal_corpus_staging.sqlite
```

Raw official documents are stored under:

```text
F:\indian-legal-database\data\raw
```

Run:

```powershell
python .\scripts\ingest_staging.py init
python .\scripts\ingest_staging.py ingest-priority-acts
python .\scripts\ingest_staging.py summary
```

The staging database stores provenance, source URL, final URL, HTTP status, file hash, local file path, statutes, extracted sections when available, and discovered PDF/download links.

This is an import staging area. PostgreSQL/pgvector remains the production database target.

