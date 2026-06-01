# Model Architecture

## Core Principle

The LLM is not the database. The LLM is an interface over verified legal data.

## Components

```text
classifier
retriever
reranker
answer model
extraction model
safety checker
human reviewer
```

## MVP Models

- Chat UX: Ollama `llama3.2:3b`
- Embeddings: `text-embedding-3-small` or local multilingual embedding model
- Extraction: stronger hosted model or larger local model
- Reranking: add after corpus grows

## Answer Flow

```text
question
-> classify domain/jurisdiction
-> retrieve laws, judgments, books and private chunks
-> rerank
-> generate sourced answer
-> safety check
-> return with citations and advocate-review warning
```

## Training Strategy

Use:

- public official legal material for legal corpus
- private user documents only for private RAG
- anonymized/consented lawyer-reviewed corrections for future fine-tuning

Do not train globally on private case files by default.

