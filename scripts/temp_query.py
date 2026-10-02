import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT CO_DEPENDENCIA, DE_DEPENDENCIA FROM IDOSGD.RHTM_DEPENDENCIA WHERE DE_DEPENDENCIA LIKE '%TECNOLOGIA%' OR DE_DEPENDENCIA LIKE '%OTIC%' OR DE_DEPENDENCIA LIKE '%INFORMACION%'")
    print("Dependencias:", cur.fetchall())
    
    cur.execute("SELECT * FROM IDOSGD.SEG_USUARIOS_ROLES WHERE COD_USER = 'sorozco' OR COD_USER = 'SOROZCO'")
    print("Roles para sorozco:", cur.fetchall())
