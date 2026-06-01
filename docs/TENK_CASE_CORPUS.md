# 10,000 Judgment Corpus Target

The current local database is a seed corpus. A serious Legal Law Advisor needs a much larger judgment corpus before it can make useful similarity claims.

## Target

Minimum production corpus:

- 10,000 judgments/orders with official provenance
- 16 priority Acts with provision extraction
- BNS offence catalog with charge/offence metadata
- OCR/text extraction for every PDF
- extracted facts, issues, evidence, outcomes and citations
- embeddings for sections, judgment chunks and case summaries

## Judgment Mix

| Source Level | Target | Why |
| --- | ---: | --- |
| Supreme Court | 2,000 | Binding precedent and authoritative interpretation |
| High Courts | 5,000 | State-level binding and persuasive precedent |
| District Courts | 3,000 | Factual and procedural patterns from disposed public matters |

District court data must be limited to public metadata and public orders/judgments. Do not assume pleadings, FIRs, witness statements or evidence bundles are public.

## Domain Mix

| Domain | Target |
| --- | ---: |
| Criminal bail/trial/appeal | 1,800 |
| Cheque bounce / NI Act 138 | 900 |
| Family/divorce/maintenance/custody | 900 |
| Domestic violence | 500 |
| Property/civil possession/title | 900 |
| Consumer | 700 |
| Cyber / IT Act | 500 |
| Motor accident / insurance | 700 |
| Labour / employment | 600 |
| Constitutional / writ | 700 |
| Commercial / contract / arbitration | 800 |
| Tax / regulatory | 500 |

## BNS And Charge Database

For criminal workflows, storing BNS section text is not enough. The database needs a structured offence catalog:

- BNS section/offence code
- offence name/title
- ingredients of the offence
- punishment text
- imprisonment minimum and maximum where extractable
- fine text
- bailable/non-bailable status where available from procedure/schedules
- cognizable/non-cognizable status where available
- compoundable status where available
- triable court
- related BNSS procedure sections
- related BSA evidence provisions
- linked precedent interpreting that offence

The schema now includes `criminal_offences` for this.

## Articles, Sections, Rules

Use `legal_provisions` for generic legal material:

- Constitution Articles
- statute Sections
- Rules
- Regulations
- Schedules
- Orders
- Clauses

Use `sections` for direct statute-section compatibility with the existing pipeline.

## Progress Rule

Do not call the database production-ready until:

- 10,000 judgments are loaded
- 90 percent of judgment PDFs have clean text above 500 words
- 90 percent of sampled outcome extractions are correct
- 90 percent of section references resolve to known provisions
- every row has source URL, fetch timestamp and content hash

