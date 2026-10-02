# Prueba de solicitudes PDF → JSON

Los mensajes de WhatsApp pueden incluir el **área en la cuarta línea**, después del usuario (por ejemplo, `logistica` o `Área: Logística`). Se conserva por persona y se utiliza en `department` de cada insert. Agrega la clave `LOGISTICA` con el grupo real en tu mapa local; la búsqueda ignora acentos y mayúsculas. No se inventa un grupo cuando falta esa equivalencia. Un mensaje como «solo dominio x ahora» no se toma como área.

En **Texto plano**, también puedes pegar mensajes de WhatsApp con DNI, nombre completo y usuario en tres líneas. Se ignoran los encabezados de hora/remitente y se consolidan registros idénticos repetidos. Marca **Dominio**, **SGD** o ambos: la selección manual se aplica a todos los usuarios del texto y define `inserts_simulados`, uno por servicio seleccionado. No se generan inserts de SIGA/SIAF. Sin datos suficientes, el área, grupo y separación de nombres quedan pendientes de revisión. Las tablas pegadas también admiten esta selección.

El extractor detecta automáticamente el modelo español local en `data/tessdata/spa.traineddata`. Si se define `TESSDATA_PREFIX`, esa ruta tiene prioridad. El modelo se obtiene del repositorio oficial `tesseract-ocr/tessdata_fast` y no se incluye en Git. No hace falta definir la variable cuando se usa la ubicación local del proyecto.

También admite capturas **PNG y JPG**: selecciona la imagen o pégala con **Ctrl+V** en la página y pulsa extraer. En consola se puede pasar la ruta de la imagen a `simulate_domain.py`. Incluye el bloque DE y la tabla completa en una captura legible. Las imágenes siempre requieren OCR en español; si falta su configuración se muestra un error. Los resultados OCR quedan pendientes de revisión. La conversión y el manejo de errores están cubiertos por pruebas; la precisión sobre capturas reales debe validarse con OCR instalado.

La extraccion se ejecuta aparte del sistema de encuestas y no requiere MySQL ni conexion a AD. El INSERT extraido es un objeto de simulacion dentro del JSON, con `ejecutado: false`. Despues de extraer puedes usar el flujo opcional de **alta real** descrito abajo: consulta AD y solo escribe al confirmar **Crear usuario en Active Directory**.

## Instalación y prueba web

