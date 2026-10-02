import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 * FROM IDOSGD.SEG_USUARIOS1 WHERE COD_USER = 'ADMIN'")
    columns = [column[0] for column in cur.description]
    print(dict(zip(columns, cur.fetchone())))
