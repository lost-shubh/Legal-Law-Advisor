# Database Architecture

## Main Groups

```text
source/provenance
courts/cases/judgments
statutes/provisions/offences
books/manuals/reports
extracted intelligence
search/embeddings
private user cases
quality/operations
corpus targets
```

## Critical Tables

- `source_documents`: every downloaded PDF/HTML/JSON with hash and source URL
- `statutes`: Acts and legal instruments
- `sections`: statute sections
- `legal_provisions`: articles, rules, regulations, schedules and clauses
- `criminal_offences`: BNS/offence/charge metadata
- `cases`: case metadata
- `judgments`: judgment/order text and PDF metadata
- `case_facts`: extracted facts, timeline and reasoning
- `embeddings`: vector search records
- `private_cases`: user-uploaded case workspace

## Separation Rule

Public legal corpus and private user case data are separate by design.

