import sys
import hashlib
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT U.COD_USER, U.CCLAVE, E.CEMP_NU_DNI FROM IDOSGD.RHTM_PER_EMPLEADOS E JOIN IDOSGD.SEG_USUARIOS1 U ON E.CEMP_CODEMP = U.CEMP_CODEMP WHERE U.CCLAVE IS NOT NULL")
    
    for row in cur.fetchmany(5):
        user, clave, dni = row
        print(f"User: {user}, DNI: {dni}, CLAVE: {clave}")
        print(f"MD5(DNI): {hashlib.md5(dni.encode()).hexdigest().upper()}")
        print(f"MD5(USER+DNI): {hashlib.md5((user+dni).encode()).hexdigest().upper()}")
        print(f"MD5(DNI+USER): {hashlib.md5((dni+user).encode()).hexdigest().upper()}")
