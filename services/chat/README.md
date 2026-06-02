# Chat Service

Owns RAG answer generation.

## Pipeline

```text
question
-> classify domain and jurisdiction
-> retrieve sources
-> rerank
-> build context
-> generate answer
-> safety check
-> cite sources
```

Local MVP model target: `llama3.2:3b` through Ollama, with `llama3.2:1b` as the lower-memory fallback.

The chat model must not answer legal questions without retrieved source context.
