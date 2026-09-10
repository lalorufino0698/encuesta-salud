# Prueba de solicitudes PDF → JSON

Los mensajes de WhatsApp pueden incluir el **área en la cuarta línea**, después del usuario (por ejemplo, `logistica` o `Área: Logística`). Se conserva por persona y se utiliza en `department` de cada insert. Agrega la clave `LOGISTICA` con el grupo real en tu mapa local; la búsqueda ignora acentos y mayúsculas. No se inventa un grupo cuando falta esa equivalencia. Un mensaje como «solo dominio x ahora» no se toma como área.

En **Texto plano**, también puedes pegar mensajes de WhatsApp con DNI, nombre completo y usuario en tres líneas. Se ignoran los encabezados de hora/remitente y se consolidan registros idénticos repetidos. Marca **Dominio**, **SGD** o ambos: la selección manual se aplica a todos los usuarios del texto y define `inserts_simulados`, uno por servicio seleccionado. No se generan inserts de SIGA/SIAF. Sin datos suficientes, el área, grupo y separación de nombres quedan pendientes de revisión. Las tablas pegadas también admiten esta selección.

El extractor detecta automáticamente el modelo español local en `data/tessdata/spa.traineddata`. Si se define `TESSDATA_PREFIX`, esa ruta tiene prioridad. El modelo se obtiene del repositorio oficial `tesseract-ocr/tessdata_fast` y no se incluye en Git. No hace falta definir la variable cuando se usa la ubicación local del proyecto.

También admite capturas **PNG y JPG**: selecciona la imagen o pégala con **Ctrl+V** en la página y pulsa extraer. En consola se puede pasar la ruta de la imagen a `simulate_domain.py`. Incluye el bloque DE y la tabla completa en una captura legible. Las imágenes siempre requieren OCR en español; si falta su configuración se muestra un error. Los resultados OCR quedan pendientes de revisión. La conversión y el manejo de errores están cubiertos por pruebas; la precisión sobre capturas reales debe validarse con OCR instalado.

Este flujo se ejecuta aparte del sistema de encuestas. No requiere MySQL ni credenciales de Active Directory. No ejecuta SQL, LDAP ni PowerShell de administración. El INSERT es un objeto dentro del JSON, con `ejecutado: false`.

## Instalación y prueba web

Desde la carpeta del proyecto, con Python instalado:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.domain.txt
.\start-domain.ps1
```

Abre http://127.0.0.1:8001, carga un PDF, revisa el resultado y pulsa **Descargar JSON**. El PDF se procesa en memoria; el navegador descarga el JSON al equipo. El servidor no guarda los documentos.

Si `py -3` indica que no hay Python instalado, instala Python o corrige su registro/ruta. Si ya existe un entorno `.venv` funcional, omite su creación.

## Uso desde consola

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
- Los DNI inválidos, duplicados, área/grupo ausentes y OCR quedan señalados. No se generan contraseñas, nombres de inicio de sesión ni rutas OU, porque sus reglas todavía no están definidas.
- PDF escaneado: necesita Tesseract con datos de idioma español (`spa.traineddata`) y `TESSDATA_PREFIX` apuntando al directorio `tessdata`. Si falta, muestra un error. El OCR y las tablas sin bordes pueden requerir revisión; no se garantiza extraer todas las variantes.
- Límite web: 20 MB; máximo 50 páginas. Los documentos con contraseña se rechazan.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pip install pytest httpx
.\.venv\Scripts\python.exe -m pytest tests/test_domain_extraction.py -q
```

Las pruebas cubren reglas de selección, nombres ambiguos, DNI, duplicados, PDF digital en memoria y carga por API sin BD. Las imágenes adjuntas se usaron como referencia de formatos; falta validar los PDF originales y la calidad de OCR en documentos reales.