Desde la carpeta del proyecto, con Python instalado:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.domain.txt
.\start-domain.ps1
```

Abre http://127.0.0.1:8001, carga un PDF, revisa el resultado y pulsa **Descargar JSON**. El PDF se procesa en memoria; el navegador descarga el JSON al equipo. El servidor no guarda los documentos.

Si `py -3` indica que no hay Python instalado, instala Python o corrige su registro/ruta. Si ya existe un entorno `.venv` funcional, omite su creación.

## Alta real de usuarios desde la extraccion

### Cuenta para administrar Active Directory

El backend carga las variables AD del archivo `.env` local (excluido de Git).
Completa `AD_USERNAME` con el nombre corto de la cuenta de dominio,
`AD_DOMAIN=CAFEDCALLAO0` y `AD_PASSWORD='tu contrasena'`. Tambien puedes usar
el UPN completo como usuario y dejar `AD_DOMAIN` vacio. `AD_HOST` apunta al
controlador. Las variables del entorno tienen prioridad sobre el archivo.
La contrasena no se interpola: los caracteres `$` se conservan literalmente.
No uses una cuenta administradora local de la VM para administrar el dominio.

Esta cuenta se utiliza en las consultas y altas mediante Negotiate con firma
y cifrado, sin pasar la contrasena en argumentos de procesos. Si ambos campos
estan vacios, se usa la sesion Windows; si solo falta uno, se detiene la operacion.
El directorio muestra la identidad configurada, nunca su contrasena. Reinicia la
aplicacion tras configurar el archivo. Los scripts de consola PowerShell leen
las variables del entorno; la carga de `.env` la realiza el backend Python.

Despues de extraer un PDF, imagen o texto, aparece **¿La información extraída es correcta?**
para las personas que incluyen el servicio Dominio. SGD conserva su simulacion;
este flujo no crea cuentas SGD.

1. Revisa nombres, apellidos, DNI, area y usuario propuesto. Usa **No, corregir
   informacion** solo si hay errores. La separacion de nombres sin coma es una
   propuesta: revisa especialmente los apellidos compuestos.
2. Pulsa **Si, la informacion es correcta — registrar**. Esta es la confirmacion
   del alta REAL; no hay una segunda confirmacion ni botones intermedios.
3. La aplicacion resuelve el grupo bajo `OU=grupos` y la OU bajo `OU=CAFED`,
   propone inicial del primer nombre + apellido paterno, verifica duplicados,
   genera contrasena y ejecuta el registro con mensajes por etapa.

La resolucion de area ignora mayusculas, tildes y puntuacion. Prioriza coincidencias
exactas por nombre o `sAMAccountName`; tambien admite frases completas contenidas
en los nombres (por ejemplo, Educativo en Gerencia de Desarrollo Educativo), si
la mejor coincidencia es unica. No corrige errores ortograficos por aproximacion.
Si no hay un grupo/OU inequivoco, o el usuario ya existe, se detiene ANTES de escribir
y muestra el formulario de correcciones con seleccion opcional de OU/grupo o
usuario alternativo. No se agregan numeros automaticamente para evitar duplicados.
La contrasena aleatoria tiene al menos 24 caracteres (o el minimo del dominio si
es mayor), con cuatro categorias de caracteres. Se usan los permisos de la cuenta
que ejecuto `start-domain.ps1`; automatizar no cambia ni amplía esos permisos.

El avance muestra mensajes emitidos por cada etapa real: generacion de contrasena,
construccion del usuario, alta en la OU, membresia del grupo, establecimiento de
contrasena, habilitacion y verificacion final. No se simula avance con temporizadores.
Al completar correctamente aparece el usuario de dominio y la contrasena generada
para su entrega. Se mantienen temporalmente en memoria del servidor durante 15
minutos; no se guardan en disco, logs ni JSON descargable. El boton de ocultar
borra los campos visibles. Si falla el seguimiento, se puede retomar el MISMO
registro sin repetir la escritura. No recargues la pagina durante el alta: si
pierdes el resultado, comprueba AD y solicita restablecer la contrasena si procede.

Para la primera prueba en texto plano selecciona solo **Dominio** y pega una persona:

Puedes pegar tres lineas sin etiquetas: nombres primero, dos apellidos al final,
DNI en la segunda linea (con o sin prefijo `DNI`) y area en la tercera.
Por ejemplo: `pruebita pruedados pruebados`, luego `DNI 47296949` y luego `otic`.
Se propone `pruebita` como nombre y `pruedados pruebados` como apellidos,
conservando el texto original. Revisa la propuesta, especialmente si hay apellidos
compuestos. El formato anterior con etiquetas tambien sigue disponible:

```text
Nombres: NOMBRES DE LA PERSONA
Apellidos: APELLIDO PATERNO APELLIDO MATERNO
DNI: 12345678
Área: NOMBRE O SIGLA DEL ÁREA
```

No es necesario proporcionar el usuario. El DNI se conserva en la extraccion;
no se escribe en un atributo de AD sin definir primero esa equivalencia.

La cuenta se crea directamente en la OU final, inicialmente deshabilitada;
se agrega al grupo, se establece la contrasena, se exige cambio al siguiente
inicio de sesion y se habilita al final. Crear directamente en la OU sustituye
el movimiento manual. El `displayName` conserva apellidos seguidos de nombres.
La aplicacion usa firma/cifrado SASL sobre LDAP 389; AD exige cifrado suficiente
y valida la contrasena con sus politicas efectivas. La politica base mostrada
puede diferir de una politica detallada aplicada al usuario/grupo. No se cambia
ninguna politica ni se habilita la opcion de contrasena sin caducidad.

La identidad del proceso necesita permisos delegados de creacion en la OU,
establecimiento de contrasena, escritura de atributos y membresia del grupo.
Poder listar grupos NO demuestra que tenga esos permisos de escritura.
No se guardan contrasenas en archivos, argumentos de PowerShell ni JSON de
resultados. Los JSON descargados conservan la extraccion y agregan `registro_ad`
con la seleccion revisada y el resultado, sin convertir el INSERT simulado en SQL.

AD no proporciona una transaccion unica para estas operaciones. Si falla el
grupo o la contrasena despues del alta, el resultado indica una cuenta parcial
deshabilitada y su DN. Si hay corte de conexion al habilitar o verificar, el
estado es incierto: comprobar AD antes de reintentar. No hay borrado automatico
ni reintento de escritura. Cada confirmacion se consume una sola vez. Para
recuperar un alta parcial, revisa la cuenta en AD con el administrador.

Las rutas de registro son locales y requieren solicitudes desde la pagina de
revision. Mantener el servidor en `127.0.0.1`; no publicar este panel mediante
un proxy sin una capa de autenticacion/autorizacion propia. No se requiere RSAT.

Verificacion: pruebas aisladas con `python -m unittest discover -s tests -p "test_ad*.py"`.
Se validaron lectura real, duplicados y revision web; no se crearon cuentas de
prueba en el directorio real durante el desarrollo.

## Uso desde consola

### Prueba de conexion a Active Directory (solo lectura)

### Listar grupos y unidades organizativas desde la web

Inicia `start-domain.ps1` desde tu sesion de dominio y abre
`http://127.0.0.1:8001/directorio`, o usa el enlace de la pagina principal.
Pulsa **Consultar directorio** para ver los grupos del contenedor `OU=grupos`
y las unidades organizativas de `OU=CAFED` (incluidas la raiz y sus subunidades), con sus
nombres, descripciones y rutas DN. El buscador filtra ambos listados. La consulta
es paginada, de solo lectura, no incluye miembros de grupos y no guarda los
resultados en disco. Solo muestra objetos que la cuenta del servidor puede leer.
La API `/api/directorio` admite unicamente clientes de loopback. Mantén el
servidor local; no lo publiques mediante un proxy sin implementar autenticacion.
Si cambias de controlador, define `$env:AD_HOST = 'dc.dominio'` antes de iniciar.
No requiere RSAT ni contrasenas en `.env`. Reinicia el servidor si estaba abierto
cuando se incorporo esta funcionalidad.

