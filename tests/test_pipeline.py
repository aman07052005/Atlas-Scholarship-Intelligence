import csv
from pathlib import Path
from src.database import init_db,connect
from src.crawler import import_seed_csv,upsert_record
from src.verification import confidence_breakdown,classify_verification,lifecycle_status,is_official_url
from src.extractor import extract_structured_candidate
from src.history import import_official_change_events
ROOT=Path(__file__).resolve().parents[1]
def test_seed_import_and_schema(tmp_path):
    db=tmp_path/"x.db";run,n=import_seed_csv(ROOT/"data"/"scholarships_seed.csv",str(db))
    with connect(db) as c:
        assert c.execute("select count(*) from scholarships").fetchone()[0]>=20
        assert c.execute("select count(*) from field_evidence").fetchone()[0]>0
def test_official_change_events_are_two_and_auditable(tmp_path):
    db=tmp_path/"x.db";import_seed_csv(ROOT/"data"/"scholarships_seed.csv",str(db))
    n=import_official_change_events(ROOT/"data"/"official_change_events.csv",str(db))
    with connect(db) as c:
        assert n>=2
        assert c.execute("select count(*) from change_history where change_kind='OFFICIAL_NOTIFICATION'").fetchone()[0]>=2
def test_change_detection_on_repeat_upsert(tmp_path):
    db=tmp_path/"x.db";init_db(db)
    r={"scholarship_name":"Demo real-shaped record","provider":"Ministry","source_type":"Government","official_source_url":"https://pib.gov.in/a","application_url":"https://scholarships.gov.in","closing_date":"30-09-2026","evidence":"official release","source_ref":"test"}
    upsert_record(r,db)
    r["closing_date"]="31-10-2026";r["evidence"]="official revised notice";upsert_record(r,db)
    with connect(db) as c:assert c.execute("select count(*) from change_history").fetchone()[0]==1
def test_confidence_threshold_and_primary_source():
    from src.verification import confidence_breakdown, classify_verification
    r={"scholarship_name":"x","provider":"Govt","source_type":"Government",
       "official_source_url":"https://scholarships.gov.in/x",
       "scheme_guideline_url":"https://scholarships.gov.in/guideline.pdf",
       "application_url":"https://scholarships.gov.in/apply",
       "research_capture_date":"2026-11-10","source_conflict":"false"}
    ev=[
        {"field_name":"eligibility","field_value":"eligible undergraduate students",
         "source_url":"https://scholarships.gov.in/guideline.pdf","evidence_excerpt":"Eligibility: eligible undergraduate students"},
        {"field_name":"amount_benefit","field_value":"₹10,000 per year",
         "source_url":"https://scholarships.gov.in/guideline.pdf","evidence_excerpt":"Scholarship amount ₹10,000 per year"},
        {"field_name":"application_route","field_value":"Apply through NSP",
         "source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Apply through NSP portal"},
        {"field_name":"current_status","field_value":"ACTIVE",
         "source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Applications close 30-11-2026"},
    ]
    score,checks=confidence_breakdown(r,ev)
    assert score==100
    assert classify_verification(score,checks)=="VERIFIED"


def test_unknown_values_not_fabricated():
    assert lifecycle_status({"closing_date":"","observed_status":"REVIEW_REQUIRED"})=="REVIEW_REQUIRED"
def test_extractor_preserves_unknowns_and_snippets():
    page={"url":"https://scholarships.gov.in/example","title":"Example Scholarship","text":"The last date for application is 15-11-2026. Family income should be below Rs 3 lakh."}
    r=extract_structured_candidate(page)
    assert r["scholarship_name"]=="Example Scholarship"
    assert r["closing_date"]!="Not specified"
    assert len(r["field_evidence"])>=1 and r["needs_human_review"]

def test_official_source_conflict_lowers_score():
    from src.verification import confidence_breakdown, classify_verification
    r={"scholarship_name":"CSSS","provider":"Ministry","source_type":"Government",
       "official_source_url":"https://scholarships.gov.in/All-Scholarships",
       "scheme_guideline_url":"https://scholarships.gov.in/guideline.pdf",
       "research_capture_date":"2026-11-10","source_conflict":"true"}
    ev=[
        {"field_name":"eligibility","field_value":"eligible students","source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Eligibility criteria cover eligible students"},
        {"field_name":"amount_benefit","field_value":"₹10,000","source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Scholarship amount is ₹10,000"},
        {"field_name":"application_route","field_value":"Apply","source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Apply through the official portal"},
        {"field_name":"current_status","field_value":"ACTIVE","source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Current applications close 30-11-2026"},
    ]
    score,checks=confidence_breakdown(r,ev)
    assert score < 95
    assert checks["no_known_source_conflict"]["passed"] is False
    assert classify_verification(score,checks)=="REVIEW_REQUIRED"


