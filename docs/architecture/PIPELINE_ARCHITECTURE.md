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

