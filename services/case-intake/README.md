# Case Intake Service

Owns private user case-file processing.

## Pipeline

```text
upload
-> virus/type/size checks
-> OCR/text extraction
-> private case index
-> entity/date/event extraction
-> timeline
-> issue classification
-> evidence map
-> similar judgment retrieval
-> lawyer-ready brief
```

Private user files must remain separated from public training data unless explicit consent and anonymization are implemented.

## Current MVP Path

The API routes `POST /v1/cases/analyze` and `POST /v1/cases/brief` implement the first version:

```text
case text
-> deterministic issue/date/evidence detection
-> missing document checklist
-> related corpus retrieval
-> optional Ollama intake note
-> deterministic research brief and Markdown export
```

Set `use_llm=false` for deterministic retrieval-only testing. Set `use_llm=true` to use the configured local Ollama model.
