import os
import pyodbc
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from dotenv import load_dotenv

def encrypt_sgd_password(plain_text):
    key_string = "SgDPasswordSecretPasswor"
    sha1 = hashlib.sha1()
    sha1.update(key_string.encode('utf-8'))
    key = sha1.digest()[:16] 
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode('utf-8')) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return ct.hex().upper()

load_dotenv()

def get_connection():
    host = os.getenv("SGD_DB_HOST", "localhost")
    user = os.getenv("SGD_DB_USER", "")
    password = os.getenv("SGD_DB_PASSWORD", "")
    dbname = os.getenv("SGD_DB_NAME", "IDOSGD")
    
    drivers = [driver for driver in pyodbc.drivers() if 'SQL Server' in driver]
    if not drivers:
        raise RuntimeError("No se encontró ningún driver de SQL Server (ODBC).")
    
    driver = drivers[0]
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={dbname};"
        f"UID={user};"
        f"PWD={password}"
    )
    return pyodbc.connect(conn_str, timeout=5)

def check_ciudadano(dni: str) -> bool:
    """Verifica si el DNI ya existe como ciudadano en la base de datos SGD."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 NULEM FROM IDOSGD.TDTX_ANI_SIMIL WHERE NULEM = ?", (dni,))
            row = cursor.fetchone()
            return row is not None
    except Exception as e:
        raise RuntimeError(f"Error al verificar ciudadano en SGD: {e}")

def register_ciudadano(dni: str, nombres: str, apellido_paterno: str, apellido_materno: str) -> None:
    """Registra un nuevo ciudadano en SGD."""
    # Usamos valores quemados para UBDEP, UBPRV, UBDIS como en la muestra proporcionada
    ubdep = "14"
    ubprv = "01"
    ubdis = "01"
    dedomicil = ""
    deemail = ""
    detelefo = ""
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO IDOSGD.TDTX_ANI_SIMIL 
                (NULEM, UBDEP, UBPRV, UBDIS, DEAPP, DEAPM, DENOM, DEDOMICIL, DEEMAIL, DETELEFO) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                query, 
                (dni, ubdep, ubprv, ubdis, apellido_paterno, apellido_materno, nombres, dedomicil, deemail, detelefo)
            )
            conn.commit()
    except Exception as e:
        raise RuntimeError(f"Error al registrar ciudadano en SGD: {e}")

def check_empleado(dni: str) -> bool:
    """Verifica si el DNI ya existe como empleado en RHTM_PER_EMPLEADOS."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 CEMP_CODEMP FROM IDOSGD.RHTM_PER_EMPLEADOS WHERE CEMP_NU_DNI = ?", (dni,))
            row = cursor.fetchone()
            return row is not None
    except Exception as e:
        raise RuntimeError(f"Error al verificar empleado en SGD: {e}")

