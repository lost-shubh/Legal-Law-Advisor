# Runbook

## Daily Jobs

- scrape new Supreme Court judgments
- scrape selected High Court judgments
- check e-Gazette updates
- process queued OCR jobs
- run AI extraction on clean judgments
- log failed fetches and parser errors

## Weekly Jobs

- run quality SQL checks
- manually spot-check 20 judgments
- retry low-quality OCR records
- retry failed extraction jobs
- update citation counts
- run source canary checks

## Monthly Jobs

- re-check India Code priority Acts for amendments
- update section mappings such as IPC to BNS
- review overruled/distinguished citation classifications
- re-embed records whose clean text changed
- archive old raw files according to storage policy

## Quality SQL

Generate check SQL:

```powershell
python -m legal_db.cli quality-sql
```

## OCR One PDF

```powershell
python -m legal_db.cli extract-pdf path\to\judgment.pdf --lang eng+hin
```

## Citation Parse One Text File

```powershell
python -m legal_db.cli parse-citations path\to\judgment.txt
```

