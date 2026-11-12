from pathlib import Path
import csv,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
errors=[]
for p in ROOT.rglob('*.py'):
    try: compile(p.read_text(encoding='utf-8-sig'),str(p),'exec')
    except Exception as e: errors.append(f'syntax {p}: {e}')
required=['data/scholarships_seed.csv','data/field_evidence.csv','data/official_source_register.csv','data/official_change_events.csv','data/official_stale_records.csv','src/database.py','src/crawler.py','src/verification.py','app.py','schema.sql','.streamlit/config.toml','docs/TECHNICAL_NOTE.md','docs/DEMO_WALKTHROUGH.md','docs/SCHEME_VERIFICATION_MATRIX.md','logs/live_crawl_latest.json','logs/local_fixture_crawl.json']
for f in required:
    if not (ROOT/f).exists(): errors.append(f'missing {f}')
with open(ROOT/'data'/'scholarships_seed.csv',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
if len(rows)<20: errors.append('less than 20 scholarship records')
names=[r['scholarship_name'] for r in rows]
if len(names)!=len(set(names)): errors.append('duplicate scholarship names')
with open(ROOT/'data'/'field_evidence.csv',encoding='utf-8-sig',newline='') as f: ev=list(csv.DictReader(f))
if len(ev)<50: errors.append('field evidence count below 50')
with open(ROOT/'data'/'official_source_register.csv',encoding='utf-8-sig',newline='') as f: source_rows=list(csv.DictReader(f))
if len(source_rows)<15: errors.append('fewer than 15 official primary source entries')
unique_official_urls = {x.get('official_url', '').strip().rstrip('/') for x in source_rows if x.get('official_url', '').strip()}
if len(unique_official_urls)<15: errors.append(f'fewer than 15 distinct official primary-source URLs ({len(unique_official_urls)})')
with open(ROOT/'data'/'official_stale_records.csv',encoding='utf-8-sig',newline='') as f: stale_rows=list(csv.DictReader(f))
if len(stale_rows)<2: errors.append('fewer than 2 source-linked stale/expired examples')
for x in ev:
    if not x.get('source_url') or not x.get('evidence_excerpt'):
        errors.append('evidence row missing source URL or excerpt');break

# Count distinct scholarship records backed by at least one allow-listed official evidence URL.
from src.verification import is_official_url
source_evidence_by_name = {}
for item in ev:
    source_evidence_by_name.setdefault(item.get('scholarship_name', ''), []).append(item)
official_backed = [r for r in rows if is_official_url(r.get('official_source_url', '')) and
                   any(is_official_url(e.get('source_url', '')) for e in source_evidence_by_name.get(r.get('scholarship_name', ''), []))]
if len(official_backed) < 15:
    errors.append(f'only {len(official_backed)} scholarship records have official primary-source evidence; minimum 15')

# Independently count distinct scheme-specific primary URLs actually assigned to records.
from urllib.parse import urlparse
scheme_specific_urls = {
    r.get('official_source_url', '').strip().rstrip('/')
    for r in rows
    if r.get('official_source_url', '').strip()
    and urlparse(r.get('official_source_url', '')).path.lower()
        not in ('', '/', '/all-scholarships', '/home', '/schemes')
}
if len(scheme_specific_urls) < 15:
    errors.append(f'only {len(scheme_specific_urls)} distinct scheme-specific primary URLs are assigned to records; minimum 15')
# Recompute confidence using the actual import pipeline; do not trust flat CSV labels alone.
from src.crawler import import_seed_csv
from src.history import import_official_change_events
from src.database import connect
with tempfile.TemporaryDirectory() as td:
    db=Path(td)/'validation.db'
    import_seed_csv(ROOT/'data'/'scholarships_seed.csv',str(db))
    changes=import_official_change_events(ROOT/'data'/'official_change_events.csv',str(db))
    with connect(str(db)) as c:
        total=c.execute('select count(*) from scholarships').fetchone()[0]
        verified=c.execute("select count(*) from scholarships where verification_status='VERIFIED' and confidence_score>=95").fetchone()[0]
        distinct=c.execute('select count(distinct source_type) from scholarships').fetchone()[0]
        history=c.execute('select count(*) from change_history').fetchone()[0]
        cols={r[1] for r in c.execute('PRAGMA table_info(scholarships)')}
        if 'current_cycle_source_url' not in cols: errors.append('current_cycle_source_url missing from database schema')
        cycle_count=c.execute("SELECT COUNT(*) FROM scholarships WHERE current_cycle_source_url IS NOT NULL AND current_cycle_source_url!=''").fetchone()[0]
    if total<20: errors.append('database import below 20 records')
    if cycle_count < 20: errors.append(f'only {cycle_count} records have a separate current-cycle source URL')
    if verified<10: errors.append(f'only {verified} records meet VERIFIED threshold (minimum 10)')
    if distinct<3: errors.append('fewer than 3 source types')
    if changes<2 or history<2: errors.append('fewer than 2 official change events')
if errors:
    print('\n'.join(errors));sys.exit(1)
print(f'PASS: {total} unique records; {verified} VERIFIED ≥95; {len(official_backed)} official-evidence-backed records; {len(scheme_specific_urls)} distinct scheme-specific primary URLs; {len(ev)} field evidence rows; {changes} official changes; {distinct} source types; Python syntax valid.')