def check_usuario_sgd(username: str) -> bool:
    """Verifica si el nombre de usuario ya existe en SEG_USUARIOS1."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 1 COD_USER FROM IDOSGD.SEG_USUARIOS1 WHERE COD_USER = ?", (username,))
            row = cursor.fetchone()
            return row is not None
    except Exception as e:
        raise RuntimeError(f"Error al verificar usuario en SGD: {e}")

DEPENDENCIAS_SGD = {
    "SCD": "00001", "MP": "00002", "OCI": "00003", "GG": "00004", "GPP": "00005",
    "OTIC": "00005",
    "GAJ": "00006", "GA": "00007", "SGRH": "00008", "SGL": "00009", "SGC": "00010",
    "SGT": "00011", "GDE": "00012", "GIE": "00013", "BE": "00014", "AC": "00015",
    "MPV": "00017", "ST": "00018", "AI": "00019", "PC": "00020", "UFII": "00021",
    "RPT": "00023"
}

def map_dependencia(area: str) -> str:
    """Mapea el nombre o sigla del área a su código de dependencia de 5 dígitos."""
    if not area: return "00001"
    area_upper = area.strip().upper()
    if area_upper in DEPENDENCIAS_SGD:
        return DEPENDENCIAS_SGD[area_upper]
    
    # Búsqueda por coincidencia de texto
    area_lower = area.strip().lower()
    mapping_text = {
        "consejo directivo": "00001", "mesa de partes": "00002", "control institucional": "00003",
        "gerencia general": "00004", "planificacion y presupuesto": "00005", "asesoria juridica": "00006",
        "gerencia de administracion": "00007", "recursos humanos": "00008", "logistica": "00009",
        "contabilidad": "00010", "tesoreria": "00011", "desarrollo educativo": "00012",
        "infraestructura": "00013", "becas": "00014", "archivo": "00015", "transparencia": "00023",
        "integridad": "00021"
    }
    for key, value in mapping_text.items():
        if key in area_lower:
            return value
    return "00001" # Por defecto si no encuentra coincidencia

def registrar_flujo_completo(dni: str, nombres: str, apellido_paterno: str, apellido_materno: str, area: str, username: str, password: str, progress) -> str:
    """Ejecuta el alta completa: Ciudadano (si falta) -> Empleado -> Accesos SGD."""
    # 1. Registrar ciudadano si no existe
    if not check_ciudadano(dni):
        progress("El ciudadano no existe en SGD. Registrando ciudadano...")
        register_ciudadano(dni, nombres, apellido_paterno, apellido_materno)
        progress("Ciudadano registrado correctamente.")
    else:
        progress("El ciudadano ya existe en SGD.")

    # 2. Verificar que no exista como empleado (doble chequeo de seguridad)
    if check_empleado(dni):
        raise ValueError(f"El DNI {dni} ya está registrado como empleado en SGD. No se puede crear duplicado.")
    
    # 3. Mapear dependencia y preparar variables por defecto
    co_depend = map_dependencia(area)
    co_cargo = "0001" # NO ESPECIFICADO
    co_categoria = ""
    co_local = "001" # CAFED
    
    progress(f"Iniciando registro de empleado en SGD (Dependencia: {co_depend})...")
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Parametros del USP
            sql = """
                SET NOCOUNT ON;
                
                DECLARE @CODE INT;
                DECLARE @MESSAGE NVARCHAR(255);
                DECLARE @DATA NVARCHAR(50);
                
                EXEC IDOSGD.USP_SGD_REGISTRAR_EMPLEADO
                    @CEMP_NU_DNI = ?,
                    @CEMP_APEPAT = ?,
                    @CEMP_APEMAT = ?,
                    @CEMP_DENOM = ?,
                    @CEMP_EMAIL = ?,
                    @CEMP_EST_EMP = '1',
                    @CEMP_TIPSEX = 'M',
                    @FEMP_FECNAC = '1990-01-01',
                    @CEMP_CO_DEPEND = ?,
                    @CEMP_CO_CARGO = ?,
                    @CEMP_CO_CATEGORIA = ?,
                    @CEMP_ID_CREA = '00001',
                    @CEMP_CO_LOCAL = ?,
                    @CEMP_DESCRIP = 'REGISTRO AUTOMATICO',
                    @CEMP_TELEFONO = '',
                    @CEMP_EST_NOT = '0',
                    
                    @COD_USER = ?,
                    @CCLAVE = ?,
                    @IN_AD = '0',
                    @CUSER_CRE = 'ADM',
                    
                    @COD_APLICA = '9',
                    @ES_ADMIN = '0',
                    @ES_MP_REG = '0',
                    @ES_MP_TOT = '0',
                    @SEG_USUARIOS_ROLES = '[3]',
                    
                    @CODE = @CODE OUTPUT,
                    @MESSAGE = @MESSAGE OUTPUT,
                    @DATA = @DATA OUTPUT;
                    
                SELECT @CODE as CODE, @MESSAGE as MESSAGE, @DATA as DATA;
            """
            
            cursor.execute(sql, (
                dni, apellido_paterno, apellido_materno, nombres, "", 
                co_depend, co_cargo, co_categoria, co_local, 
                username.upper(), encrypt_sgd_password(password) if password else ""
            ))
            
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("El procedimiento almacenado no devolvió resultados.")
                
            code, message, data = row.CODE, row.MESSAGE, row.DATA
            
            if code != 1:
                raise RuntimeError(f"Error del procedimiento SGD: {message}")
                
            if row and row.CODE == 1:
                # Corregir bugs del SP original:
                # 1. Quitar expiración inmediata de cuenta
                # 2. Pasar el usuario a estado 'A' (Activo) para evitar el bucle de "Contraseña caducada / Debe cambiarla"
                fix_sql = "UPDATE IDOSGD.SEG_USER_APLICA SET FE_DEACT = NULL WHERE COD_USER = ?"
                cursor.execute(fix_sql, (username.upper(),))
                
                fix_sql_2 = "UPDATE IDOSGD.SEG_USUARIOS1 SET ES_USUARIO = 'A' WHERE COD_USER = ?"
                cursor.execute(fix_sql_2, (username.upper(),))
                
                # Insertar los permisos detallados (opciones del aplicativo) basados en los roles asignados
                opc_sql = """
                    INSERT INTO IDOSGD.SEG_USER_APLICA_OPC_C (COD_USER, COD_APLICA, COD_OPC, ES_HABILITADO)
                    SELECT U.COD_USER, R.COD_APLICA, R.COD_OPC, '1'
                    FROM IDOSGD.SEG_USUARIOS_ROLES U
                    JOIN IDOSGD.SEG_ROLES_OPCIONES R ON U.ID_ROL = R.ID_ROL
                    WHERE U.COD_USER = ?
                """
                cursor.execute(opc_sql, (username.upper(),))

            conn.commit()
            progress(f"Registro en SGD completado con éxito (Código Empleado: {data}).")
            return data
            
    except Exception as e:
        raise RuntimeError(f"Error al registrar empleado en SGD: {e}")



def validate_ciudadano(dni: str, progress=lambda message: None) -> dict:
    """Consulta de existencia exclusivamente; no registra ciudadanos ni empleados."""
    if not isinstance(dni, str) or len(dni) != 8 or not dni.isascii() or not dni.isdigit():
        raise ValueError("El DNI debe tener exactamente 8 dígitos.")
    progress("Validando tabla Ciudadano en SGD...")
    try:
        exists = check_ciudadano(dni)
    except RuntimeError as exc:
        raise RuntimeError("No se pudo validar la tabla Ciudadano en SGD. Revisa la conexión e inténtalo nuevamente.") from exc
    message = (
        "Se verificó que el ciudadano existe. Continuaremos con el registro de empleado en la siguiente etapa; por ahora queda pendiente."
        if exists else
        "Se verificó que el ciudadano no existe. Su registro en la tabla Ciudadano queda pendiente."
    )
    progress(message)
    progress("Validación de SGD finalizada. No se realizó ningún INSERT.")
    return {'existe': exists, 'estado': 'ciudadano_existente' if exists else 'ciudadano_no_existe',
            'mensaje': message, 'solo_validacion': True}
