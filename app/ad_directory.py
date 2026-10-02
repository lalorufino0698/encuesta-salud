"""Read the directory with the Windows identity running the local server."""
import json
import os
from pathlib import Path
import subprocess
from app.ad_config import process_environment, redact


def list_directory():
    env = process_environment()
    if os.name != 'nt':
        raise RuntimeError('Esta consulta requiere Windows y una sesion de dominio.')
    script = Path(__file__).resolve().parent.parent / 'scripts' / 'list_ad_windows.ps1'
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
    try:
        result = subprocess.run(
            [str(powershell), '-NoProfile', '-NonInteractive', '-File', str(script),
             '-Server', env['AD_HOST']], env=env,
            capture_output=True, encoding='utf-8', errors='replace', timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('La consulta excedio 90 segundos. Comprueba la conexion al dominio.') from exc
    except OSError as exc:
        raise RuntimeError('No se pudo iniciar Windows PowerShell para consultar AD.') from exc
    if result.returncode:
        raise RuntimeError('No se pudo consultar AD. Revisa la cuenta configurada y sus permisos. Detalle: ' + redact(result.stderr.strip(), env)[:600])
    try:
        data = json.loads(result.stdout.lstrip('\ufeff'))
        if not isinstance(data['grupos'], list) or not isinstance(data['unidades_organizativas'], list):
            raise ValueError('Invalid lists')
        return data
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError('La consulta de AD devolvio una respuesta inesperada.') from exc
