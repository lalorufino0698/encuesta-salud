import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.objects WHERE type IN ('P') AND (name LIKE '%LOGIN%' OR name LIKE '%VALIDA%')")
    print("SPs:", cur.fetchall())
