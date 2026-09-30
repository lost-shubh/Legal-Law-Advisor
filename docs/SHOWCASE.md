# Legal Law Advisor — Project Showcase

## One-line description

An evidence-first Indian legal intelligence platform that turns official statutes,
judgments and notifications into searchable, citation-aware and reviewable research.

## What a visitor can verify

1. `/health` shows the API state.
2. `/docs` exposes the FastAPI contract.
3. `/v1/search` demonstrates lexical, semantic and hybrid retrieval.
4. `/v1/verified-research` demonstrates evidence IDs, claim support and abstention.
5. `/v1/similar-cases` demonstrates case-law discovery.
6. `/v1/admin/overview` exposes corpus, model, ingestion and quality status.

## Technical differentiators

- Official-source provenance and content hashing.
- Hybrid PDF/OCR extraction with quality and confidence gates.
- SQLite staging and PostgreSQL/pgvector production paths.
- Reciprocal-rank fusion across lexical and semantic retrieval.
- Case-law citation graph and similar-case retrieval.
- Local Ollama support for privacy-conscious development.
- Claim-level evidence checks before text is labelled verified.
- Explicit abstention when evidence is missing or insufficient.

## Honest scope

This is an actively developed MVP foundation, not a replacement for legal advice. The
current evidence checker is a conservative lexical support gate; the next research step is
legal entailment/reranking trained and evaluated on an Indian legal benchmark.

## Suggested five-minute demo

1. Start Docker services and the FastAPI server.
2. Open `/docs` and run `/health`.
3. Run `/v1/search` with `mode=hybrid`.
4. Run `/v1/verified-research` with `use_llm=false` to inspect evidence safely.
5. Repeat with `use_llm=true` if Ollama is available.
6. Show `/v1/similar-cases` and `/v1/admin/overview`.