def test_crawler_discovers_fetches_extracts_and_persists_candidate(tmp_path):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    from src.crawler import crawl_seed_sources
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=="/":
                body=b'<html><title>Scholarship Directory</title><a href="/scheme/alpha">Alpha Scholarship</a></html>'
            else:
                body=b'<html><title>Alpha Scholarship</title><body>Eligibility: first year undergraduate students. Family income below Rs 2 lakh. Scholarship amount Rs 20,000. Last date 30-11-2026.</body></html>'
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        result=crawl_seed_sources([f'http://127.0.0.1:{server.server_port}/'],max_links=10,db_path=str(tmp_path/'crawl.db'))
        assert result['discovered']>=1 and result['fetched']>=1
        with connect(tmp_path/'crawl.db') as c:
            assert c.execute('select count(*) from page_snapshots').fetchone()[0]>=1
            assert c.execute('select count(*) from extracted_candidates').fetchone()[0]>=1
            assert c.execute("select review_status from extracted_candidates limit 1").fetchone()[0]=='REVIEW_REQUIRED'
    finally:
        server.shutdown();thread.join(timeout=2);server.server_close()


def test_curated_dataset_has_at_least_10_evidence_verified_records(tmp_path):
    db=tmp_path/"curated.db"
    import_seed_csv(ROOT/"data"/"scholarships_seed.csv",str(db))
    with connect(db) as c:
        assert c.execute("select count(*) from scholarships").fetchone()[0] >= 20
        assert c.execute("select count(*) from scholarships where verification_status='VERIFIED' and confidence_score>=95").fetchone()[0] >= 10
        assert c.execute("select count(*) from field_evidence").fetchone()[0] >= 50


def test_portal_navigation_page_is_not_misclassified_as_scheme():
    page={"url":"https://scholarships.gov.in/All-Scholarships",
          "title":"National Scholarship Portal",
          "text":"Application Status Track Your Payment Aadhaar Seva Kendra Check Aadhaar Seeding Status NSP OTR APP Check UDID details How to fill Registration Form Find Institutes on NSP List of Applicants Processed for Scholarships."}
    candidate=extract_structured_candidate(page)
    assert candidate["is_scheme_candidate"] is False
    assert candidate["candidate_type"] == "SOURCE_PAGE"
    assert candidate["scholarship_name"] == "Not specified"
    assert candidate["amount_benefit"] == "Not specified"
    assert candidate["eligibility"] == "Not specified"


def test_pdf_filename_is_not_used_as_scholarship_name():
    page={"url":"https://scholarships.gov.in/public/FAQ/FAQforICAR_NTS_PG_3104.pdf",
          "title":"FAQforICAR_NTS_PG_3104.pdf", "is_pdf":True,
          "text":"Frequently Asked Questions. Eligibility criteria of awarding ICAR NTS-PG Scholarship? Securing admission in Post Graduate programme in any non-domicile state. The scholarship amount is Rs. 5000 per month for PG students."}
    candidate=extract_structured_candidate(page)
    assert candidate["is_scheme_candidate"] is True
    assert "ICAR NTS-PG Scholarship" in candidate["scholarship_name"]
    assert candidate["amount_benefit"] != "Not specified"
    assert candidate["eligibility"] != "Not specified"
    assert all(x["evidence_excerpt"] == x["value"] for x in candidate["field_evidence"])


def test_pdf_with_generic_content_is_not_a_scheme_candidate():
    page={"url":"https://scholarships.gov.in/public/FAQ/general_faq.pdf",
          "title":"general_faq.pdf", "is_pdf":True,
          "text":"Frequently Asked Questions. Login to the portal. Contact the helpdesk for registration assistance."}
    candidate=extract_structured_candidate(page)
    assert candidate["is_scheme_candidate"] is False
    assert candidate["scholarship_name"] == "Not specified"


