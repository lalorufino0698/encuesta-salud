import os
import pyodbc
from dotenv import load_dotenv

# Cargar el archivo .env
load_dotenv()

# Obtener credenciales del entorno
SGD_DB_HOST = os.getenv("SGD_DB_HOST", "localhost")
SGD_DB_USER = os.getenv("SGD_DB_USER", "")
SGD_DB_PASSWORD = os.getenv("SGD_DB_PASSWORD", "")
SGD_DB_NAME = os.getenv("SGD_DB_NAME", "IDOSGD")

def test_connection():
    print(f"Probando conexión a SQL Server en {SGD_DB_HOST} (Base de datos: {SGD_DB_NAME})...")
    
    # Buscar el driver de SQL Server disponible en la máquina
    drivers = [driver for driver in pyodbc.drivers() if 'SQL Server' in driver]
    if not drivers:
        print("ERROR: No se encontró ningún driver de SQL Server (ODBC) instalado en este equipo.")
        return
        
    driver = drivers[0] # Preferimos el primero que coincida (por ejemplo 'ODBC Driver 17 for SQL Server')
    print(f"Usando driver: {driver}")
    
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SGD_DB_HOST};"
        f"DATABASE={SGD_DB_NAME};"
        f"UID={SGD_DB_USER};"
        f"PWD={SGD_DB_PASSWORD}"
    )
    
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        print("✅ CONEXIÓN EXITOSA!")
        
        # Probar que la tabla existe
        cursor = conn.cursor()
        print("Comprobando existencia de la tabla TDTX_ANI_SIMIL...")
        try:
            # Selecciona solo 1 registro para confirmar que la tabla es accesible
            cursor.execute("SELECT TOP 1 NULEM FROM IDOSGD.TDTX_ANI_SIMIL")
            row = cursor.fetchone()
            print(f"✅ TABLA ACCESIBLE! Registro de prueba obtenido: {row}")
        except Exception as e:
            print(f"⚠️ La conexión a la BD fue exitosa, pero la consulta a la tabla falló: {e}")
            print("Asegúrate de que el usuario tenga permisos sobre la tabla o que el esquema IDOSGD sea correcto.")
        
        conn.close()
    except Exception as e:
        print("❌ ERROR DE CONEXIÓN:")
        print(str(e))

if __name__ == "__main__":
    if not SGD_DB_USER or not SGD_DB_PASSWORD:
        print("Por favor, llena las variables SGD_DB_USER y SGD_DB_PASSWORD en el archivo .env primero.")
    else:
        test_connection()
