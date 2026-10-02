import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path para poder importar 'app'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.sgd_registration import get_connection

def delete_test_user(dni: str):
    if not dni or len(dni) != 8 or not dni.isdigit():
        print("Error: El DNI debe tener 8 dígitos numéricos.")
        return

    print(f"Buscando registros asociados al DNI: {dni}...")
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Obtener CEMP_CODEMP (El identificador del empleado)
            cursor.execute("SELECT CEMP_CODEMP FROM IDOSGD.RHTM_PER_EMPLEADOS WHERE CEMP_NU_DNI = ?", (dni,))
            emp_row = cursor.fetchone()
            
            # 2. Buscar ciudadano
            cursor.execute("SELECT NULEM FROM IDOSGD.TDTX_ANI_SIMIL WHERE NULEM = ?", (dni,))
            citizen_row = cursor.fetchone()

            if not emp_row and not citizen_row:
                print("No se encontraron registros de Empleado ni Ciudadano con ese DNI.")
                return
            
            cemp_codemp = emp_row.CEMP_CODEMP if emp_row else None
            cod_user = None
            
            if cemp_codemp:
                cursor.execute("SELECT COD_USER FROM IDOSGD.SEG_USUARIOS1 WHERE CEMP_CODEMP = ?", (cemp_codemp,))
                user_row = cursor.fetchone()
                if user_row:
                    cod_user = user_row.COD_USER
            
            print("\nIniciando eliminación (esto no se puede deshacer)...")
            
            # El borrado se hace de "hijos a padres" para evitar problemas de Foreign Keys
            if cod_user:
                print(f"[-] Borrando roles y accesos del usuario '{cod_user}'...")
                cursor.execute("DELETE FROM IDOSGD.SEG_USER_APLICA_OPC_C WHERE COD_USER = ?", (cod_user,))
                cursor.execute("DELETE FROM IDOSGD.SEG_USUARIOS_ROLES WHERE COD_USER = ?", (cod_user,))
                cursor.execute("DELETE FROM IDOSGD.SEG_USER_APLICA WHERE COD_USER = ?", (cod_user,))
                cursor.execute("DELETE FROM IDOSGD.TDTR_PERMISOS WHERE CO_USE = ?", (cod_user,))
                
            if cemp_codemp:
                print(f"[-] Borrando credenciales del usuario asociado al empleado '{cemp_codemp}'...")
                cursor.execute("DELETE FROM IDOSGD.SEG_USUARIOS1 WHERE CEMP_CODEMP = ?", (cemp_codemp,))
                
                print(f"[-] Borrando configuraciones y registro del empleado '{cemp_codemp}'...")
                cursor.execute("DELETE FROM IDOSGD.TDTX_CONFIG_EMP WHERE CO_EMP = ?", (cemp_codemp,))
                cursor.execute("DELETE FROM IDOSGD.TDTR_PERMISO_MP WHERE CO_EMP = ?", (cemp_codemp,))
                cursor.execute("DELETE FROM IDOSGD.RHTM_PER_EMPLEADOS WHERE CEMP_CODEMP = ?", (cemp_codemp,))
            
            if citizen_row:
                print(f"[-] Borrando al ciudadano (DNI: {dni})...")
                cursor.execute("DELETE FROM IDOSGD.TDTX_ANI_SIMIL WHERE NULEM = ?", (dni,))

            conn.commit()
            print("\n¡Borrado exitoso! Los registros de prueba han sido eliminados del SGD.")

    except Exception as e:
        print(f"\n[X] Error al intentar borrar el usuario: {e}")

if __name__ == "__main__":
    print("=== SCRIPT DE LIMPIEZA DE USUARIOS DE PRUEBA SGD ===")
    dni_input = input("Ingresa el DNI del usuario de prueba que deseas eliminar: ").strip()
    delete_test_user(dni_input)