def test_candidate_fields_require_relevant_sentence_context():
    page={"url":"https://scholarships.gov.in/guidelines/example",
          "title":"Example Merit Scholarship", "headings":["Example Merit Scholarship"],
          "text":"Example Merit Scholarship. Students must be enrolled in a recognized undergraduate course. Family income must be below Rs 2 lakh per annum. The scholarship amount is Rs 20,000 per year. Applications close on 30-11-2026."}
    candidate=extract_structured_candidate(page)
    assert candidate["is_scheme_candidate"] is True
    assert "recognized undergraduate" in candidate["eligibility"]
    assert "Family income" in candidate["income_criteria"]
    assert "scholarship amount" in candidate["amount_benefit"].lower()
    assert "30-11-2026" in candidate["closing_date"]
    assert len(candidate["field_evidence"]) >= 4


def test_extract_page_removes_navigation_and_preserves_main_content(monkeypatch):
    from src import crawler
    html=b'''<html><head><title>Example Merit Scholarship</title></head><body>
    <nav>Aadhaar Seva Kendra Login Helpdesk</nav>
    <main><h1>Example Merit Scholarship</h1>
    <p>Students must be enrolled in a recognized undergraduate course.</p>
    <p>Scholarship amount is Rs 20,000 per year.</p></main>
    <footer>Contact us Site map</footer></body></html>'''
    monkeypatch.setattr(crawler,"fetch_page",lambda url:(html,url,200,"text/html; charset=utf-8"))
    page=crawler.extract_page("https://scholarships.gov.in/example")
    assert page["title"]=="Example Merit Scholarship"
    assert "Aadhaar Seva Kendra" not in page["text"]
    assert "Contact us" not in page["text"]
    assert "recognized undergraduate" in page["text"]


def test_missing_benefit_evidence_cannot_be_verified():
    from src.verification import confidence_breakdown, classify_verification
    record={"scholarship_name":"ICAR example","official_source_url":"https://scholarships.gov.in/All-Scholarships",
            "scheme_guideline_url":"https://www.icar.gov.in/sites/default/files/guidelines.pdf",
            "application_url":"https://scholarships.gov.in/", "source_conflict":"false"}
    evidence=[
        {"field_name":"eligibility","field_value":"AIEE admission outside domicile state","source_url":"https://www.icar.gov.in/guidelines.pdf","evidence_excerpt":"AIEE admission outside domicile state"},
        {"field_name":"current_status","field_value":"EXPIRED","source_url":"https://scholarships.gov.in/All-Scholarships","evidence_excerpt":"Student application close 31-10-2026"},
        {"field_name":"application_route","field_value":"NSP","source_url":"https://scholarships.gov.in/All-Scholarships","evidence_excerpt":"Apply through NSP"},
    ]
    score, checks=confidence_breakdown(record,evidence)
    assert checks["benefit_field_evidence"]["passed"] is False
    assert classify_verification(score,checks)=="REVIEW_REQUIRED"


def test_official_application_url_without_route_excerpt_is_partial_credit_only():
    from src.verification import confidence_breakdown, classify_verification
    r={"scholarship_name":"x","official_source_url":"https://scholarships.gov.in/x",
       "scheme_guideline_url":"https://scholarships.gov.in/guideline.pdf",
       "application_url":"https://scholarships.gov.in/apply","research_capture_date":"2026-11-10","source_conflict":"false"}
    ev=[{"field_name":"eligibility","field_value":"eligible students","source_url":"https://scholarships.gov.in/guideline.pdf","evidence_excerpt":"Eligibility: eligible students"},
        {"field_name":"amount_benefit","field_value":"₹10,000","source_url":"https://scholarships.gov.in/guideline.pdf","evidence_excerpt":"Scholarship amount ₹10,000"},
        {"field_name":"current_status","field_value":"ACTIVE","source_url":"https://scholarships.gov.in/x","evidence_excerpt":"Applications close 30-11-2026"}]
    score, checks=confidence_breakdown(r,ev)
    assert checks["application_route_field_evidence"]["passed"] is False
    assert score == 95
    assert classify_verification(score,checks)=="VERIFIED"


def test_known_conflict_never_verifies_even_with_complete_evidence():
    from src.verification import confidence_breakdown, classify_verification
    r={"scholarship_name":"ICAR NTS-PG","official_source_url":"https://scholarships.gov.in/All-Scholarships",
       "scheme_guideline_url":"https://www.icar.gov.in/sites/default/files/Circulars/Guidelines%20for%20ICAR%20NTS%20Scholarship.pdf",
       "application_url":"https://scholarships.gov.in/","source_conflict":"true"}
    ev=[{"field_name":f,"field_value":"captured","source_url":"https://www.icar.gov.in/guidelines.pdf","evidence_excerpt":"Official evidence excerpt for "+f} for f in ("eligibility","amount_benefit","application_route","current_status")]
    score,checks=confidence_breakdown(r,ev)
    assert score < 95
    assert classify_verification(score,checks)=="REVIEW_REQUIRED"


