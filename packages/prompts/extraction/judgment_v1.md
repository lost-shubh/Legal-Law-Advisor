# Judgment Extraction Prompt v1

Extract structured fields from an Indian court judgment.

Return valid JSON only:

```json
{
  "acts_cited": [],
  "sections_cited": [],
  "issue_tags": [],
  "dispute_summary": null,
  "timeline": [],
  "allegations": null,
  "defence": null,
  "evidence_discussed": null,
  "key_arguments": null,
  "reasoning": null,
  "outcome": "UNKNOWN",
  "citations": []
}
```

Do not infer facts unsupported by text.

