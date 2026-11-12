"""Run a portable local HTTP integration fixture for the crawler."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.crawler import crawl_seed_sources
from src.database import connect


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = b'<html><title>Scholarship Directory</title><a href="/scheme/alpha">Alpha Scholarship</a></html>'
        else:
            body = (b'<html><title>Alpha Scholarship</title><main><h1>Alpha Scholarship</h1>'
                    b'<p>Eligibility: first year undergraduate students.</p>'
                    b'<p>Family income below Rs 2 lakh.</p>'
                    b'<p>Scholarship amount Rs 20,000 per year.</p>'
                    b'<p>Last date 30-11-2026.</p></main></html>')
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with TemporaryDirectory(prefix="atlas_fixture_") as tmp:
        db = str(Path(tmp) / "atlas_fixture.db")
        result = crawl_seed_sources([f"http://127.0.0.1:{server.server_port}/"], 10, db)
        with connect(db) as con:
            snapshots = con.execute("SELECT COUNT(*) FROM page_snapshots").fetchone()[0]
            candidates = con.execute("SELECT COUNT(*) FROM extracted_candidates").fetchone()[0]
        output = {
            "run_time": datetime.now(timezone.utc).isoformat(),
            "seed": "local HTTP fixture",
            "discovered": result["discovered"],
            "fetched": result["fetched"],
            "errors": result["errors"],
            "snapshots_persisted": snapshots,
            "candidates_persisted": candidates,
            "review_status": "REVIEW_REQUIRED",
            "note": "Functional integration fixture, not an external scholarship-source crawl.",
        }
        log = ROOT / "logs" / "local_fixture_crawl.json"
        log.parent.mkdir(exist_ok=True)
        log.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
finally:
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()