def test_repeated_crawl_persists_page_hash_change(tmp_path):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    from src.crawler import crawl_seed_sources
    from src.database import connect
    state = {"amount": "Rs 20,000"}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = b'<html><title>Scholarship Directory</title><a href="/scheme/alpha">Alpha Scholarship</a></html>'
            else:
                body = (f'<html><title>Alpha Scholarship</title><main><h1>Alpha Scholarship</h1>'
                        f'<p>Eligibility: first year undergraduate students.</p>'
                        f'<p>Scholarship amount {state["amount"]} per year.</p>'
                        f'<p>Last date 30-11-2026.</p></main></html>').encode()
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers(); self.wfile.write(body)
        def log_message(self, *args): pass
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    db = str(tmp_path / "repeat.db")
    seed = f"http://127.0.0.1:{server.server_port}/"
    try:
        first = crawl_seed_sources([seed], max_links=10, db_path=db)
        assert first["fetched"] >= 1
        state["amount"] = "Rs 25,000"
        second = crawl_seed_sources([seed], max_links=10, db_path=db)
        assert second["fetched"] >= 1
        with connect(db) as con:
            changes = con.execute("SELECT COUNT(*) FROM page_change_events").fetchone()[0]
        assert changes >= 1
    finally:
        server.shutdown(); thread.join(timeout=2); server.server_close()


def test_stale_evidence_cannot_pass_current_cycle_gate():
    from src.verification import confidence_breakdown
    record = {
        "official_source_url": "https://scholarships.gov.in/scheme/alpha",
        "scheme_guideline_url": "https://scholarships.gov.in/guidelines/alpha.pdf",
        "research_capture_date": "2025-01-01",
        "source_conflict": "false",
    }
    evidence = [
        {"field_name": "eligibility", "field_value": "UG students", "source_url": "https://scholarships.gov.in/guidelines/alpha.pdf", "evidence_excerpt": "Eligibility applies to undergraduate students."},
        {"field_name": "amount_benefit", "field_value": "Rs 20,000", "source_url": "https://scholarships.gov.in/guidelines/alpha.pdf", "evidence_excerpt": "The scholarship amount is Rs 20,000 annually."},
        {"field_name": "current_status", "field_value": "ACTIVE", "source_url": "https://scholarships.gov.in/scheme/alpha", "evidence_excerpt": "The application window for the current year is open.", "captured_on": "2025-01-01"},
    ]
    _, checks = confidence_breakdown(record, evidence, today=__import__("datetime").date(2026, 11, 10))
    assert checks["current_cycle_or_status_evidence"]["passed"] is False


def test_generic_portal_page_is_not_a_scheme_guideline():
    from src.verification import confidence_breakdown
    record = {"official_source_url": "https://scholarships.gov.in/All-Scholarships",
              "scheme_guideline_url": "https://scholarships.gov.in/All-Scholarships"}
    score, checks = confidence_breakdown(record, [])
    assert checks["scheme_specific_official_guideline"]["passed"] is False
    assert score < 95


def test_icar_faq_question_is_paired_with_following_answer_not_question_heading():
    import json
    page = {
        "url": "https://scholarships.gov.in/public/FAQ/FAQsforICAR_NTS-PG_3104.pdf",
        "title": "FAQsforICAR_NTS-PG_3104.pdf",
        "is_pdf": True,
        "text": (
            "Frequently Asked Questions on ICAR NTS-PG Scholarship\n"
            "Q. No. 1: What are the eligibility criteria of awarding ICAR NTS-PG Scholarship?\n"
            "Securing admission in a Post Graduate programme in a non-domicile state. "
            "Master's students admitted through AIEE in an Agricultural University "
            "outside their domicile state are eligible.\n"
            "Q. No. 2: What is the amount of ICAR NTS-PG Scholarship?\n"
            "The scholarship amount is Rs. 5,000 per month for PG students.\n"
            "Q. No. 3: What are the renewal conditions?\n"
            "Continuation is subject to good conduct, punctuality and minimum "
            "qualifying CGPA."
        ),
    }
    candidate = extract_structured_candidate(page)
    assert candidate["scholarship_name"] == "ICAR NTS-PG Scholarship"
    assert "non-domicile state" in candidate["eligibility"].lower()
    assert "what are the eligibility criteria" not in candidate["eligibility"].lower()
    assert "5,000 per month" in candidate["amount_benefit"]
    assert "good conduct" in candidate["renewal_requirements"].lower()
    for field in ("eligibility", "amount_benefit", "renewal_requirements"):
        rows = [x for x in candidate["field_evidence"] if x["field"] == field]
        assert rows, f"missing evidence for {field}"
        assert "Answer:" in rows[0]["evidence_excerpt"]
        assert rows[0]["source_url"] == page["url"]


