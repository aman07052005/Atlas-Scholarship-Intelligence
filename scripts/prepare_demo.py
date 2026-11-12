from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.database import init_db
from src.crawler import import_seed_csv
from src.history import import_official_change_events
init_db()
run,count=import_seed_csv(ROOT/"data"/"scholarships_seed.csv")
changes=import_official_change_events(ROOT/"data"/"official_change_events.csv")
print(f"Loaded {count} scholarship records and {changes} official change events (run {run}).")