Para consultar desde consola: `.\scripts\list_ad_windows.ps1` (salida JSON).
Para las pruebas aisladas: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_ad_directory.py`.

### Diagnostico de conexion

En Windows unido al dominio, puedes usar la sesion actual sin instalar RSAT ni
configurar certificados LDAPS:

```powershell
.\scripts\check_ad_windows.ps1
```

Este script usa autenticacion integrada Negotiate en el puerto 389, con firma
y cifrado SASL habilitados. Consulta RootDSE y el objeto base del dominio, sin
modificar objetos ni guardar contrasenas. Ejecutalo con tu sesion de dominio;
una cuenta local o un servicio con otra identidad no hereda estas credenciales.
Acepta `-Server nombre.completo` para elegir otro controlador. Esta prueba no
integra automaticamente Active Directory en la aplicacion web.

La prueba independiente no cambia el flujo web ni crea usuarios. Instala sus
dependencias y ejecuta desde una terminal interactiva:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.ad.txt
.\.venv\Scripts\python.exe scripts/check_ad.py --check-only
.\.venv\Scripts\python.exe scripts/check_ad.py
```

El destino predeterminado es `DC02.cafedcallao.gob.pe:636`. Se puede cambiar con
`--host` y `--port`. Primero valida TLS y el certificado; solo entonces solicita
usuario UPN y contrasena oculta, sin guardarla. Realiza un unico intento de
autenticacion, consulta RootDSE y lee el objeto base del dominio. No modifica AD.
Si la CA interna no esta en el almacen de confianza, usa `--ca-file ruta.pem`
con su certificado obtenido del administrador. No se desactiva la validacion.
Un puerto TCP abierto no garantiza que LDAPS funcione. El error 10054 durante
TLS indica que la conexion se interrumpio antes de autenticar: revisa LDAPS,
el certificado del controlador y los eventos Schannel del servidor.

