import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM IDOSGD.SEG_APLICA")
        print("Apps:", cur.fetchall())
    except Exception as e:
        print("Error SEG_APLICA:", e)
        
    try:
        cur.execute("SELECT * FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER = 'EOROZCO'")
        print("EOROZCO Apps:", cur.fetchall())
    except Exception as e:
        print("Error SEG_USER_APLICA:", e)
        
    try:
        cur.execute("SELECT * FROM IDOSGD.SEG_APLICA_OPC")
        print("OPCiones de aplicacion (M01, etc):", cur.fetchmany(5))
    except Exception as e:
        print("Error SEG_APLICA_OPC:", e)
