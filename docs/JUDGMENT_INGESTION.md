# Judgment Ingestion

This is the first scalable path from the current starter corpus toward the 1,000 judgment MVP target.

## Why Manifest First

Court portals change frequently and often require source-specific selectors. The reliable first step is a manifest-based ingestion path:

```text
official PDF URL or local PDF
-> hash
-> store under data/raw/judgments
-> source_documents
-> cases
-> judgments
-> optional PDF text extraction
-> ingestion job/item status
```

This lets us collect verified official PDFs immediately while live scrapers are built source by source.

## Create A Manifest

```powershell
python .\scripts\ingest_judgments.py --init-template .\data\judgment_manifest.local.json
```

Edit the generated JSON and replace the example rows with official Supreme Court/e-SCR, High Court, or other court judgment PDFs.

Required fields:

```json
{
  "title": "Case title",
  "court_code": "SC",
  "source_code": "ESCR",
  "pdf_url": "https://official-source/judgment.pdf"
}
```

Use `local_pdf_path` instead of `pdf_url` when the official PDF has already been downloaded manually.

Recommended fields:

```json
{
  "case_number": "Civil Appeal No. 1234 of 2025",
  "neutral_citation": "2025 INSC 1234",
  "judgment_date": "2025-05-01",
  "judgment_type": "FINAL"
}
```

## Run Ingestion

Download PDFs and extract text:

```powershell
python .\scripts\ingest_judgments.py .\data\judgment_manifest.local.json
```

Store PDFs only:

```powershell
python .\scripts\ingest_judgments.py .\data\judgment_manifest.local.json --no-extract-text
```

Use already-downloaded local PDFs only:

```powershell
python .\scripts\ingest_judgments.py .\data\judgment_manifest.local.json --no-download
```

Limit a trial run:

```powershell
python .\scripts\ingest_judgments.py .\data\judgment_manifest.local.json --limit 10
```

## Check Status

CLI:

```powershell
python .\scripts\ingest_judgments.py --status
```

API:

```text
GET /v1/ingestion/status
```

The API returns job counts, item counts, and the 10 most recent ingestion jobs.

## Supreme Court/e-SCR Manifest Generator

The Supreme Court SCR portal is official, but its public search UI is dynamic and CAPTCHA-protected. For the MVP, use it to locate official result pages/PDFs, then generate a manifest from saved result HTML or directly accessible result pages.

Generate from saved HTML:

```powershell
python .\scripts\generate_sc_manifest.py `
  --html .\data\source_exports\scr_results_section_138.html `
  --output .\data\manifests\sc_escr_manifest.local.json `
  --limit 50
```

Generate from result URLs:

```powershell
python .\scripts\generate_sc_manifest.py `
  --url "https://scr.sci.gov.in/scrsearch/" `
  --output .\data\manifests\sc_escr_manifest.local.json
```

Then ingest the generated manifest:

```powershell
python .\scripts\ingest_judgments.py .\data\manifests\sc_escr_manifest.local.json --limit 25
```

The generator extracts:

- title
- Supreme Court court code
- source code `ESCR`
- neutral citation, for example `2025 INSC 77`
- case number where present
- judgment date where present
- official PDF URL
- source-page context metadata

## Next Source-Specific Scrapers

Build these after the manifest path is stable:

1. Delhi High Court official judgment parser.
2. Bombay High Court official judgment parser.
3. DOJ judgment search portal parser.

Each scraper should output the same manifest item shape before inserting anything. That keeps source parsing separate from storage, hashing, text extraction, and status tracking.
