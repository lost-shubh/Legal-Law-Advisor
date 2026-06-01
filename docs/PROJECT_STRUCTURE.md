# Project Structure

This repository contains the database and ingestion foundation for the Indian Legal Law Advisor platform.

## Core Areas

```text
sql/
  PostgreSQL + pgvector production schema, indexes and seed data.

legal_db/
  Python package for source ingestion, PDF/OCR processing, AI extraction,
  embeddings, citation parsing and quality checks.

scripts/
  Operational scripts for schema setup, local directories, staging ingestion
  and ingestion manifest export.

config/
  Official source registry and priority source configuration.

docs/
  Build plan, source notes, compliance, runbook, ingestion status and database
  design notes.

tests/
  Lightweight tests for parsing and chunking logic.

data/
  Local-only staging database and raw legal documents. Raw data is ignored by
  git and should be stored in object storage or imported into PostgreSQL.

manifests/
  Git-tracked summaries of what has been ingested locally.
```

## Current Implementation

Implemented:

- production PostgreSQL schema with public corpus, private case, embedding and quality tables
- legal provision and criminal offence catalog tables for BNS/articles/rules
- 10,000-judgment corpus target configuration and progress reporting
- staging SQLite database workflow because Docker/WSL is blocked on local admin elevation
- official-source statute ingestion for 16 priority Acts
- legal books/materials ingestion with chapter and chunk indexing
- official Supreme Court latest judgment ingestion
- PDF text extraction using PyMuPDF
- local Ollama chatbot client with retrieval from book chunks
- citation parser skeleton
- embedding pipeline skeleton
- AI extraction prompt/validation skeleton
- data quality SQL checks

Not implemented yet:

- Gazette ingestion
- High Court ingestion
- eCourts/district court ingestion
- 10,000-case collection completion
- BNS offence catalog extraction population
- OCR confidence scoring for scanned PDFs
- production PostgreSQL import from staging
- embeddings generation
- citation graph resolution
- AI extraction batch writes
