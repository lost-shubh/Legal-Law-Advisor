# Retrieval Service

Owns hybrid legal search.

## Current MVP

- `StagingRetrievalService.search()` supports `lexical`, `semantic` and `hybrid` modes.
- Lexical search matches staging SQLite statute/book/judgment text.
- Semantic search uses local deterministic hash embeddings stored in `staging_embeddings`.
- Build local staging embeddings with:

```powershell
python .\scripts\build_staging_embeddings.py
```

This local hash embedding layer is only an MVP fallback. Production should use PostgreSQL
full-text search, pgvector embeddings and reranking.

## Retrieval Sources

- statute sections and legal provisions
- BNS offence catalog
- judgment chunks
- case facts
- legal book chunks
- private case chunks

## Ranking Signals

- exact section/article match
- court authority
- jurisdiction
- date
- citation count
- overruled/distinguished status
- semantic similarity
- issue/domain match

