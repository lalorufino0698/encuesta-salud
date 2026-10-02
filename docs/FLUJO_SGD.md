# Flujo previsto de registro SGD

## Estado actual

Solo está habilitada la consulta por DNI de Ciudadano (`IDOSGD.TDTX_ANI_SIMIL`). Las etapas siguientes se muestran como pendientes; no se consulta Empleado ni se ejecuta el procedimiento. No se agregaron rutas de ejecución ni llamadas EXEC, INSERT o COMMIT al flujo activo.

El procedimiento original aportado está conservado sin cambios en `referencias/USP_SGD_REGISTRAR_EMPLEADO.sql.txt`. Es una referencia, no una migración ni un script de arranque.

## Secuencia futura

1. Consultar Ciudadano. Si existe, omitir su alta; si no existe, su registro debe completarse antes del registro de empleado. Si falla la consulta, no interpretar el error como ausencia.
2. Validar DNI en `IDOSGD.RHTM_PER_EMPLEADOS`. Un empleado ya existente detiene el alta: no se soluciona cambiando su identidad ni agregando una letra al usuario.
3. Preparar datos laborales y, cuando se solicite cuenta, validar la disponibilidad del login. Un login ocupado requerirá un ajuste únicamente del usuario de SGD, independiente del de Dominio.
4. Ejecutar en el futuro `IDOSGD.USP_SGD_REGISTRAR_EMPLEADO` con parámetros validados: genera código e inserta empleado, con tipo de empleado 3.
5. Si COD_USER no está vacío, crear SEG_USUARIOS1, SEG_USER_APLICA y SEG_USUARIOS_ROLES.
6. Aplicar configuración adicional solo para los perfiles explícitamente autorizados: ES_ADMIN, ES_MP_REG, ES_MP_TOT. No activar permisos por defecto desde la interfaz.
7. Evaluar CODE, MESSAGE y DATA. Mostrar éxito y código de empleado solo tras confirmación efectiva de la transacción. Con error, detenerse y conservar la separación respecto de Dominio.

## Parámetros para definir antes de habilitar

- Identidad y contacto: CEMP_NU_DNI, CEMP_APEPAT, CEMP_APEMAT, CEMP_DENOM, CEMP_EMAIL, CEMP_TIPSEX, FEMP_FECNAC, CEMP_TELEFONO.
- Datos laborales: CEMP_CO_DEPEND, CEMP_CO_CARGO, CEMP_CO_CATEGORIA, CEMP_CO_LOCAL, CEMP_DESCRIP.
- Estados y auditoría: CEMP_EST_EMP, CEMP_EST_NOT, CEMP_ID_CREA, CUSER_CRE.
- Cuenta: COD_USER, CCLAVE, IN_AD. Confirmar el formato de clave compatible con el aplicativo; el procedimiento recibe CCLAVE y no la cifra.
- Aplicación y permisos: COD_APLICA, ES_ADMIN, ES_MP_REG, ES_MP_TOT, SEG_USUARIOS_ROLES.
- Salidas: CODE, MESSAGE, DATA.

## Observaciones sobre el SQL recibido

- El encabezado selecciona la base SGD. Confirmar la base configurada antes de habilitar; el código local conserva su configuración actual.
- La transacción del procedimiento abarca empleado y accesos. No inserta Ciudadano, por lo que no garantiza atomicidad conjunta con un alta previa de Ciudadano.
- `OPENJSON(@SEG_USUARIOS_ROLES)` seguido de `CAST(value AS SMALLINT)` requiere valores escalares convertibles a entero, por ejemplo `[1,2]`. El ejemplo `[{"idRol":1}]` no coincide con ese código. Confirmar contrato con el aplicativo original.
- No hay validación explícita de COD_USER duplicado en el procedimiento recibido. Debe definirse la consulta de disponibilidad y el tratamiento de una eventual colisión concurrente/constraint antes de habilitar el alta.
- MAX(CEMP_CODEMP)+1 puede producir colisiones concurrentes, fallar con valores no numéricos o devolver NULL con una tabla vacía. Revisar también el límite de cinco dígitos.
- El CATCH ejecuta RAISERROR antes de ROLLBACK. Revisar el manejo de errores/transacciones antes de afirmar una garantía incondicional de rollback.
- La dependencia de Mesa de Partes se obtiene mediante subconsulta escalar. Confirmar que exista una sola coincidencia.

Estas observaciones no modifican el procedimiento original ni habilitan escrituras.
