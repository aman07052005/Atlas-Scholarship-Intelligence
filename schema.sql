-- Atlas Scholarship Intelligence SQLite schema (generated from the packaged demo DB)



CREATE TABLE change_history(
          id INTEGER PRIMARY KEY, scholarship_id INTEGER, field_name TEXT, old_value TEXT,
          new_value TEXT, detected_at TEXT, source_url TEXT, evidence_text TEXT,
          evidence_date TEXT, run_id INTEGER, change_kind TEXT);

CREATE TABLE crawl_runs(
          id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, seed_url TEXT,
          discovered_count INTEGER DEFAULT 0, fetched_count INTEGER DEFAULT 0,
          inserted_count INTEGER DEFAULT 0, updated_count INTEGER DEFAULT 0, errors TEXT);

CREATE TABLE discovered_urls(
          id INTEGER PRIMARY KEY, url TEXT UNIQUE, discovered_from TEXT, discovered_at TEXT,
          crawl_status TEXT, page_title TEXT, extracted_at TEXT);

CREATE TABLE extracted_candidates(
          id INTEGER PRIMARY KEY, source_url TEXT, page_title TEXT, candidate_json TEXT,
          extracted_at TEXT, review_status TEXT DEFAULT 'REVIEW_REQUIRED');

CREATE TABLE field_evidence(
          id INTEGER PRIMARY KEY, scholarship_id INTEGER, field_name TEXT, field_value TEXT,
          source_url TEXT, evidence_excerpt TEXT, captured_at TEXT, evidence_type TEXT,
          web_capture_ref TEXT, document_version TEXT,
          FOREIGN KEY(scholarship_id) REFERENCES scholarships(id));

CREATE TABLE page_change_events(
          id INTEGER PRIMARY KEY, url TEXT NOT NULL, old_hash TEXT, new_hash TEXT,
          detected_at TEXT NOT NULL, old_title TEXT, new_title TEXT,
          evidence_excerpt TEXT, run_id INTEGER);

CREATE TABLE page_snapshots(
          id INTEGER PRIMARY KEY, url TEXT, fetched_at TEXT, content_hash TEXT,
          page_title TEXT, extracted_text TEXT, http_status INTEGER, error TEXT);

CREATE TABLE scholarships(
          id INTEGER PRIMARY KEY, scholarship_name TEXT UNIQUE NOT NULL, provider TEXT, source_type TEXT,
          official_source_url TEXT, application_url TEXT, amount_benefit TEXT, eligibility TEXT,
          academic_requirements TEXT, education_level TEXT, income_criteria TEXT, age_criteria TEXT,
          gender_criteria TEXT, category_criteria TEXT, domicile_state TEXT, institution_criteria TEXT,
          opening_date TEXT, closing_date TEXT, documents_required TEXT, selection_process TEXT,
          renewal_requirements TEXT, current_status TEXT, confidence_score REAL, verification_status TEXT,
          last_verified TEXT, evidence TEXT, record_hash TEXT, created_at TEXT, updated_at TEXT,
          scheme_guideline_url TEXT, guideline_version TEXT, verification_basis TEXT, source_conflict TEXT,
          current_cycle_source_url TEXT);

CREATE INDEX idx_changes_detected ON change_history(detected_at);
CREATE INDEX idx_evidence_scholarship ON field_evidence(scholarship_id);
CREATE INDEX idx_snapshots_url ON page_snapshots(url, fetched_at);
