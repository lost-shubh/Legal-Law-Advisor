INSERT INTO data_sources (source_code, source_name, source_type, base_url, jurisdiction, notes)
VALUES
  ('INDIA_CODE', 'India Code', 'STATUTE', 'https://www.indiacode.nic.in/', 'INDIA', 'Primary source for Central and State Acts.'),
  ('EGAZETTE', 'e-Gazette of India', 'GAZETTE', 'https://egazette.gov.in/', 'INDIA', 'Official notifications, rules, commencement and amendments.'),
  ('SCI', 'Supreme Court of India', 'JUDGMENT', 'https://www.sci.gov.in/', 'INDIA', 'Official Supreme Court website.'),
  ('ESCR', 'e-SCR Supreme Court Reports', 'JUDGMENT', 'https://scr.sci.gov.in/scrsearch/', 'INDIA', 'Official electronic Supreme Court Reports search.'),
  ('DOJ_JUDGMENTS', 'Department of Justice Judgment Search Portal', 'JUDGMENT', 'https://doj.gov.in/judgment-search-portal/', 'INDIA', 'High Court judgments and final orders search entry point.'),
  ('ECOURTS', 'eCourts Services', 'CASE_STATUS', 'https://services.ecourts.gov.in/ecourtindia_v6/', 'INDIA', 'District court case status, orders and judgments where public.'),
  ('NJDG', 'National Judicial Data Grid', 'COURT_METADATA', 'https://doj.gov.in/the-national-judicial-data-grid-njdg/', 'INDIA', 'Aggregate judicial data, not a full public case-file API.')
ON CONFLICT (source_code) DO NOTHING;

INSERT INTO courts (court_code, court_name, court_level, state)
VALUES
  ('SC', 'Supreme Court of India', 'SUPREME', 'India'),
  ('HC-DEL', 'High Court of Delhi', 'HIGH', 'Delhi'),
  ('HC-BOM', 'High Court of Bombay', 'HIGH', 'Maharashtra'),
  ('HC-MAD', 'High Court of Madras', 'HIGH', 'Tamil Nadu'),
  ('HC-ALL', 'High Court of Judicature at Allahabad', 'HIGH', 'Uttar Pradesh'),
  ('HC-KAR', 'High Court of Karnataka', 'HIGH', 'Karnataka'),
  ('HC-CAL', 'High Court at Calcutta', 'HIGH', 'West Bengal')
ON CONFLICT (court_code) DO NOTHING;

WITH india_code AS (
  SELECT id FROM data_sources WHERE source_code = 'INDIA_CODE'
)
INSERT INTO statutes (act_name, short_title, year, jurisdiction, source_id, source_url, india_code_id)
SELECT * FROM (
  VALUES
    ('The Bharatiya Nyaya Sanhita, 2023', 'BNS', 2023, 'CENTRAL', (SELECT id FROM india_code), 'https://www.indiacode.nic.in/handle/123456789/20062', '123456789/20062'),
    ('The Bharatiya Nagarik Suraksha Sanhita, 2023', 'BNSS', 2023, 'CENTRAL', (SELECT id FROM india_code), 'https://www.indiacode.nic.in/handle/123456789/20099', '123456789/20099'),
    ('The Bharatiya Sakshya Adhiniyam, 2023', 'BSA', 2023, 'CENTRAL', (SELECT id FROM india_code), 'https://www.indiacode.nic.in/handle/123456789/20063', '123456789/20063'),
    ('The Digital Personal Data Protection Act, 2023', 'DPDP Act', 2023, 'CENTRAL', (SELECT id FROM india_code), 'https://www.indiacode.nic.in/handle/123456789/22037', '123456789/22037'),
    ('The Negotiable Instruments Act, 1881', 'NI Act', 1881, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Information Technology Act, 2000', 'IT Act', 2000, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Consumer Protection Act, 2019', 'Consumer Protection Act', 2019, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Hindu Marriage Act, 1955', 'HMA', 1955, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Protection of Women from Domestic Violence Act, 2005', 'DV Act', 2005, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Transfer of Property Act, 1882', 'TPA', 1882, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Constitution of India', 'Constitution', 1950, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Motor Vehicles Act, 1988', 'MV Act', 1988, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Industrial Disputes Act, 1947', 'ID Act', 1947, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Indian Penal Code, 1860', 'IPC', 1860, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Code of Criminal Procedure, 1973', 'CrPC', 1973, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL),
    ('The Indian Evidence Act, 1872', 'Evidence Act', 1872, 'CENTRAL', (SELECT id FROM india_code), NULL, NULL)
) AS s(act_name, short_title, year, jurisdiction, source_id, source_url, india_code_id)
ON CONFLICT (act_name, year, jurisdiction) DO NOTHING;
