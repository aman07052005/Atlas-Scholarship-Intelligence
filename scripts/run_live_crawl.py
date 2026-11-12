from pathlib import Path
import sys
import json
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.crawler import crawl_seed_sources
started=datetime.now(timezone.utc).isoformat()
seeds=["https://scholarships.gov.in/All-Scholarships","https://www.ugc.gov.in/Home/student_Corner","https://socialjustice.gov.in/schemes","https://tribal.nic.in/Scholarship.aspx"]
result=crawl_seed_sources(seeds,max_links=60)
log={"started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"seed_urls":seeds,
     "discovered":result["discovered"],"fetched":result["fetched"],"errors":result["errors"],
     "note":"This log is genuine runtime output. A zero-fetch result must be reported as a network/site-access failure, not as a successful crawl."}
out=ROOT/"logs"/"live_crawl_latest.json";out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(log,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(log,indent=2,ensure_ascii=False))
