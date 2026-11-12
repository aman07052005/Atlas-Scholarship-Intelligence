from .database import init_db,connect,DB_PATH
from .crawler import upsert_record
def seed_change_demo(db_path=DB_PATH):
    # Controlled fixture only; not a real scholarship or claimed provider change.
    init_db(db_path)
    r={"scholarship_name":"DEMO FIXTURE — Deadline Change Scenario","provider":"Controlled test fixture (not real)",
       "source_type":"DEMO_ONLY","official_source_url":"https://example.org/fixture","application_url":"",
       "amount_benefit":"Not specified","eligibility":"Not specified","closing_date":"31-08-2026",
       "current_status":"ACTIVE","evidence":"Controlled fixture for validating audit history; not an observed provider change."}
    upsert_record(r,db_path,official_page_present=False)
    r["closing_date"]="15-09-2026"
    r["evidence"]="Controlled fixture update: old 31-08-2026; new 15-09-2026. Not an observed provider change."
    upsert_record(r,db_path,official_page_present=False)
