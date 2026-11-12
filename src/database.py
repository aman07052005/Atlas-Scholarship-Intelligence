"""SQLite schema and connection lifecycle for Atlas."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "atlas.db"


@contextmanager
def connect(path=DB_PATH):
    """Yield a configured SQLite connection and always close it afterwards."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(path=DB_PATH):
    with connect(path) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS scholarships(
          id INTEGER PRIMARY KEY, scholarship_name TEXT UNIQUE NOT NULL, provider TEXT, source_type TEXT,
          official_source_url TEXT, application_url TEXT, amount_benefit TEXT, eligibility TEXT,
          academic_requirements TEXT, education_level TEXT, income_criteria TEXT, age_criteria TEXT,
          gender_criteria TEXT, category_criteria TEXT, domicile_state TEXT, institution_criteria TEXT,
          opening_date TEXT, closing_date TEXT, documents_required TEXT, selection_process TEXT,
          renewal_requirements TEXT, current_status TEXT, confidence_score REAL, verification_status TEXT,
          last_verified TEXT, evidence TEXT, record_hash TEXT, created_at TEXT, updated_at TEXT,
          scheme_guideline_url TEXT, guideline_version TEXT, verification_basis TEXT, source_conflict TEXT, current_cycle_source_url TEXT);
        CREATE TABLE IF NOT EXISTS field_evidence(
          id INTEGER PRIMARY KEY, scholarship_id INTEGER, field_name TEXT, field_value TEXT,
          source_url TEXT, evidence_excerpt TEXT, captured_at TEXT, evidence_type TEXT,
          web_capture_ref TEXT, document_version TEXT,
          FOREIGN KEY(scholarship_id) REFERENCES scholarships(id));
        CREATE TABLE IF NOT EXISTS crawl_runs(
          id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, seed_url TEXT,
          discovered_count INTEGER DEFAULT 0, fetched_count INTEGER DEFAULT 0,
          inserted_count INTEGER DEFAULT 0, updated_count INTEGER DEFAULT 0, errors TEXT);
        CREATE TABLE IF NOT EXISTS change_history(
          id INTEGER PRIMARY KEY, scholarship_id INTEGER, field_name TEXT, old_value TEXT,
          new_value TEXT, detected_at TEXT, source_url TEXT, evidence_text TEXT,
          evidence_date TEXT, run_id INTEGER, change_kind TEXT);
        CREATE TABLE IF NOT EXISTS discovered_urls(
          id INTEGER PRIMARY KEY, url TEXT UNIQUE, discovered_from TEXT, discovered_at TEXT,
          crawl_status TEXT, page_title TEXT, extracted_at TEXT);
        CREATE TABLE IF NOT EXISTS page_snapshots(
          id INTEGER PRIMARY KEY, url TEXT, fetched_at TEXT, content_hash TEXT,
          page_title TEXT, extracted_text TEXT, http_status INTEGER, error TEXT);
        CREATE TABLE IF NOT EXISTS extracted_candidates(
          id INTEGER PRIMARY KEY, source_url TEXT, page_title TEXT, candidate_json TEXT,
          extracted_at TEXT, review_status TEXT DEFAULT 'REVIEW_REQUIRED');
        CREATE TABLE IF NOT EXISTS page_change_events(
          id INTEGER PRIMARY KEY, url TEXT NOT NULL, old_hash TEXT, new_hash TEXT,
          detected_at TEXT NOT NULL, old_title TEXT, new_title TEXT,
          evidence_excerpt TEXT, run_id INTEGER);
        CREATE INDEX IF NOT EXISTS idx_evidence_scholarship ON field_evidence(scholarship_id);
        CREATE INDEX IF NOT EXISTS idx_snapshots_url ON page_snapshots(url, fetched_at);
        CREATE INDEX IF NOT EXISTS idx_changes_detected ON change_history(detected_at);
        ''')
        cols = {r[1] for r in c.execute("PRAGMA table_info(scholarships)")}
        for name in ("scheme_guideline_url", "guideline_version", "verification_basis", "source_conflict", "current_cycle_source_url"):
            if name not in cols:
                c.execute(f"ALTER TABLE scholarships ADD COLUMN {name} TEXT")
        evcols = {r[1] for r in c.execute("PRAGMA table_info(field_evidence)")}
        for name in ("web_capture_ref", "document_version"):
            if name not in evcols:
                c.execute(f"ALTER TABLE field_evidence ADD COLUMN {name} TEXT")
        pagecols = {r[1] for r in c.execute("PRAGMA table_info(page_change_events)")}
        if "run_id" not in pagecols:
            c.execute("ALTER TABLE page_change_events ADD COLUMN run_id INTEGER")
        # Keep one current review payload per source URL. Page snapshots and
        # page_change_events retain crawl history; duplicate review rows do not.
        c.execute("""
            DELETE FROM extracted_candidates
            WHERE source_url IS NOT NULL
              AND id NOT IN (
                SELECT MAX(id) FROM extracted_candidates
                WHERE source_url IS NOT NULL
                GROUP BY source_url
              )
        """)
        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_source_unique
            ON extracted_candidates(source_url)
        """)
    return str(path)
