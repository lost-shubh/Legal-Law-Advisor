-- Backward-compatible production migration for auditable PDF page locators.
ALTER TABLE judgments ADD COLUMN IF NOT EXISTS page_spans_json JSONB;
