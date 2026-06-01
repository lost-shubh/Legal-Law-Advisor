# Compliance Guardrails

This is not legal advice. It is a technical checklist for building a legal information platform responsibly.

## Product Positioning

The platform should say:

- It provides legal information, research assistance and case preparation support.
- It is not a substitute for a licensed advocate.
- User-facing drafts should be reviewed by an advocate before filing.

## Private Data

User case files may contain sensitive personal data, criminal allegations, medical details, financial information, minors' information and identity documents.

Minimum controls:

- explicit upload consent
- purpose notice
- encryption at rest
- private case-level access control
- retention period
- delete/export request flow
- no default training on private files
- audit logs for file access and AI extraction

## Scraping Ethics

- Use official sources.
- Respect rate limits.
- Do not bypass CAPTCHA or access controls.
- Store source URL and fetch timestamp.
- Keep canary checks for source drift.

## User-Facing Legal Safety

The answer engine should:

- cite laws and judgments used
- separate facts from assumptions
- show confidence and missing information
- flag urgent situations such as arrest, violence, threats or limitation deadlines
- recommend advocate/legal aid review before action

