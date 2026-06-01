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

The project is now configured to prefer `llama3.2:2b` because that is the target local chatbot model requested for the product. If `llama3.2:2b` is not installed, the API automatically falls back to installed models listed in `OLLAMA_FALLBACK_MODELS`, currently `llama3.2:3b,llama3.2:1b`.

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

## About `llama3.2:2b`

The local Ollama installation currently shows `llama3.2:3b`, not `llama3.2:2b`. The integration is configurable through:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:2b
OLLAMA_FALLBACK_MODELS=llama3.2:3b,llama3.2:1b
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_MAX_ANSWER_TOKENS=350
OLLAMA_CONTEXT_WINDOW=4096
OLLAMA_NUM_THREAD=0
```

Check what the API will use:

```powershell
python .\scripts\ollama_status.py
```

If `llama3.2:2b` is installed later, the API will select it automatically when `OLLAMA_MODEL=llama3.2:2b`.

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

For MVP:

- hosted: `text-embedding-3-small`
- local option: `nomic-embed-text` or a multilingual BGE embedding model

For Indian law, multilingual support matters because future material may include Hindi and state-language documents.

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
