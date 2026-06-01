# First 1000 Cases Plan

The first dataset should be balanced and useful for product validation, not random.

## Target Mix

| Domain | Count | Sources |
| --- | ---: | --- |
| Bail and criminal procedure | 150 | SC, HCs, selected district orders |
| Cheque bounce / NI Act Section 138 | 150 | SC, HCs, district courts |
| Matrimonial and divorce | 120 | HCs, family courts where public |
| Domestic violence | 80 | HCs, district courts |
| Property and civil disputes | 120 | HCs, district courts |
| Consumer disputes | 100 | Consumer commissions, HCs |
| Cyber and IT Act | 80 | SC, Delhi HC, Karnataka HC, other HCs |
| Motor accident claims | 80 | HCs, MACT orders where public |
| Labour and employment | 70 | SC, HCs, tribunals where public |
| Writ and constitutional | 50 | SC, HCs |

## Per-Case Required Fields

- official source URL
- court and court level
- case number or CNR
- decision date
- judge/coram
- parties
- PDF hash
- raw text and clean text
- acts and sections cited
- legal issues
- outcome
- extracted facts
- evidence discussed
- citations

## Sampling Rule

For each domain, keep a mix of:

- Supreme Court decisions for binding precedent
- High Court decisions for state-level interpretation
- district court orders/judgments for factual and procedural patterns

## Acceptance Criteria

Before using the first 1000 cases in user-facing search:

- 95 percent of PDFs have source URL and hash.
- 90 percent of judgments have clean text above 500 words.
- 90 percent of AI-extracted outcomes pass manual spot checks.
- 90 percent of section references resolve to a statute/section or are marked unresolved.
- Every record has provenance.

