import csv,hashlib,re
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
import time
_ROBOTS_CACHE={}
_LAST_FETCH=0.0

from .database import connect,init_db,DB_PATH
from .verification import confidence_breakdown,classify_verification,lifecycle_status,is_official_url
HEADERS={"User-Agent":"AtlasScholarshipIntelligence/1.1 (educational research crawler; contact: repository maintainer)"}
def _robots_allowed(url):
    from urllib.parse import urlsplit
    parts=urlsplit(url);origin=f"{parts.scheme}://{parts.netloc}"
    if origin not in _ROBOTS_CACHE:
        robots_url=origin+"/robots.txt"
        try:
            response=requests.get(robots_url,headers=HEADERS,timeout=10)
            if response.status_code >= 500:
                raise RuntimeError(f"robots.txt unavailable (HTTP {response.status_code}); refusing crawl")
            parser=RobotFileParser();parser.set_url(robots_url)
            parser.parse(response.text.splitlines() if response.status_code==200 else [])
            _ROBOTS_CACHE[origin]=parser
        except Exception as exc:
            raise RuntimeError(f"Could not verify robots.txt for {origin}; refusing crawl: {exc}") from exc
    return _ROBOTS_CACHE[origin].can_fetch(HEADERS["User-Agent"],url)
def fetch_page(url):
    global _LAST_FETCH
    if not _robots_allowed(url):
        raise PermissionError(f"robots.txt disallows crawler access to {url}")
    wait=max(0.0,0.5-(time.monotonic()-_LAST_FETCH))
    if wait:time.sleep(wait)
    response=requests.get(url,headers=HEADERS,timeout=20);response.raise_for_status()
    _LAST_FETCH=time.monotonic()
    return response.content,response.url,response.status_code,response.headers.get("Content-Type","")
def discover_links(seed_url,max_links=60):
    raw,final,_,content_type=fetch_page(seed_url)
    html=raw.decode("utf-8",errors="replace")
    soup=BeautifulSoup(html,"html.parser");found=[];seen=set()
    for a in soup.select("a[href]"):
        url=urljoin(final,a["href"]).split("#")[0].strip();p=urlparse(url)
        path_parts=[part.lower() for part in p.path.split("/") if part]
        if p.scheme not in ("http","https") or not p.netloc or url in seen:continue
        if any(part in {"null", "undefined"} for part in path_parts):continue
        if p.path.rstrip("/").lower() == "/institutes":continue
        if p.username or p.password:continue
        label=" ".join(a.get_text(" ",strip=True).split())
        if re.search(r"scholar|fund|fellow|education|student|scheme|guideline|apply",label+" "+url,re.I):
            seen.add(url);found.append({"url":url,"label":label,"discovered_from":final})
    return found[:max_links]
def extract_page(url):
    """Fetch and normalize a page/PDF without treating its filename as a scheme title."""
    raw,final,status,content_type=fetch_page(url)
    is_pdf = "application/pdf" in content_type.lower() or raw[:4] == b"%PDF"
    headings=[]
    if is_pdf:
        try:
            from io import BytesIO
            from pypdf import PdfReader
            reader=PdfReader(BytesIO(raw))
            page_text=[]
            for page in reader.pages[:12]:
                page_text.append(page.extract_text() or "")
            text="\n".join(page_text)
            metadata_title=""
            try: metadata_title=str((reader.metadata or {}).title or "").strip()
            except Exception: pass
            # Metadata is used only when it is descriptive, never the URL filename.
            title=metadata_title if metadata_title and not metadata_title.lower().endswith(".pdf") else ""
            headings=[line.strip() for line in text.splitlines() if line.strip()][:40]
        except ImportError as exc:
            raise RuntimeError("PDF source found but pypdf is not installed; install requirements.txt") from exc
    else:
        soup=BeautifulSoup(raw.decode("utf-8",errors="replace"),"html.parser")
        for node in soup(["script","style","noscript","nav","footer","header","form","aside"]):
            node.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        headings=[x.get_text(" ",strip=True) for x in soup.select("h1,h2,h3") if x.get_text(" ",strip=True)]
        main=soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|main",re.I)) or soup.body or soup
        # Preserve paragraph/list boundaries so the extractor can reject menu-like fragments.
        chunks=[]
        for node in main.find_all(["h1","h2","h3","p","li","td","th"]):
            value=" ".join(node.get_text(" ",strip=True).split())
            if value and len(value)>8:
                chunks.append(value)
        text="\n".join(chunks) if chunks else "\n".join(main.stripped_strings)
    text="\n".join(line.strip() for line in text.splitlines() if line.strip())
    return {"url":final,"title":title,"headings":headings,"text":text[:50000],"status":status,
            "content_type":content_type,"is_pdf":is_pdf}

