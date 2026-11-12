"""Atlas Scholarship Intelligence - interactive evidence-first dashboard."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

from src.database import DB_PATH, connect, init_db
from src.crawler import import_seed_csv, crawl_seed_sources, extract_page
from src.extractor import extract_structured_candidate
from src.history import import_official_change_events
from src.verification import explain_score

ROOT = Path(__file__).resolve().parent
SEED = ROOT / "data" / "scholarships_seed.csv"

st.set_page_config(
    page_title="Atlas | Scholarship Intelligence",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --atlas-ink:#17243a; --atlas-muted:#64748b; --atlas-line:#e5eaf2; }
.block-container { padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f7f9fd 0%,#ffffff 34%); }
[data-testid="stSidebar"] { background: #101d33; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown strong,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #edf3ff !important;
}

[data-testid="stSidebar"] hr {
    border-color: #34445f !important;
}

[data-testid="stSidebar"] [data-testid="stAlert"],
[data-testid="stSidebar"] [data-testid="stAlert"] p {
    color: #17243a !important;
}
.atlas-hero { padding: 1.45rem 1.7rem; border-radius: 20px; color: white;
 background: radial-gradient(circle at 90% 15%,rgba(83,155,255,.45),transparent 27%),
 linear-gradient(120deg,#13243e 0%,#1e4775 58%,#2864a0 100%); margin-bottom:1rem;
 box-shadow: 0 12px 30px rgba(24,55,95,.14); }
.atlas-hero h1 { color:white; margin:0; font-size:2rem; letter-spacing:-.04em; }
.atlas-hero p { color:#d9e8fb; margin:.35rem 0 0 0; font-size:.98rem; }
.kpi { background:white; border:1px solid var(--atlas-line); border-radius:16px; padding:14px 16px; min-height:104px;
 box-shadow:0 4px 16px rgba(30,50,80,.04); }
.kpi-label { color:#64748b; font-size:.78rem; font-weight:650; text-transform:uppercase; letter-spacing:.055em; }
.kpi-value { color:#17243a; font-size:1.85rem; font-weight:780; line-height:1.25; margin-top:5px; }
.kpi-note { color:#8491a5; font-size:.76rem; margin-top:3px; }
.section-title { color:#17243a; font-weight:750; font-size:1.16rem; margin:.2rem 0 .55rem; }
.soft-panel { background:#fff; border:1px solid #e6ebf3; border-radius:16px; padding:1rem 1.1rem; }
.status-pill { display:inline-block; border-radius:99px; padding:3px 9px; font-size:.74rem; font-weight:700; background:#edf2f8; color:#34445d; }
div[data-testid="stMetric"] { background:white; border:1px solid var(--atlas-line); border-radius:15px; padding:12px 15px; }
div[data-testid="stTabs"] button { font-weight:650; }
[data-testid="stDataFrame"] { border:1px solid #e7ebf2; border-radius:12px; }
</style>
""", unsafe_allow_html=True)


def read_table(sql: str, params=()) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def metric_card(label: str, value: str, note: str = ""):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def safe_text(value):
    if value is None or str(value).strip() == "":
        return "Not specified"
    return str(value)


init_db()
with connect() as con:
    has_records = con.execute("SELECT COUNT(*) FROM scholarships").fetchone()[0]
if not has_records:
    run_id, imported = import_seed_csv(SEED)
    imported_changes = import_official_change_events(ROOT / "data" / "official_change_events.csv")
    st.toast(f"Loaded {imported} curated records and {imported_changes} official change events.", icon="?")

with st.sidebar:
    st.markdown("## ATLAS")
    st.caption("SCHOLARSHIP INTELLIGENCE")
    st.markdown("---")
    st.markdown("**Evidence-first funding discovery**")
    st.caption("Discover | Extract | Verify | Monitor")
    st.markdown("---")
    st.markdown("**System health**")
    st.success("SQLite database connected")
    st.info("New crawler candidates are always sent to human review.")
    st.markdown("---")
    st.caption("Research snapshot | 10 Nov 2026")
    st.caption("Free and open-source stack")

with connect() as con:
    records = [dict(row) for row in con.execute("SELECT * FROM scholarships ORDER BY scholarship_name")]
df = pd.DataFrame(records)

