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

Local MVP model: `llama3.2:3b` through Ollama.

The chat model must not answer legal questions without retrieved source context.

