import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT TOP 5 * FROM IDOSGD.SEG_ROLES_OPCIONES")
    print("Columns:", [column[0] for column in cur.description])
    print("Data:", cur.fetchall())