def test_faq_question_only_is_never_used_as_field_value():
    page = {
        "url": "https://scholarships.gov.in/public/FAQ/icar.pdf",
        "title": "icar.pdf",
        "is_pdf": True,
        "text": (
            "Frequently Asked Questions on ICAR NTS-PG Scholarship\n"
            "Q. No. 1: What are the eligibility criteria of awarding ICAR NTS-PG Scholarship?"
        ),
    }
    candidate = extract_structured_candidate(page)
    assert candidate["eligibility"] == "Not specified"
    assert candidate["amount_benefit"] == "Not specified"
    assert candidate["is_scheme_candidate"] is False


def test_repeated_crawl_updates_one_candidate_per_source_url(tmp_path):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread
    from src.crawler import crawl_seed_sources
    from src.database import connect

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/robots.txt":
                body = b"User-agent: *\\nAllow: /\\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
            elif self.path == "/":
                body = b'<html><title>Directory</title><a href="/scheme">Example Merit Scholarship</a></html>'
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
            else:
                body = (b'<html><title>Example Merit Scholarship</title><main>'
                        b'<h1>Example Merit Scholarship</h1>'
                        b'<p>Eligibility: enrolled undergraduate students.</p>'
                        b'<p>The scholarship amount is Rs 20,000 per year.</p>'
                        b'</main></html>')
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    db = str(tmp_path / "dedupe.db")
    seed = f"http://127.0.0.1:{server.server_port}/"
    try:
        first = crawl_seed_sources([seed], max_links=10, db_path=db)
        second = crawl_seed_sources([seed], max_links=10, db_path=db)
        assert first["fetched"] == 1 and second["fetched"] == 1
        assert first["inserted"] == 1 and first["updated"] == 0
        assert second["inserted"] == 0 and second["updated"] == 1
        with connect(db) as con:
            run_metrics = con.execute(
                "SELECT inserted_count, updated_count FROM crawl_runs ORDER BY id"
            ).fetchall()
            assert [tuple(row) for row in run_metrics] == [(1, 0), (0, 1)]
            count = con.execute(
                "SELECT COUNT(*) FROM extracted_candidates WHERE source_url=?",
                (f"http://127.0.0.1:{server.server_port}/scheme",),
            ).fetchone()[0]
        assert count == 1
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_official_icar_faq_pdf_layout_extracts_all_supported_answers():
    page = {
        "url": "https://scholarships.gov.in/public/FAQ/FAQsforICAR_NTS-PG_3104.pdf",
        "title": "FAQsforICAR_NTS-PG_3104.pdf",
        "is_pdf": True,
        "text": (
            "Frequently Asked Questions on ICAR NTS-PG Scholarship\n"
            "Q. No. 1: What are the eligibility criteria of awarding ICAR NTS-PG Scholarship?\n"
            "Answer: Securing admission in Post Graduate programme in any non-domicile state.\n"
            "Q. No. 2: Who is eligible to get ICAR NTS-PG Scholarship?\n"
            "Answer: National Talent Scholarship (NTS) of the Indian Council of Agricultural Research is "
            "available to a student pursuing Master degree programme admitted through All India Entrance "
            "Examination (AIEE) in the Agricultural University located outside of his State of domicile.\n"
            "Q. No. 3: What is the amount and duration of ICAR NTS-PG Scholarship?\n"
            "Answer: NTS-PG is awarded @ Rs.5000/- per month to PG students for entire duration of "
            "degree programme subject to minimum qualifying CGPA.\n"
            "Q. No. 4: Is there any evaluation process for continuation of ICAR NTS-PG Scholarship?\n"
            "Answer: The continuation of the ICAR NTS-PG scholarship is subject to good conduct, punctuality "
            "and minimum prescribed performance [OGPA/CGPA of minimum 7.00 OUT of 10.00 (6.50/10.00 for SC/ST)].\n"
            "Q. No. 7: Do I have to apply separately for ICAR NTS-PG Scholarship?\n"
            "Answer: No. Candidates who appeared and admitted through All India Entrance Examination "
            "(AIEE) under ICAR AIQ Seats are automatically eligible for the said scholarship.\n"
            "Q. No. 8: What documents are required to be uploaded on NSP for release of the scholarship?\n"
            "Answer: Award letter issued by the ICAR may be required."
        ),
    }
    candidate = extract_structured_candidate(page)
    assert candidate["scholarship_name"] == "ICAR NTS-PG Scholarship"
    assert "outside of his State of domicile" in candidate["eligibility"]
    assert "Rs.5000/- per month" in candidate["amount_benefit"]
    assert "good conduct" in candidate["renewal_requirements"]
    assert "7.00 OUT of 10.00" in candidate["academic_requirements"]
    assert "automatically eligible" in candidate["application_route"]
    assert "Award letter" in candidate["documents_required"]
    assert all("Question:" in row["evidence_excerpt"] and "Answer:" in row["evidence_excerpt"]
               for row in candidate["field_evidence"])
    assert all(row["source_url"] == page["url"] for row in candidate["field_evidence"])


