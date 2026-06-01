# Services

Domain services for the platform.

```text
services/ingestion        Source download and provenance.
services/document-ai      PDF/OCR/text extraction.
services/legal-extraction Structured statute, offence and judgment extraction.
services/retrieval        Hybrid search, embeddings and reranking.
services/chat             RAG answer generation.
services/case-intake      Private user case-file analysis.
services/review           Lawyer/admin review workflows.
services/compliance       Consent, retention, audit and safety checks.
```

These folders define service ownership. Current executable code still lives mostly in `legal_db/` and `scripts/`; move it into services as the product hardens.

