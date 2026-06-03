# Legal Extraction Service

Owns structured legal intelligence extraction.

## Responsibilities

- BNS offence catalog extraction
- Constitution article extraction
- rules/regulations/schedule extraction
- Acts and sections cited in judgments
- issues, facts, evidence, arguments, reasoning and outcomes
- citation context classification

Every extraction run must store model name, prompt version and validation status.

## Current MVP

- Local model: `local-rule-extractor-v1`
- Prompt version: `judgment_v1`
- CLI:

```powershell
python .\scripts\extract_staging_judgments.py
python .\scripts\extract_staging_judgments.py --status
```

- API:
  - `GET /v1/models/extraction`
  - `GET /v1/extractions/status`
  - `POST /v1/extractions/judgments`

The local model is deterministic and credential-free. It is suitable for staging metadata and backend wiring, not final legal interpretation.

