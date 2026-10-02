import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.objects WHERE type IN ('FN', 'IF', 'TF', 'P') AND name LIKE '%hash%' OR name LIKE '%pwd%' OR name LIKE '%clave%' OR name LIKE '%pass%'")
    print("Objects:", cur.fetchall())