def _hash(r):
    keys=("scholarship_name","provider","amount_benefit","eligibility","closing_date","current_status")
    return hashlib.sha256(repr(sorted((k,r.get(k,"")) for k in keys)).encode()).hexdigest()
def upsert_record(r,db_path=DB_PATH,run_id=None,source_evidence=None):
    init_db(db_path);now=datetime.now(timezone.utc).isoformat()
    r=dict(r);r.setdefault("observed_status","REVIEW_REQUIRED")
    evidence_rows=source_evidence or []
    score,checks=confidence_breakdown(r,evidence_rows)
    status=classify_verification(score,checks)
    life=lifecycle_status({"closing_date":r.get("closing_date"),"observed_status":r.get("current_status") or r.get("observed_status")})
    fields=["provider","source_type","official_source_url","application_url","amount_benefit","eligibility","academic_requirements","education_level","income_criteria","age_criteria","gender_criteria","category_criteria","domicile_state","institution_criteria","opening_date","closing_date","documents_required","selection_process","renewal_requirements","current_cycle_source_url"]
    with connect(db_path) as c:
        old=c.execute("SELECT * FROM scholarships WHERE scholarship_name=?",(r["scholarship_name"],)).fetchone()
        if old is None:
            cols=["scholarship_name"]+fields+["current_status","confidence_score","verification_status","last_verified","evidence","record_hash","created_at","updated_at","scheme_guideline_url","guideline_version","verification_basis","source_conflict","current_cycle_source_url"]
            vals=[r.get(k,"") for k in ["scholarship_name"]+fields]+[life,score,status,now,r.get("evidence",""),_hash(r),now,now,r.get("scheme_guideline_url"),r.get("guideline_version"),r.get("verification_basis"),r.get("source_conflict","false"),r.get("current_cycle_source_url")]
            c.execute(f"INSERT INTO scholarships({','.join(cols)}) VALUES({','.join('?' for _ in cols)})",vals)
            sid=c.execute("SELECT id FROM scholarships WHERE scholarship_name=?",(r["scholarship_name"],)).fetchone()["id"]
        else:
            sid=old["id"]
            for field in ["amount_benefit","eligibility","closing_date","current_status","application_url","official_source_url"]:
                new=str(r.get(field,"") or "");prev=str(old[field] or "")
                if new and prev and new!=prev:
                    c.execute("INSERT INTO change_history(scholarship_id,field_name,old_value,new_value,detected_at,source_url,evidence_text,evidence_date,run_id,change_kind) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (sid,field,prev,new,now,r.get("official_source_url"),r.get("evidence"),r.get("evidence_date"),run_id,"LIVE_OBSERVED"))
            c.execute("UPDATE scholarships SET "+",".join(f"{k}=?" for k in fields)+",current_status=?,confidence_score=?,verification_status=?,last_verified=?,evidence=?,record_hash=?,updated_at=?,scheme_guideline_url=?,guideline_version=?,verification_basis=?,source_conflict=?,current_cycle_source_url=? WHERE id=?",
            [r.get(k,"") for k in fields]+[life,score,status,now,r.get("evidence",""),_hash(r),now,r.get("scheme_guideline_url"),r.get("guideline_version"),r.get("verification_basis"),r.get("source_conflict","false"),r.get("current_cycle_source_url"),sid])
        if source_evidence:
            c.execute("DELETE FROM field_evidence WHERE scholarship_id=? AND evidence_type='OFFICIAL_RESEARCH_CAPTURE'",(sid,))
            for item in source_evidence:
                c.execute("INSERT INTO field_evidence(scholarship_id,field_name,field_value,source_url,evidence_excerpt,captured_at,evidence_type,web_capture_ref,document_version) VALUES(?,?,?,?,?,?,?,?,?)",
                (sid,item["field"],item["value"],item["url"],item["excerpt"],now,item.get("type","PRIMARY"),item.get("web_capture_ref"),item.get("document_version")))
        return sid,score,status
def import_seed_csv(csv_path,db_path=DB_PATH):
    """Import curated records with their paired field evidence.

    Evidence can fill an explicitly unknown seed value, but it never silently
    overwrites a populated value. Conflicting evidence is retained and forces review.
    """
    import json
    from pathlib import Path
    init_db(db_path); now=datetime.now(timezone.utc).isoformat()
    root=Path(csv_path).resolve().parent
    evidence_path=root/"field_evidence.csv"
    evidence_by_name={}
    if evidence_path.exists():
        with open(evidence_path,encoding="utf-8-sig",newline="") as ef:
            for item in csv.DictReader(ef):
                evidence_by_name.setdefault(item["scholarship_name"],[]).append({
                    "field":item.get("field_name",""),"value":item.get("field_value",""),
                    "url":item.get("source_url",""),"excerpt":item.get("evidence_excerpt",""),
                    "type":("USER_SUPPLIED_SCREENSHOT" if str(item.get("web_capture_ref", "")).startswith("user_supplied_") else "OFFICIAL_RESEARCH_CAPTURE"),"web_capture_ref":item.get("web_capture_ref"),
                    "document_version":item.get("document_version"),"captured_at":item.get("captured_on")})
    with connect(db_path) as c:
        run=c.execute("INSERT INTO crawl_runs(started_at,seed_url) VALUES(?,?)",
                      (now,"curated-official-source-research")).lastrowid
    count=0
    with open(csv_path,encoding="utf-8-sig",newline="") as f:
        for raw in csv.DictReader(f):
            row={str(k).strip().lstrip("* ").replace("**", ""): (str(v).replace("\\:", ":").replace("\\.", ".") if v is not None else "") for k,v in raw.items()}
            ev=evidence_by_name.get(row.get("scholarship_name", ""),[])
            by_field={}
            for item in ev:
                by_field.setdefault(item["field"],[]).append(item)
            # Use source-backed values only when the curated cell is blank/unknown.
            for field in ("amount_benefit","eligibility","income_criteria","closing_date","opening_date","renewal_requirements"):
                current=str(row.get(field," ") or "").strip().lower()
                candidates=by_field.get(field,[])
                distinct={x["value"].strip() for x in candidates if x.get("value","").strip()}
                if current in {"", "not specified", "not specified in nsp listing", "not specified in listing", "not specified in reviewed official listing"}:
                    if len(distinct)==1:
                        row[field]=next(iter(distinct))
                    elif len(distinct)>1:
                        row["source_conflict"]="true"
                # Multiple distinct official amount captures are a conflict, not a
                # reason to choose the newest-looking value without a version rule.
                if field == "amount_benefit" and len(distinct)>1:
                    row["source_conflict"]="true"
            # Explicit evidence conflict flags always survive import.
            score, _ = confidence_breakdown(row,ev)
            upsert_record(row,db_path,run,ev)
            count+=1
    with connect(db_path) as c:
        c.execute("UPDATE crawl_runs SET finished_at=?,discovered_count=?,inserted_count=? WHERE id=?",
                  (datetime.now(timezone.utc).isoformat(),count,count,run))
    return run,count

def crawl_seed_sources(seed_urls,max_links=60,db_path=DB_PATH):
    """Crawl public seed portals defensively; one bad URL must not abort a run."""
    import json
    from .extractor import extract_structured_candidate
    init_db(db_path)
    discovered=[];fetched=[];errors=[]
    inserted_count=0;updated_count=0
    started=datetime.now(timezone.utc).isoformat()
    with connect(db_path) as c:
        c.execute("PRAGMA busy_timeout=30000")
        run_id=c.execute("INSERT INTO crawl_runs(started_at,seed_url) VALUES(?,?)",(started,";".join(seed_urls))).lastrowid

    # Discover links independently. A failed seed is recorded and the remaining seeds continue.
    for seed in seed_urls:
        try:
            links=discover_links(seed,max_links)
            discovered.extend(links)
            with connect(db_path) as c:
                c.executemany(
                    "INSERT OR IGNORE INTO discovered_urls(url,discovered_from,discovered_at,crawl_status) VALUES(?,?,?,?)",
                    [(x["url"],x["discovered_from"],datetime.now(timezone.utc).isoformat(),"DISCOVERED") for x in links]
                )
        except Exception as e:
            errors.append({"url":seed,"stage":"discover","error":f"{type(e).__name__}: {e}"})

    # De-duplicate discovered URLs and fetch one by one. HTTP errors (including 404)
    # are normal crawl outcomes, not fatal application exceptions.
    unique=[];seen=set()
    for item in discovered:
        if item["url"] not in seen:
            seen.add(item["url"]);unique.append(item)
    for item in unique[:max_links]:
        url=item["url"]
        try:
            page=extract_page(url)
            candidate=extract_structured_candidate(page)
            stamp=datetime.now(timezone.utc).isoformat()
            page_hash=hashlib.sha256(page["text"].encode()).hexdigest()
            with connect(db_path) as c:
                previous=c.execute("SELECT content_hash,page_title,extracted_text FROM page_snapshots WHERE url=? AND http_status BETWEEN 200 AND 299 AND content_hash<>'' ORDER BY id DESC LIMIT 1",(page["url"],)).fetchone()
                c.execute("UPDATE discovered_urls SET crawl_status='FETCHED',page_title=?,extracted_at=? WHERE url=?",(page["title"],stamp,url))
                c.execute("INSERT INTO page_snapshots(url,fetched_at,content_hash,page_title,extracted_text,http_status) VALUES(?,?,?,?,?,?)",
                    (page["url"],stamp,page_hash,page["title"],page["text"],page["status"]))
                if previous and previous["content_hash"] != page_hash:
                    old_text=str(previous["extracted_text"] or "")
                    new_text=str(page["text"] or "")
                    # Store a compact auditable diff excerpt, not an invented field value.
                    excerpt=("Previous: "+old_text[:450]+"\nCurrent: "+new_text[:450])[:1000]
                    c.execute("INSERT INTO page_change_events(url,old_hash,new_hash,detected_at,old_title,new_title,evidence_excerpt,run_id) VALUES(?,?,?,?,?,?,?,?)",
                        (page["url"],previous["content_hash"],page_hash,stamp,previous["page_title"],page["title"],excerpt,run_id))
                review_status="REVIEW_REQUIRED" if candidate.get("is_scheme_candidate") else "NOT_A_SCHEME"
                existing_candidate=c.execute(
                    "SELECT 1 FROM extracted_candidates WHERE source_url=?", (page["url"],)
                ).fetchone()
                c.execute("""
                    INSERT INTO extracted_candidates(source_url,page_title,candidate_json,extracted_at,review_status)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(source_url) DO UPDATE SET
                      page_title=excluded.page_title,
                      candidate_json=excluded.candidate_json,
                      extracted_at=excluded.extracted_at,
                      review_status=excluded.review_status
                """, (page["url"],page["title"],json.dumps(candidate,ensure_ascii=False),stamp,review_status))
                if existing_candidate:
                    updated_count += 1
                else:
                    inserted_count += 1
            fetched.append(page)
        except Exception as e:
            message=f"{type(e).__name__}: {e}"
            errors.append({"url":url,"stage":"fetch_or_extract","error":message})
            # Persist the failure separately; retry transient SQLite locks rather than
            # masking the original HTTP/robots/network error with 'database is locked'.
            try:
                with connect(db_path) as c:
                    c.execute("UPDATE discovered_urls SET crawl_status=? WHERE url=?",("ERROR: "+message[:180],url))
                    c.execute("INSERT INTO page_snapshots(url,fetched_at,content_hash,page_title,extracted_text,http_status,error) VALUES(?,?,?,?,?,?,?)",
                        (url,datetime.now(timezone.utc).isoformat(),"","","",None,message[:1000]))
            except Exception as db_error:
                errors.append({"url":url,"stage":"persist_error","error":f"{type(db_error).__name__}: {db_error}"})

    with connect(db_path) as c:
        c.execute("UPDATE crawl_runs SET finished_at=?,discovered_count=?,fetched_count=?,inserted_count=?,updated_count=?,errors=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(),len(unique),len(fetched),inserted_count,updated_count,json.dumps(errors,ensure_ascii=False),run_id))
    return {"run_id":run_id,"discovered":len(unique),"fetched":len(fetched),
            "inserted":inserted_count,"updated":updated_count,"pages":fetched,"errors":errors}
