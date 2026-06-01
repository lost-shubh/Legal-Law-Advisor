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

On this machine, Ollama is installed and the available local model is:

```text
llama3.2:3b
```

I would use `llama3.2:3b` for the first local chatbot integration because it is already installed and lightweight.
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
OLLAMA_MODEL=llama3.2:3b
```

If you install another Ollama model later, set `OLLAMA_MODEL` to that tag.

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