def test_icar_faq_extraction_handles_flattened_pdf_text():
    page = {
        "url": "https://scholarships.gov.in/public/FAQ/FAQsforICAR_NTS-PG_3104.pdf",
        "title": "FAQsforICAR_NTS-PG_3104.pdf",
        "is_pdf": True,
        "text": (
            "Frequently Asked Questions on ICAR NTS-PG Scholarship "
            "Q. No. 1: What are the eligibility criteria of awarding ICAR NTS-PG Scholarship? "
            "Answer: Securing admission in Post Graduate programme in any non-domicile state. "
            "Q. No. 3: What is the amount and duration of ICAR NTS-PG Scholarship? "
            "Answer: NTS-PG is awarded @ Rs.5000/- per month to PG students for entire duration of degree programme."
        ),
    }
    candidate = extract_structured_candidate(page)
    assert "non-domicile state" in candidate["eligibility"]
    assert "Rs.5000/- per month" in candidate["amount_benefit"]
    assert "Q. No." not in candidate["eligibility"]


def test_database_startup_consolidates_legacy_duplicate_candidates(tmp_path):
    import sqlite3
    from src.database import init_db, connect
    db = tmp_path / "legacy-duplicates.db"
    raw = sqlite3.connect(db)
    raw.execute("CREATE TABLE extracted_candidates (id INTEGER PRIMARY KEY, source_url TEXT, page_title TEXT, candidate_json TEXT, extracted_at TEXT, review_status TEXT DEFAULT 'REVIEW_REQUIRED')")
    raw.executemany(
        "INSERT INTO extracted_candidates(source_url,page_title,candidate_json,extracted_at,review_status) VALUES(?,?,?,?,?)",
        [
            ("https://example.gov/scheme.pdf", "old", "{}", "2026-11-10", "REVIEW_REQUIRED"),
            ("https://example.gov/scheme.pdf", "new", "{\\\"latest\\\":true}", "2026-11-11", "REVIEW_REQUIRED"),
        ],
    )
    raw.commit()
    raw.close()
    init_db(db)
    with connect(db) as con:
        rows = con.execute("SELECT page_title FROM extracted_candidates WHERE source_url=?", ("https://example.gov/scheme.pdf",)).fetchall()
    assert len(rows) == 1
    assert rows[0]["page_title"] == "new"


def test_cycle_source_is_stored_separately_from_scheme_guideline(tmp_path):
    import sqlite3
    db=tmp_path/"cycle-source.db"
    import_seed_csv(ROOT/"data"/"scholarships_seed.csv",str(db))
    with connect(db) as c:
        cols={r["name"] for r in c.execute("PRAGMA table_info(scholarships)")}
        assert "current_cycle_source_url" in cols
        row=c.execute("""SELECT official_source_url,scheme_guideline_url,current_cycle_source_url
                         FROM scholarships
                         WHERE scholarship_name LIKE 'AICTE - Pragati%'""").fetchone()
        assert row["official_source_url"].endswith("AICTE_2010_G.pdf")
        assert row["scheme_guideline_url"].endswith("AICTE_2010_G.pdf")
        assert row["current_cycle_source_url"]=="https://scholarships.gov.in/All-Scholarships"
