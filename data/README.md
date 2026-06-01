# Local Data Directory

This directory is for local generated data.

Ignored by git:

- `raw/` official PDFs and HTML pages
- `processed/` extracted/intermediate data
- `tmp/` temporary downloads
- `*.sqlite` staging databases

The current local staging database is:

```text
data/legal_corpus_staging.sqlite
```

Raw legal PDFs and HTML files are stored in:

```text
data/raw
```

Use `manifests/ingestion_summary.json` to see the committed summary of what has been loaded locally.