```powershell
.\.venv\Scripts\python.exe simulate_domain.py "C:\ruta\solicitud.pdf"
```

Genera `data/domain/solicitud.json`. Se puede elegir otra ruta con `--output`. Repetir el mismo nombre reemplaza su JSON anterior. `data/` está excluido de Git.

## Área y grupo

El área se toma del bloque **DE**, debajo del nombre del solicitante; no del destinatario **A**. El nombre real del grupo AD requiere una equivalencia local: el documento no lo proporciona.

Copia `config/grupos.example.json` a `data/grupos.json` y **reemplaza los valores de ejemplo por los nombres reales**. Las claves deben coincidir con el área/cargo que aparece en el PDF (se ignoran mayúsculas, acentos y espacios repetidos). Agrega variantes si un documento dice «SUB GERENTE DE LOGISTICA» y otro «SUB GERENCIA DE LOGISTICA».

```powershell
New-Item -ItemType Directory -Force data
Copy-Item config/grupos.example.json data/grupos.json
# Editar data/grupos.json antes de usarlo.
$env:DOMAIN_GROUPS_FILE = (Resolve-Path data/grupos.json).Path
.\start-domain.ps1
```

En consola: `--groups data/grupos.json`. Sin equivalencia se conserva el área y `grupo_ad` queda en `null`, pendiente de revisión. La simulación no comprueba la existencia del grupo en AD.

## Reglas de extracción

- Lee tablas con encabezado «APELLIDOS Y NOMBRES», DNI y columnas opcionales de correo, teléfono y servicios.
- Con columna USUARIO/USUARIOS/ACCESO/ACCESOS, manda el servicio de cada fila: SGD/SIGA sin dominio se excluyen aunque el cuerpo mencione dominio.
- Sin columna de servicios, busca DOMINIO o la variante DOMINO en el texto del documento. ACCESO genérico queda pendiente; ACCESO a SGD/SIGA/SIAF no implica dominio.
- Conserva los nombres originales y los ceros iniciales del DNI. Separa apellidos y nombres cuando hay una coma. Sin separador, conserva el nombre completo y solicita revisión; no adivina apellidos compuestos.
- Los DNI inválidos, duplicados, área/grupo ausentes y OCR quedan señalados. La extraccion conserva esos avisos; la revision de alta permite completar usuario, OU y grupo y generar la contrasena al confirmar.
- PDF escaneado: necesita Tesseract con datos de idioma español (`spa.traineddata`) y `TESSDATA_PREFIX` apuntando al directorio `tessdata`. Si falta, muestra un error. El OCR y las tablas sin bordes pueden requerir revisión; no se garantiza extraer todas las variantes.
- Límite web: 20 MB; máximo 50 páginas. Los documentos con contraseña se rechazan.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pip install pytest httpx
.\.venv\Scripts\python.exe -m pytest tests/test_domain_extraction.py -q
```

Las pruebas cubren reglas de selección, nombres ambiguos, DNI, duplicados, PDF digital en memoria y carga por API sin BD. Las imágenes adjuntas se usaron como referencia de formatos; falta validar los PDF originales y la calidad de OCR en documentos reales.
