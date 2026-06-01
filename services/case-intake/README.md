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

