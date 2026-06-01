CREATE INDEX IF NOT EXISTS idx_courts_level ON courts(court_level);
CREATE INDEX IF NOT EXISTS idx_courts_state ON courts(state);

CREATE INDEX IF NOT EXISTS idx_source_documents_source ON source_documents(source_id);
CREATE INDEX IF NOT EXISTS idx_source_documents_hash ON source_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_source_documents_status ON source_documents(parse_status);

CREATE INDEX IF NOT EXISTS idx_statutes_jurisdiction ON statutes(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_statutes_name ON statutes USING GIN (to_tsvector('english', coalesce(act_name, '')));

CREATE INDEX IF NOT EXISTS idx_sections_statute ON sections(statute_id);
CREATE INDEX IF NOT EXISTS idx_sections_current ON sections(statute_id, section_number) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_sections_fts ON sections
  USING GIN (to_tsvector('english', coalesce(section_text, '')));

CREATE INDEX IF NOT EXISTS idx_legal_provisions_statute ON legal_provisions(statute_id);
CREATE INDEX IF NOT EXISTS idx_legal_provisions_kind ON legal_provisions(provision_kind);
CREATE INDEX IF NOT EXISTS idx_legal_provisions_fts ON legal_provisions
  USING GIN (to_tsvector('english', coalesce(provision_text, '')));

CREATE INDEX IF NOT EXISTS idx_criminal_offences_statute ON criminal_offences(statute_id);
CREATE INDEX IF NOT EXISTS idx_criminal_offences_code ON criminal_offences(offence_code);
CREATE INDEX IF NOT EXISTS idx_criminal_offences_status ON criminal_offences(cognizable_status, bailable_status);
CREATE INDEX IF NOT EXISTS idx_criminal_offences_fts ON criminal_offences
  USING GIN (to_tsvector('english', coalesce(offence_title, '') || ' ' || coalesce(offence_text, '') || ' ' || coalesce(punishment_text, '')));

CREATE INDEX IF NOT EXISTS idx_gazette_statute ON gazette_notifications(statute_id);
CREATE INDEX IF NOT EXISTS idx_gazette_type_date ON gazette_notifications(notification_type, notification_date);

CREATE INDEX IF NOT EXISTS idx_legal_books_source ON legal_books(source_code, material_type);
CREATE INDEX IF NOT EXISTS idx_legal_books_subject_tags ON legal_books USING GIN(subject_tags);
CREATE INDEX IF NOT EXISTS idx_book_chapters_book ON book_chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_book_chunks_book ON book_chunks(book_id);
CREATE INDEX IF NOT EXISTS idx_book_chunks_fts ON book_chunks
  USING GIN (to_tsvector('english', coalesce(chunk_text, '')));

CREATE INDEX IF NOT EXISTS idx_cases_court ON cases(court_id);
CREATE INDEX IF NOT EXISTS idx_cases_date ON cases(decision_date);
CREATE INDEX IF NOT EXISTS idx_cases_cnr ON cases(cnr_number);
CREATE INDEX IF NOT EXISTS idx_cases_neutral ON cases(neutral_citation);
CREATE INDEX IF NOT EXISTS idx_cases_parties_fts ON cases
  USING GIN (to_tsvector('english', coalesce(petitioner, '') || ' ' || coalesce(respondent, '')));

CREATE INDEX IF NOT EXISTS idx_case_citations_case ON case_citations(case_id);
CREATE INDEX IF NOT EXISTS idx_case_citations_text ON case_citations(citation);

CREATE INDEX IF NOT EXISTS idx_judgments_case ON judgments(case_id);
CREATE INDEX IF NOT EXISTS idx_judgments_date ON judgments(judgment_date);
CREATE INDEX IF NOT EXISTS idx_judgments_hash ON judgments(pdf_hash);
CREATE INDEX IF NOT EXISTS idx_judgments_extraction_status ON judgments(extraction_status);
CREATE INDEX IF NOT EXISTS idx_judgments_fts ON judgments
  USING GIN (to_tsvector('english', coalesce(clean_text, '')));

CREATE INDEX IF NOT EXISTS idx_case_sections_case ON case_sections(case_id);
CREATE INDEX IF NOT EXISTS idx_case_sections_section ON case_sections(section_id);
CREATE INDEX IF NOT EXISTS idx_case_sections_raw ON case_sections(raw_act_name, raw_section_number);

CREATE INDEX IF NOT EXISTS idx_issues_tag ON case_issues(issue_tag);
CREATE INDEX IF NOT EXISTS idx_outcomes_result ON outcomes(result);

CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_case_id);
CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_case_id);
CREATE INDEX IF NOT EXISTS idx_citations_type ON citations(citation_type);

CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_type, source_id);
-- Create vector indexes after bulk embedding loads. Keeping this here is fine for small MVP data.
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine ON embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_private_cases_user ON private_cases(external_user_id);
CREATE INDEX IF NOT EXISTS idx_private_files_case ON private_case_files(private_case_id);

CREATE INDEX IF NOT EXISTS idx_corpus_targets_type ON corpus_targets(target_type, court_level, domain_tag);
CREATE INDEX IF NOT EXISTS idx_collection_batches_target ON collection_batches(target_code, status);