st.markdown(
    '<div class="atlas-hero"><h1>Scholarship Intelligence, backed by evidence.</h1>'
    '<p>A living repository of Indian education funding - with source traceability, confidence gates and change monitoring.</p></div>',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No scholarship records are loaded. Use the repository import action or run scripts/prepare_demo.py.")
    st.stop()

verified_n = int((df["verification_status"] == "VERIFIED").sum())
review_n = int((df["verification_status"] == "REVIEW_REQUIRED").sum())
active_n = int((df["current_status"] == "ACTIVE").sum())
expired_n = int((df["current_status"] == "EXPIRED").sum())
with connect() as con:
    recent_changes = con.execute("SELECT COUNT(*) FROM change_history WHERE detected_at >= datetime('now','-7 days')").fetchone()[0]
    crawl_runs = con.execute("SELECT COUNT(*) FROM crawl_runs").fetchone()[0]
    candidates_n = con.execute("SELECT COUNT(*) FROM extracted_candidates WHERE review_status='REVIEW_REQUIRED'").fetchone()[0]

kpi_cols = st.columns(6)
for col, label, val, note in [
    (kpi_cols[0], "Scholarships", f"{len(df):,}", "Curated repository"),
    (kpi_cols[1], "Verified >=95", f"{verified_n}", "All mandatory gates pass"),
    (kpi_cols[2], "Review required", f"{review_n}", "Human review queue"),
    (kpi_cols[3], "Active", f"{active_n}", "Current lifecycle status"),
    (kpi_cols[4], "Expired", f"{expired_n}", "Past explicit deadlines"),
    (kpi_cols[5], "Recent changes", f"{recent_changes}", "Detected in last 7 days"),
]:
    with col:
        metric_card(label, val, note)

st.caption(f"Average evidence coverage: **{df.confidence_score.astype(float).mean():.1f}/100** | {crawl_runs} crawl runs | {candidates_n} candidate(s) awaiting review")

tabs = st.tabs(["Overview", "Scholarship explorer", "Live crawler", "Change intelligence", "Evidence & QA"])

with tabs[0]:
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown('<div class="section-title">Verification distribution</div>', unsafe_allow_html=True)
        status_counts = df["verification_status"].value_counts().rename_axis("Verification").reset_index(name="Records")
        st.bar_chart(status_counts.set_index("Verification"), height=240)
        st.markdown('<div class="section-title">Scholarship lifecycle</div>', unsafe_allow_html=True)
        lifecycle = df["current_status"].fillna("REVIEW_REQUIRED").value_counts().rename_axis("Lifecycle").reset_index(name="Records")
        st.bar_chart(lifecycle.set_index("Lifecycle"), height=220)
    with right:
        st.markdown('<div class="section-title">Source ecosystem</div>', unsafe_allow_html=True)
        source_counts = df["source_type"].fillna("Unclassified").value_counts().rename_axis("Source type").reset_index(name="Records")
        st.bar_chart(source_counts.set_index("Source type"), height=240)
        st.markdown('<div class="section-title">Confidence score bands</div>', unsafe_allow_html=True)
        scores = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(0)
        bands = pd.cut(scores, bins=[-1, 49, 74, 94.99, 100], labels=["0-49", "50-74", "75-94", "95-100"])
        band_counts = bands.value_counts(sort=False).rename_axis("Score band").reset_index(name="Records")
        st.bar_chart(band_counts.set_index("Score band"), height=220)
    st.markdown('<div class="section-title">Latest verified opportunities</div>', unsafe_allow_html=True)
    top = df[df.verification_status == "VERIFIED"].sort_values("confidence_score", ascending=False).head(6)
    if len(top):
        st.dataframe(top[["scholarship_name", "provider", "amount_benefit", "closing_date", "current_status", "confidence_score"]],
                     width="stretch", hide_index=True)
    else:
        st.info("No records currently satisfy the strict verification gates.")

with tabs[1]:
    st.markdown('<div class="section-title">Explore the scholarship repository</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([1.5, 1, 1, 1])
    with f1:
        query = st.text_input("Search by scheme, provider, eligibility or keyword", placeholder="e.g. disability, postgraduate, UGC")
    with f2:
        ver_filter = st.multiselect("Verification", sorted(df.verification_status.dropna().unique()), default=sorted(df.verification_status.dropna().unique()))
    with f3:
        life_filter = st.multiselect("Lifecycle", sorted(df.current_status.dropna().unique()), default=sorted(df.current_status.dropna().unique()))
    with f4:
        source_filter = st.multiselect("Source type", sorted(df.source_type.dropna().unique()), default=sorted(df.source_type.dropna().unique()))
    filtered = df.copy()
    if query:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    if ver_filter:
        filtered = filtered[filtered.verification_status.isin(ver_filter)]
    if life_filter:
        filtered = filtered[filtered.current_status.isin(life_filter)]
    if source_filter:
        filtered = filtered[filtered.source_type.isin(source_filter)]
    st.caption(f"Showing {len(filtered)} of {len(df)} records")
    st.dataframe(filtered[["scholarship_name", "provider", "source_type", "amount_benefit", "closing_date", "current_status", "confidence_score", "verification_status"]],
                 width="stretch", hide_index=True, height=330)
    if len(filtered):
        selected_name = st.selectbox("Open a scholarship record", filtered.scholarship_name.tolist())
        record = next(x for x in records if x["scholarship_name"] == selected_name)
        score_rows = read_table(
            "SELECT field_name,field_value,source_url,evidence_excerpt,captured_at,evidence_type,web_capture_ref,document_version "
            "FROM field_evidence WHERE scholarship_id=? ORDER BY id DESC", (record["id"],))
        score, checks, explanation = explain_score(record, score_rows.to_dict("records"))
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.subheader(record["scholarship_name"])
            st.caption(f"{safe_text(record.get('provider'))} ? {safe_text(record.get('source_type'))}")
        with c2:
            st.metric("Evidence score", f"{score:.0f}/100")
        with c3:
            st.metric("Verification", safe_text(record.get("verification_status")))
        st.progress(min(max(score / 100, 0), 1), text=f"Evidence coverage {score:.1f}% - VERIFIED requires >=95 and all mandatory gates")
        detail_tabs = st.tabs(["Details", "Score explanation", "Field evidence", "History"])
        with detail_tabs[0]:
            fields = [
                ("Benefit", "amount_benefit"), ("Eligibility", "eligibility"),
                ("Academic requirements", "academic_requirements"), ("Education level", "education_level"),
                ("Income criteria", "income_criteria"), ("Age criteria", "age_criteria"),
                ("Gender criteria", "gender_criteria"), ("Category criteria", "category_criteria"),
                ("Domicile / state", "domicile_state"), ("Institution criteria", "institution_criteria"),
                ("Opening date", "opening_date"), ("Closing date", "closing_date"),
                ("Documents", "documents_required"), ("Selection", "selection_process"),
                ("Renewal", "renewal_requirements"), ("Current status", "current_status"),
                ("Last verified", "last_verified"), ("Guideline version", "guideline_version"),
            ]
            for idx in range(0, len(fields), 2):
                a, b = st.columns(2)
                for col, (label, key) in zip((a, b), fields[idx:idx+2]):
                    with col:
                        st.markdown(f"**{label}**")
                        st.write(safe_text(record.get(key)))
            st.markdown("**Official source**")
            st.markdown(f"[{safe_text(record.get('official_source_url'))}]({record.get('official_source_url') or '#'})")
            st.markdown("**Scheme guideline**")
            st.markdown(f"[{safe_text(record.get('scheme_guideline_url'))}]({record.get('scheme_guideline_url') or '#'})")
            st.markdown("**Current-cycle source**")
            cycle_url = record.get("current_cycle_source_url") or ""
            if cycle_url:
                st.markdown(f"[{safe_text(cycle_url)}]({cycle_url})")
            else:
                st.write("Not specified")
            st.markdown("**Application URL**")
            st.markdown(f"[{safe_text(record.get('application_url'))}]({record.get('application_url') or '#'})")
        with detail_tabs[1]:
            st.info(explanation)
            gate_rows = [{"Gate": name.replace("_", " ").title(), "Weight": info["weight"],
                          "Result": "PASS" if info["passed"] else "MISSING / FAIL"}
                         for name, info in checks.items()]
            st.dataframe(pd.DataFrame(gate_rows), width="stretch", hide_index=True)
            st.caption("A numerical score alone cannot promote a record. The mandatory source, eligibility, benefit, freshness, traceability and conflict gates must also pass.")
        with detail_tabs[2]:
            if len(score_rows):
                st.dataframe(score_rows, width="stretch", hide_index=True, column_config={
                    "source_url": st.column_config.LinkColumn("Official source", display_text="Open source"),
                })
            else:
                st.warning("No field-level evidence rows are attached to this record yet.")
        with detail_tabs[3]:
            history = read_table("SELECT field_name,old_value,new_value,evidence_date,detected_at,source_url,evidence_text,change_kind FROM change_history WHERE scholarship_id=? ORDER BY evidence_date DESC", (record["id"],))
            if len(history):
                st.dataframe(history, width="stretch", hide_index=True)
            else:
                st.caption("No field-level changes recorded for this scholarship yet.")

with tabs[2]:
    st.markdown('<div class="section-title">Live discovery and extraction</div>', unsafe_allow_html=True)
    st.write("Start from public official portals. Atlas discovers relevant links, respects robots.txt, fetches accessible pages, extracts candidates and stores source snapshots. New candidates remain REVIEW_REQUIRED until a person validates them.")
    defaults = "https://scholarships.gov.in/All-Scholarships\nhttps://www.ugc.gov.in/Home/student_Corner\nhttps://socialjustice.gov.in/schemes"
    seeds_text = st.text_area("Seed portals - one HTTPS URL per line", defaults, height=95)
    crawl_col, status_col = st.columns([1, 2])
    with crawl_col:
        run_crawl = st.button("Run discovery crawl", type="primary", width="stretch")
    with status_col:
        st.caption("Tip: run the crawler twice to inspect persisted page-hash change events. Network, robots.txt and source availability affect live results.")
    if run_crawl:
        seed_urls = [line.strip() for line in seeds_text.splitlines() if line.strip()]
        if not seed_urls:
            st.error("Add at least one public seed URL.")
        else:
            with st.spinner("Discovering and fetching public pages..."):
                result = crawl_seed_sources(seed_urls)
            m1, m2, m3 = st.columns(3)
            m1.metric("Discovered", result["discovered"])
            m2.metric("Fetched", result["fetched"])
            m3.metric("Errors", len(result["errors"]))
            if result["fetched"]:
                st.success("Crawl finished. Inspect extracted candidates below; no candidate is auto-verified.")
            else:
                st.warning("No pages were fetched in this run. Review the errors; blocked or inaccessible pages are not bypassed.")
            if result["errors"]:
                with st.expander("Crawl errors", expanded=False):
                    st.dataframe(pd.DataFrame(result["errors"]), width="stretch", hide_index=True)
            if result["pages"]:
                page_urls = [x["url"] for x in result["pages"]]
                inspect_url = st.selectbox("Inspect a fetched source page", page_urls, key="inspect_live_page")
                page = next(x for x in result["pages"] if x["url"] == inspect_url)
                candidate = extract_structured_candidate(page)
                st.markdown(f"**Page title:** {safe_text(page.get('title'))}")
                st.markdown(f"**Source:** [{page['url']}]({page['url']})")
                st.json(candidate)
    st.markdown("### Review queue")
    candidate_df = read_table("SELECT id,source_url,page_title,extracted_at,review_status FROM extracted_candidates ORDER BY id DESC LIMIT 100")
    if len(candidate_df):
        st.dataframe(candidate_df, width="stretch", hide_index=True, column_config={
            "source_url": st.column_config.LinkColumn("Source URL", display_text="Open source")})
        candidate_id = st.selectbox("Inspect candidate payload", candidate_df.id.tolist())
        candidate_payload = read_table("SELECT candidate_json FROM extracted_candidates WHERE id=?", (int(candidate_id),))
        if len(candidate_payload):
            st.json(json.loads(candidate_payload.iloc[0]["candidate_json"]))
    else:
        st.info("No live candidates have been stored yet. Run a crawl to populate this queue.")
    with st.expander("Import / refresh curated official research dataset"):
        st.warning("This imports the source-reviewed snapshot; it does not promote live crawler candidates automatically.")
        if st.button("Import reviewed dataset", key="import_seed"):
            run_id, count = import_seed_csv(SEED)
            changes = import_official_change_events(ROOT / "data" / "official_change_events.csv")
            st.success(f"Imported {count} records; added {changes} official change events (run {run_id}). Refresh the page to view updated metrics.")

with tabs[3]:
    st.markdown('<div class="section-title">Change and stale-data intelligence</div>', unsafe_allow_html=True)
    history = read_table("SELECT s.scholarship_name,h.field_name,h.old_value,h.new_value,h.evidence_date,h.detected_at,h.source_url,h.evidence_text,h.change_kind FROM change_history h LEFT JOIN scholarships s ON s.id=h.scholarship_id ORDER BY h.evidence_date DESC")
    page_changes = read_table("SELECT url,old_hash,new_hash,detected_at,old_title,new_title,evidence_excerpt FROM page_change_events ORDER BY detected_at DESC")
    a, b = st.columns(2)
    with a:
        st.markdown("**Official / field-level change history**")
        if len(history):
            st.dataframe(history, width="stretch", hide_index=True, column_config={"source_url": st.column_config.LinkColumn("Source", display_text="Open evidence")})
        else:
            st.info("No field-level change events recorded yet.")
    with b:
        st.markdown("**Repeated-crawl page changes**")
        if len(page_changes):
            st.dataframe(page_changes, width="stretch", hide_index=True, column_config={"url": st.column_config.LinkColumn("Changed page", display_text="Open page")})
        else:
            st.info("No page-hash changes recorded yet. Re-crawl the same source after it changes to populate this view.")
    st.markdown("**Stale / expired source register**")
    stale_path = ROOT / "data" / "official_stale_records.csv"
    if stale_path.exists():
        stale = pd.read_csv(stale_path)
        st.dataframe(stale, width="stretch", hide_index=True)
    with st.expander("Import dated official change notices"):
        if st.button("Import official notices", key="import_changes"):
            count = import_official_change_events(ROOT / "data" / "official_change_events.csv")
            st.success(f"Added {count} new official notification events.")

with tabs[4]:
    st.markdown('<div class="section-title">Evidence policy and reproducibility</div>', unsafe_allow_html=True)
    st.markdown("""
**Confidence is evidence coverage, not a probability.** The deterministic rubric totals 100 points. A record is `VERIFIED` only when its score is at least 95 **and** all mandatory gates pass.

| Signal | Weight |
|---|---:|
| Official HTTPS primary source | 15 |
| Scheme-specific official guideline/page | 15 |
| Field-level eligibility evidence | 20 |
| Field-level benefit evidence | 15 |
| Official application URL | 5 |
| Captured application-route evidence | 5 |
| Fresh current-cycle/status evidence (<=180 days) | 10 |
| Traceability across 3+ official fields | 15 |
| Known conflict / non-official evidence | Hard fail / cap below 95 |

The mandatory gates are source authenticity, scheme-specific guideline, eligibility, benefit, current-cycle freshness, traceability and no known conflict. Application URL evidence is scored when available but is not mandatory if no official application link exists. A bare numerical score cannot promote a record.

Missing values remain `Not specified`. Conflicting values remain visible as separate evidence and force review. The crawler does not bypass robots.txt, authentication, CAPTCHA or access restrictions.
""")
    st.markdown("### Data and audit files")
    file_cols = st.columns(3)
    with file_cols[0]:
        st.download_button("Download scholarships CSV", SEED.read_bytes(), file_name="scholarships_seed.csv", mime="text/csv")
    with file_cols[1]:
        evidence_file = ROOT / "data" / "field_evidence.csv"
        st.download_button("Download field evidence", evidence_file.read_bytes(), file_name="field_evidence.csv", mime="text/csv")
    with file_cols[2]:
        with connect() as con:
            db_bytes = DB_PATH.read_bytes() if DB_PATH.exists() else b""
        if db_bytes:
            st.download_button("Download SQLite database", db_bytes, file_name="atlas.db", mime="application/x-sqlite3")
    st.markdown("### Validation commands")
    st.code("python -m pytest -q\npython scripts/validate_package.py\npython scripts/run_local_fixture.py\npython scripts/run_live_crawl.py\nstreamlit run app.py", language="powershell")
    st.caption(f"Database path: {DB_PATH}")
    st.caption("See README.md, FINAL_QA_REPORT.md and docs/TECHNICAL_NOTE.md for the implementation and acceptance limitations.")


