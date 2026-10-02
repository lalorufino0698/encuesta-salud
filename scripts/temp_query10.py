import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT TOP 5 COD_USER, ES_USUARIO, DFE_MOD_CLAVE, DFEC_CRE FROM IDOSGD.SEG_USUARIOS1 WHERE ES_USUARIO = 'A'")
    print("Activos:", cur.fetchall())
    
    cur.execute("SELECT TOP 5 COD_USER, COD_APLICA, FE_ACTIVO, FE_DEACT FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER IN (SELECT TOP 5 COD_USER FROM IDOSGD.SEG_USUARIOS1 WHERE ES_USUARIO = 'A')")
    print("Aplica:", cur.fetchall())
