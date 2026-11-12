import csv
from datetime import datetime,timezone
from .database import connect,init_db,DB_PATH
def import_official_change_events(csv_path,db_path=DB_PATH):
    init_db(db_path);inserted=0
    with open(csv_path,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            with connect(db_path) as c:
                row=c.execute("SELECT id FROM scholarships WHERE scholarship_name=?",(r["scholarship_name"],)).fetchone()
                if not row: continue
                exists=c.execute("SELECT id FROM change_history WHERE scholarship_id=? AND field_name=? AND old_value=? AND new_value=? AND evidence_date=?",
                    (row["id"],r["field_name"],r["old_value"],r["new_value"],r["evidence_date"])).fetchone()
                if not exists:
                    c.execute("INSERT INTO change_history(scholarship_id,field_name,old_value,new_value,detected_at,source_url,evidence_text,evidence_date,change_kind) VALUES(?,?,?,?,?,?,?,?,?)",
                    (row["id"],r["field_name"],r["old_value"],r["new_value"],datetime.now(timezone.utc).isoformat(),r["source_url"],r["evidence_text"],r["evidence_date"],r["change_kind"]))
                    inserted+=1
    return inserted
