# Staging Ingestion

Docker/PostgreSQL needs WSL/administrator setup on this Windows machine. Until that is available, the project uses a staging SQLite database:

```text
C:\Users\Admin\Legal-Law-Advisor\data\legal_corpus_staging.sqlite
```

Raw official documents are stored under:

```text
C:\Users\Admin\Legal-Law-Advisor\data\raw
```

Run:

```powershell
python .\scripts\ingest_staging.py init
python .\scripts\ingest_staging.py ingest-priority-acts
python .\scripts\ingest_staging.py summary
```

The staging database stores provenance, source URL, final URL, HTTP status, file hash, local file path, statutes, extracted sections when available, and discovered PDF/download links.

This is an import staging area. PostgreSQL/pgvector remains the production database target.

Before importing to PostgreSQL, run a dry-run count:

```powershell
python .\scripts\migrate_staging_to_postgres.py --dry-run
```

Run the actual migration only after WSL/Docker/PostgreSQL are live and `sql/001_schema.sql`, `sql/002_indexes.sql`, and `sql/003_seed_reference.sql` have been applied:

```powershell
python .\scripts\migrate_staging_to_postgres.py
```

