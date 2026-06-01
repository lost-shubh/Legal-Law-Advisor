# Schema Notes

## Public Corpus

Core public tables:

- `data_sources`
- `source_documents`
- `courts`
- `statutes`
- `sections`
- `gazette_notifications`
- `cases`
- `judgments`

These tables represent the official legal corpus and every row should have provenance wherever possible.

## Extracted Intelligence

Derived tables:

- `case_sections`
- `case_issues`
- `case_facts`
- `outcomes`
- `case_citations`
- `citations`
- `citation_strings`
- `embeddings`

These are not source-of-truth tables. They are extracted from official material and must track model/version/validation where AI is used.

## Private User Case Data

Private tables:

- `private_cases`
- `private_case_files`
- `private_case_analysis`

These are intentionally separate from public judgments and statutes. They should have stronger access control, retention, deletion and consent policies.

## Training Data Boundary

Public statutes, official judgments and official notifications can support legal model training or retrieval.

Private user files should be used for private RAG within that user's case only unless explicit consent and anonymization are implemented.

