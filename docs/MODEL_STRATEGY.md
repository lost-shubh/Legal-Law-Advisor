# Model Strategy

The platform should not rely on a small chatbot model alone. Legal accuracy comes from retrieval, citations and validation.

## Recommended Architecture

1. **Retrieval corpus**
   - statutes, sections, articles, rules and schedules
   - BNS offence catalog
   - judgments and extracted case facts
   - legal books, manuals and Law Commission reports

2. **Search**
   - PostgreSQL full-text search for exact legal terms and section numbers
   - vector search for semantic similarity
   - reranking before answer generation

3. **Answer model**
   - use a local Ollama model for early chatbot UX
   - use stronger models for extraction and high-risk legal reasoning
   - always cite retrieved sources

4. **Human review**
   - advocate review for drafts, filings, evidence strategy and urgent matters

## Local Chatbot Model

On this machine, Ollama is installed. The latest local check showed this installed model:

```text
llama3.2:3b
```

The project is configured to prefer `llama3.2:3b` because that is the local model actually installed on this machine. The earlier `llama3.2:2b` target is not a valid/available Ollama tag in this environment. If `llama3.2:3b` cannot be loaded, the API checks installed fallback models listed in `OLLAMA_FALLBACK_MODELS`, currently `llama3.2:1b`.

The repository includes a prototype local chat command:

```powershell
python .\scripts\chat_local.py "What are the basic features of the Constitution of India?" --context-limit 1
```

That command retrieves local legal-book chunks and sends them to Ollama.

I would not use it as the sole legal reasoning engine. It is suitable for:

- simple legal Q&A over retrieved context
- explaining legal terms
- summarizing uploaded text
- conversational UX

It is not suitable by itself for:

- final legal advice
- predicting case outcomes
- drafting court filings without review
- extracting complex judgment ratios at scale

## Llama Version Conflict Resolution

GitHub issue #1 reported that the Llama model pipeline was not syncing properly with the main legal database for the built-in chatbot. The fix is:

- default to the installed model: `llama3.2:3b`
- keep a smaller fallback: `llama3.2:1b`
- expose combined chat readiness through `GET /v1/chat/status`
- keep the chatbot retrieval-first through `LocalLegalRagPipeline`

The integration is configurable through:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_FALLBACK_MODELS=llama3.2:1b
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_MAX_ANSWER_TOKENS=350
OLLAMA_CONTEXT_WINDOW=4096
OLLAMA_NUM_THREAD=0
```

Check what the API will use:

```powershell
python .\scripts\ollama_status.py
```

Check whether the chatbot is ready to answer from the legal corpus:

```text
GET /v1/chat/status
```

CLI equivalent:

```powershell
python .\scripts\chatbot_status.py
```

## Local Model Usage Pattern

The local model should be used after retrieval, not as a raw free-form legal advisor:

```text
case text or user question
-> deterministic intake/classification
-> retrieve sections, cases, book chunks and BNS offence data
-> pass compact context to Ollama
-> generate an explanatory note with safety limits
```

The model settings are tuned for local use:

- `keep_alive=30m` keeps the model loaded between requests.
- `num_ctx=4096` gives enough room for retrieved legal context on a small model.
- `num_predict=350` keeps answers concise and lowers latency.
- `temperature=0.2` reduces creative drift in legal explanations.
- `OLLAMA_NUM_THREAD=0` lets Ollama choose thread usage; set it manually if the laptop needs tuning.

## Embedding Model

Current local MVP:

- `scripts/build_staging_embeddings.py` builds deterministic hash embeddings for parsed judgment chunks in the staging SQLite DB.
- `POST /v1/search` accepts `mode: "semantic"` or `mode: "hybrid"`.
- This path needs no OpenAI key and keeps tests/local demos working before PostgreSQL/pgvector is available.

For MVP:

- hosted: `text-embedding-3-small`
- local option: `nomic-embed-text` or a multilingual BGE embedding model

For Indian law, multilingual support matters because future material may include Hindi and state-language documents.

## Extraction Model

Current local MVP:

- `local-rule-extractor-v1` runs without hosted credentials.
- `scripts/extract_staging_judgments.py` stores staging outputs in SQLite `staging_extractions`.
- `GET /v1/models/extraction` reports local and hosted extraction model availability.
- `GET /v1/extractions/status` reports staging extraction counts.
- `POST /v1/extractions/judgments` runs the local extraction model over parsed staging judgments.

The local extractor is deterministic and suitable for backend wiring, tests and first-pass metadata. It should not be treated as final legal interpretation. Production extraction should use a stronger hosted or larger local model, validation rules and human review for high-impact fields.

## Production Direction

Production should support model swapping:

- local Ollama model for low-cost chat
- stronger hosted model for extraction and complex reasoning
- separate embedding model
- separate reranker

The answer pipeline should be:

```text
user question
-> classify legal domain
-> retrieve statutes/judgments/books/user case chunks
-> rerank
-> generate answer with citations
-> safety checks
-> advocate review where needed
```
