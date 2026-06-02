CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS data_sources (
  id BIGSERIAL PRIMARY KEY,
  source_code TEXT UNIQUE NOT NULL,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN (
    'STATUTE', 'GAZETTE', 'JUDGMENT', 'CASE_STATUS', 'COURT_METADATA', 'REFERENCE'
  )),
  base_url TEXT NOT NULL,
  jurisdiction TEXT,
  is_official BOOLEAN DEFAULT TRUE,
  scrape_delay_seconds INTEGER DEFAULT 3,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courts (
  id BIGSERIAL PRIMARY KEY,
  court_code TEXT UNIQUE NOT NULL,
  court_name TEXT NOT NULL,
  court_level TEXT NOT NULL CHECK (court_level IN (
    'SUPREME', 'HIGH', 'DISTRICT', 'TRIBUNAL', 'FORUM', 'COMMISSION'
  )),
  state TEXT,
  district TEXT,
  ecourts_state_code TEXT,
  ecourts_district_code TEXT,
  source_id BIGINT REFERENCES data_sources(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_documents (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES data_sources(id),
  source_url TEXT NOT NULL,
  canonical_url TEXT,
  document_type TEXT NOT NULL CHECK (document_type IN (
    'ACT_HTML', 'ACT_PDF', 'SECTION_HTML', 'GAZETTE_PDF', 'JUDGMENT_PDF',
    'ORDER_PDF', 'BOOK_PDF', 'TEXTBOOK_PDF', 'REPORT_PDF', 'MANUAL_PDF',
    'CASE_STATUS_JSON', 'HTML_PAGE', 'OTHER'
  )),
  s3_key TEXT,
  local_path TEXT,
  content_hash TEXT,
  mime_type TEXT,
  byte_size BIGINT,
  http_status INTEGER,
  fetched_at TIMESTAMPTZ,
  parse_status TEXT DEFAULT 'PENDING' CHECK (parse_status IN (
    'PENDING', 'PARSED', 'FAILED', 'SKIPPED'
  )),
  error_msg TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source_url, content_hash)
);

CREATE TABLE IF NOT EXISTS statutes (
  id BIGSERIAL PRIMARY KEY,
  act_name TEXT NOT NULL,
  short_title TEXT,
  year INTEGER,
  jurisdiction TEXT DEFAULT 'CENTRAL',
  source_id BIGINT REFERENCES data_sources(id),
  source_url TEXT,
  india_code_id TEXT UNIQUE,
  is_in_force BOOLEAN DEFAULT TRUE,
  commenced_on DATE,
  repealed_on DATE,
  content_hash TEXT,
  last_fetched TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(act_name, year, jurisdiction)
);

CREATE TABLE IF NOT EXISTS sections (
  id BIGSERIAL PRIMARY KEY,
  statute_id BIGINT NOT NULL REFERENCES statutes(id) ON DELETE CASCADE,
  section_number TEXT NOT NULL,
  section_title TEXT,
  section_text TEXT,
  effective_from DATE,
  effective_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  content_hash TEXT,
  source_document_id BIGINT REFERENCES source_documents(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(statute_id, section_number, effective_from)
);

CREATE TABLE IF NOT EXISTS legal_provisions (
  id BIGSERIAL PRIMARY KEY,
  statute_id BIGINT NOT NULL REFERENCES statutes(id) ON DELETE CASCADE,
  provision_kind TEXT NOT NULL CHECK (provision_kind IN (
    'SECTION', 'ARTICLE', 'RULE', 'REGULATION', 'SCHEDULE', 'ORDER', 'CLAUSE'
  )),
  provision_number TEXT NOT NULL,
  provision_title TEXT,
  provision_text TEXT,
  parent_provision_id BIGINT REFERENCES legal_provisions(id),
  effective_from DATE,
  effective_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  source_document_id BIGINT REFERENCES source_documents(id),
  content_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(statute_id, provision_kind, provision_number, effective_from)
);

CREATE TABLE IF NOT EXISTS criminal_offences (
  id BIGSERIAL PRIMARY KEY,
  statute_id BIGINT NOT NULL REFERENCES statutes(id),
  section_id BIGINT REFERENCES sections(id),
  provision_id BIGINT REFERENCES legal_provisions(id),
  offence_code TEXT NOT NULL,
  offence_title TEXT,
  offence_text TEXT,
  ingredients JSONB,
  punishment_text TEXT,
  imprisonment_min_months INTEGER,
  imprisonment_max_months INTEGER,
  fine_text TEXT,
  cognizable_status TEXT,
  bailable_status TEXT,
  compoundable_status TEXT,
  triable_by TEXT,
  related_procedure_sections JSONB,
  related_evidence_sections JSONB,
  source TEXT DEFAULT 'STATUTE_EXTRACTED',
  validation_status TEXT DEFAULT 'UNVALIDATED' CHECK (validation_status IN (
    'UNVALIDATED', 'AUTO_VALIDATED', 'HUMAN_VALIDATED', 'REJECTED'
  )),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(statute_id, offence_code)
);

CREATE TABLE IF NOT EXISTS gazette_notifications (
  id BIGSERIAL PRIMARY KEY,
  gazette_number TEXT,
  part TEXT,
  series TEXT,
  ministry TEXT,
  notification_date DATE,
  subject TEXT,
  act_name TEXT,
  statute_id BIGINT REFERENCES statutes(id),
  sections_affected TEXT[],
  notification_type TEXT CHECK (notification_type IN (
    'COMMENCEMENT', 'AMENDMENT', 'REPEAL', 'RULES', 'REGULATION', 'ORDER', 'OTHER'
  )),
  source_document_id BIGINT REFERENCES source_documents(id),
  pdf_s3_key TEXT,
  full_text TEXT,
  extraction_status TEXT DEFAULT 'PENDING',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legal_books (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  material_type TEXT NOT NULL CHECK (material_type IN (
    'TEXTBOOK', 'REPORT', 'HANDBOOK', 'MANUAL', 'GUIDE', 'COMMENTARY', 'OTHER'
  )),
  source_code TEXT REFERENCES data_sources(source_code),
  jurisdiction TEXT DEFAULT 'INDIA',
  subject_tags TEXT[],
  source_url TEXT NOT NULL,
  source_document_id BIGINT REFERENCES source_documents(id),
  content_hash TEXT,
  rights_note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(title, source_url)
);

CREATE TABLE IF NOT EXISTS book_chapters (
  id BIGSERIAL PRIMARY KEY,
  book_id BIGINT NOT NULL REFERENCES legal_books(id) ON DELETE CASCADE,
  chapter_number TEXT,
  chapter_title TEXT,
  start_char INTEGER,
  end_char INTEGER,
  chapter_text TEXT,
  content_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_id, chapter_number, chapter_title)
);

CREATE TABLE IF NOT EXISTS book_chunks (
  id BIGSERIAL PRIMARY KEY,
  book_id BIGINT NOT NULL REFERENCES legal_books(id) ON DELETE CASCADE,
  chapter_id BIGINT REFERENCES book_chapters(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  word_count INTEGER,
  content_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_id, chapter_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS cases (
  id BIGSERIAL PRIMARY KEY,
  cnr_number TEXT UNIQUE,
  case_number TEXT,
  neutral_citation TEXT,
  court_id BIGINT REFERENCES courts(id),
  case_type TEXT,
  filing_date DATE,
  decision_date DATE,
  status TEXT CHECK (status IN (
    'PENDING', 'DECIDED', 'DISPOSED', 'TRANSFERRED', 'UNKNOWN'
  )),
  judge_names TEXT[],
  petitioner TEXT,
  respondent TEXT,
  advocates JSONB,
  source_url TEXT,
  source_document_id BIGINT REFERENCES source_documents(id),
  citation_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_citations (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  citation TEXT NOT NULL,
  reporter TEXT,
  year INTEGER,
  volume TEXT,
  page TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(case_id, citation)
);

CREATE TABLE IF NOT EXISTS judgments (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  court_id BIGINT REFERENCES courts(id),
  judgment_date DATE,
  judge_names TEXT[],
  judgment_type TEXT CHECK (judgment_type IN (
    'FINAL', 'INTERIM', 'ORDER', 'BAIL', 'REVISION', 'APPEAL', 'UNKNOWN'
  )),
  language TEXT DEFAULT 'en',
  pdf_url TEXT,
  s3_key TEXT,
  pdf_hash TEXT UNIQUE,
  raw_text TEXT,
  clean_text TEXT,
  text_extraction_method TEXT CHECK (text_extraction_method IN (
    'PDF_TEXT', 'OCR', 'MIXED', 'MANUAL', 'UNKNOWN'
  )),
  ocr_quality NUMERIC(4,3),
  page_count INTEGER,
  word_count INTEGER,
  source_document_id BIGINT REFERENCES source_documents(id),
  extraction_status TEXT DEFAULT 'PENDING' CHECK (extraction_status IN (
    'PENDING', 'DONE', 'FAILED', 'SKIPPED', 'NEEDS_REVIEW'
  )),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_sections (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  statute_id BIGINT REFERENCES statutes(id),
  section_id BIGINT REFERENCES sections(id),
  raw_act_name TEXT,
  raw_section_number TEXT,
  mention_type TEXT CHECK (mention_type IN (
    'CHARGED_UNDER', 'APPLIED', 'REFERRED', 'INTERPRETED', 'UNKNOWN'
  )),
  confidence NUMERIC(4,3),
  source TEXT DEFAULT 'AI_EXTRACTED',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_issues (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  issue_tag TEXT NOT NULL,
  confidence NUMERIC(4,3),
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(case_id, issue_tag)
);

CREATE TABLE IF NOT EXISTS case_facts (
  id BIGSERIAL PRIMARY KEY,
  judgment_id BIGINT REFERENCES judgments(id) ON DELETE CASCADE,
  dispute_summary TEXT,
  timeline JSONB,
  allegations TEXT,
  defence TEXT,
  evidence_discussed TEXT,
  key_arguments TEXT,
  reasoning TEXT,
  ratio_summary TEXT,
  validation_status TEXT DEFAULT 'UNVALIDATED' CHECK (validation_status IN (
    'UNVALIDATED', 'AUTO_VALIDATED', 'HUMAN_VALIDATED', 'REJECTED'
  )),
  extracted_at TIMESTAMPTZ,
  model_used TEXT,
  model_version TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  judgment_id BIGINT REFERENCES judgments(id) ON DELETE CASCADE,
  result TEXT CHECK (result IN (
    'ALLOWED', 'DISMISSED', 'PARTLY_ALLOWED', 'CONVICTED', 'ACQUITTED',
    'BAIL_GRANTED', 'BAIL_REJECTED', 'SETTLED', 'REMANDED', 'COMPENSATION_AWARDED',
    'UNKNOWN'
  )),
  compensation NUMERIC,
  sentence TEXT,
  conditions TEXT,
  confidence NUMERIC(4,3),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS citations (
  id BIGSERIAL PRIMARY KEY,
  citing_case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  cited_case_id BIGINT REFERENCES cases(id) ON DELETE CASCADE,
  citation_text TEXT NOT NULL,
  citation_type TEXT CHECK (citation_type IN (
    'FOLLOWED', 'DISTINGUISHED', 'OVERRULED', 'REFERRED', 'RELIED_ON', 'UNKNOWN'
  )),
  context_text TEXT,
  confidence NUMERIC(4,3),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(citing_case_id, cited_case_id, citation_text)
);

CREATE TABLE IF NOT EXISTS citation_strings (
  id BIGSERIAL PRIMARY KEY,
  citation_text TEXT UNIQUE NOT NULL,
  case_id BIGINT REFERENCES cases(id),
  normalized_text TEXT,
  reporter TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS embeddings (
  id BIGSERIAL PRIMARY KEY,
  source_type TEXT NOT NULL CHECK (source_type IN (
    'JUDGMENT_CHUNK', 'SECTION', 'LEGAL_PROVISION', 'CRIMINAL_OFFENCE',
    'BOOK_CHUNK', 'CASE_FACT', 'GAZETTE_NOTIFICATION', 'PRIVATE_CASE_CHUNK'
  )),
  source_id BIGINT NOT NULL,
  chunk_index INTEGER DEFAULT 0,
  chunk_text TEXT,
  embedding vector(1536),
  model_name TEXT NOT NULL,
  model_version TEXT,
  content_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source_type, source_id, chunk_index, model_name)
);

CREATE TABLE IF NOT EXISTS scrape_log (
  id BIGSERIAL PRIMARY KEY,
  url TEXT NOT NULL,
  http_status INTEGER,
  bytes BIGINT,
  scraped_at TIMESTAMPTZ DEFAULT NOW(),
  source_name TEXT,
  error_msg TEXT
);

CREATE TABLE IF NOT EXISTS extraction_runs (
  id BIGSERIAL PRIMARY KEY,
  target_type TEXT NOT NULL,
  target_id BIGINT NOT NULL,
  model_name TEXT,
  model_version TEXT,
  prompt_version TEXT,
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'DONE', 'FAILED', 'SKIPPED')),
  validation_status TEXT DEFAULT 'UNVALIDATED',
  error_msg TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS section_mappings (
  id BIGSERIAL PRIMARY KEY,
  old_statute_id BIGINT REFERENCES statutes(id),
  old_section TEXT,
  new_statute_id BIGINT REFERENCES statutes(id),
  new_section TEXT,
  mapping_type TEXT CHECK (mapping_type IN ('REPLACED_BY', 'SPLIT_INTO', 'MERGED_WITH', 'SIMILAR_TO')),
  notes TEXT,
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS private_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_user_id TEXT NOT NULL,
  jurisdiction TEXT DEFAULT 'INDIA',
  case_title TEXT,
  consent_for_training BOOLEAN DEFAULT FALSE,
  anonymization_status TEXT DEFAULT 'NOT_STARTED' CHECK (anonymization_status IN (
    'NOT_STARTED', 'DONE', 'FAILED', 'NOT_REQUIRED'
  )),
  retention_until DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS private_case_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  private_case_id UUID REFERENCES private_cases(id) ON DELETE CASCADE,
  original_filename TEXT,
  document_type TEXT,
  s3_key TEXT,
  file_hash TEXT,
  extracted_text TEXT,
  clean_text TEXT,
  extraction_method TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS private_case_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  private_case_id UUID REFERENCES private_cases(id) ON DELETE CASCADE,
  timeline JSONB,
  issue_tags TEXT[],
  evidence_map JSONB,
  missing_documents JSONB,
  similar_public_case_ids BIGINT[],
  model_used TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS corpus_targets (
  id BIGSERIAL PRIMARY KEY,
  target_code TEXT UNIQUE NOT NULL,
  target_name TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN (
    'STATUTE', 'JUDGMENT', 'CASE', 'GAZETTE', 'OFFENCE_CATALOG', 'EMBEDDING'
  )),
  court_level TEXT,
  jurisdiction TEXT,
  domain_tag TEXT,
  target_count INTEGER NOT NULL,
  priority INTEGER DEFAULT 100,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS collection_batches (
  id BIGSERIAL PRIMARY KEY,
  batch_code TEXT UNIQUE NOT NULL,
  target_code TEXT REFERENCES corpus_targets(target_code),
  source_code TEXT REFERENCES data_sources(source_code),
  status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN (
    'PLANNED', 'RUNNING', 'DONE', 'FAILED', 'PAUSED'
  )),
  planned_count INTEGER,
  collected_count INTEGER DEFAULT 0,
  from_date DATE,
  to_date DATE,
  court_codes TEXT[],
  domain_tags TEXT[],
  notes TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
  id BIGSERIAL PRIMARY KEY,
  job_code TEXT UNIQUE NOT NULL,
  job_type TEXT NOT NULL,
  source_code TEXT REFERENCES data_sources(source_code),
  source_url TEXT,
  status TEXT NOT NULL CHECK (status IN (
    'PENDING', 'RUNNING', 'DONE', 'FAILED', 'PAUSED', 'SKIPPED'
  )),
  target_count INTEGER DEFAULT 0,
  processed_count INTEGER DEFAULT 0,
  success_count INTEGER DEFAULT 0,
  failed_count INTEGER DEFAULT 0,
  skipped_count INTEGER DEFAULT 0,
  metadata JSONB,
  error_msg TEXT,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ingestion_items (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
  item_key TEXT NOT NULL,
  item_type TEXT NOT NULL,
  source_url TEXT,
  status TEXT NOT NULL CHECK (status IN (
    'PENDING', 'RUNNING', 'DONE', 'FAILED', 'SKIPPED', 'DUPLICATE'
  )),
  local_path TEXT,
  s3_key TEXT,
  content_hash TEXT,
  source_document_id BIGINT REFERENCES source_documents(id),
  metadata JSONB,
  error_msg TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(job_id, item_key)
);

CREATE TABLE IF NOT EXISTS quality_metrics (
  id BIGSERIAL PRIMARY KEY,
  metric_name TEXT NOT NULL,
  metric_scope TEXT,
  numerator INTEGER,
  denominator INTEGER,
  score NUMERIC(6,4),
  sample_ids BIGINT[],
  measured_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS canary_checks (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT REFERENCES data_sources(id),
  url TEXT NOT NULL,
  expected_pattern TEXT,
  last_status TEXT CHECK (last_status IN ('PASS', 'FAIL', 'UNKNOWN')),
  last_checked_at TIMESTAMPTZ,
  error_msg TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
