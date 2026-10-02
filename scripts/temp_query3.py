import sys
import hashlib
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.sgd_registration import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT U.COD_USER, U.CCLAVE, E.CEMP_NU_DNI FROM IDOSGD.RHTM_PER_EMPLEADOS E JOIN IDOSGD.SEG_USUARIOS1 U ON E.CEMP_CODEMP = U.CEMP_CODEMP WHERE U.CCLAVE IS NOT NULL")
    
    count = 0
    for row in cur.fetchall():
        user, clave, dni = row
        if clave == hashlib.md5(dni.encode()).hexdigest().upper(): 
            print('Match DNI:', user)
            count += 1
        elif clave == hashlib.md5(user.encode()).hexdigest().upper(): 
            print('Match User:', user)
            count += 1
        elif clave == hashlib.sha256(dni.encode()).hexdigest().upper(): 
            print('Match DNI SHA256:', user)
            count += 1
        elif clave == hashlib.sha256(user.encode()).hexdigest().upper(): 
            print('Match User SHA256:', user)
            count += 1
        elif clave == dni: 
            print('Plain DNI:', user)
            count += 1
        elif clave == hashlib.md5(b"123456").hexdigest().upper():
            print('Match 123456:', user)
            count += 1
            
    print(f'Total matched: {count}')
