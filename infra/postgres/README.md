# PostgreSQL

Production database target:

- PostgreSQL
- `pgvector`
- structured tables from `sql/`
- object storage for raw PDFs

Keep raw PDFs outside Postgres. Store only hashes, metadata, extracted text and object keys.

