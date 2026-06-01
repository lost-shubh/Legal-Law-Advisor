# Pipeline Architecture

## Public Corpus Pipeline

```text
official source
-> polite fetcher
-> source_documents
-> object storage
-> PDF/text/OCR extraction
-> clean text
-> structured extraction
-> validation
-> embeddings
-> search/ranking
```

## Sources

- India Code
- e-Gazette
- Supreme Court
- High Courts
- eCourts
- Law Commission
- CBSE/legal manuals
- NALSA/legal aid material

## Private Case Pipeline

```text
user upload
-> private_cases/private_case_files
-> OCR/text extraction
-> private chunks
-> timeline extraction
-> issue detection
-> evidence map
-> similar public case retrieval
-> lawyer-ready brief
-> advocate review
```

Private case data must not enter public model training by default.

## Implemented Local Case-Text Pipeline

```text
case text
-> legal_db.case_intake.analyzer
-> issue tags, dates, evidence categories, missing documents
-> staging corpus retrieval
-> legal_db.case_intake.pipeline.CaseIntakePipeline
-> optional Ollama note using configured local model
```

This is the current bridge between user case facts and the public legal corpus. File upload/OCR/private chunk storage still belongs in the later private case pipeline.
