import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER = 'EOROZCO'")
    print("EOROZCO:", cur.fetchall())
    
    cur.execute("SELECT TOP 1 * FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER = 'ADMIN'")
    print("ADMIN:", cur.fetchall())
