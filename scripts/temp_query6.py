import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.tables WHERE name LIKE '%OPC%'")
    print("OPC Tables:", cur.fetchall())
