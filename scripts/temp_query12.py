import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM IDOSGD.SEG_USUARIOS1 WHERE COD_USER = 'SOROZCO'")
    columns = [column[0] for column in cur.description]
    for row in cur.fetchall():
        print(dict(zip(columns, row)))
        
    cur.execute("SELECT * FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER = 'SOROZCO'")
    columns2 = [column[0] for column in cur.description]
    for row in cur.fetchall():
        print(dict(zip(columns2, row)))
