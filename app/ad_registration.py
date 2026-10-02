"""Review and explicitly confirm one AD account at a time."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import threading
import time
import unicodedata
import string

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from app.ad_directory import list_directory
from app.ad_config import process_environment, redact


class AccountDraft(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    paternal: str = Field(min_length=1, max_length=40)
    maternal: str = Field(default='', max_length=40)
    given_names: str = Field(min_length=1, max_length=64)
    dni: str = Field(pattern=r'^[0-9]{8}$', default='00000000')
    username: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,19}$')
    area: str = Field(default='', max_length=128)
    ou_dn: str = Field(min_length=1, max_length=1024)
    group_dn: str = Field(min_length=1, max_length=1024)
    servicios_a_crear: list[str] = Field(default_factory=lambda: ["dominio"])
    reviewed: bool


class Confirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str
    password: SecretStr
    password_confirmation: SecretStr


class GeneratedConfirmation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: str


class AutomaticAccount(AccountDraft):
    username: str = Field(default='', pattern=r'^$|^[a-z][a-z0-9._-]{0,19}$')
    ou_dn: str = Field(default='', max_length=1024)
    group_dn: str = Field(default='', max_length=1024)


def resolve_unique(items, terms, fields):
    def key(value):
        return ' '.join(re.findall(r'\w+', normalize(value)))
    terms = [key(term) for term in terms if key(term)]
    scored = []
    for item in items:
        score = (0, 0)
        for field in fields:
            value = key(item.get(field, ''))
            if not value:
                continue
            for term in terms:
                if value == term:
                    score = max(score, (2, len(value)))
                elif (' ' + value + ' ') in (' ' + term + ' ') or (' ' + term + ' ') in (' ' + value + ' '):
                    score = max(score, (1, min(len(value), len(term))))
        if score[0]:
            scored.append((score, item))
    if not scored:
        return None
    best = max(score for score, _ in scored)
    matches = [item for score, item in scored if score == best]
    return matches[0] if len(matches) == 1 else None


def automatic_payload(draft, progress):
    progress('Armando el usuario a partir de los nombres y apellidos confirmados...')
    username = draft.username or suggest_username(draft.given_names, draft.paternal)
    if not re.fullmatch(r'[a-z][a-z0-9._-]{0,19}', username):
        raise ValueError('El usuario propuesto requiere correccion (maximo 20 caracteres).')
    progress('Usuario propuesto: ' + username + '. Consultando grupos y OUs de CAFED...')
    ou_mapping = {
        "gie": "infraestructura",
        "otic": "tecnologias",
        "oci": "control institucional",
        "gg": "gerencia general",
        "gpp": "planificacion",
        "gaj": "asesoria juridica",
        "ga": "administracion",
        "sgrh": "recursos humanos",
        "sgl": "logistica",
        "sgc": "contabilidad",
        "sgt": "tesoreria",
        "teso": "tesoreria",
        "gde": "desarrollo educativo",
        "be": "becas",
        "ac": "archivo"
    }
    mapped_term = ou_mapping.get(draft.area.strip().lower(), draft.area)
    
    directory = registration_directory()
    group = (next((g for g in directory['grupos'] if g['dn'] == draft.group_dn), None)
             if draft.group_dn else resolve_unique(directory['grupos'], [draft.area, mapped_term], ['nombre', 'cuenta']))
    if not group:
        raise ValueError('No se encontro un grupo inequivoco para el area. Corrige el area o elige el grupo.')
    progress('Grupo identificado: ' + group['nombre'] + ' — ' + group.get('cuenta', ''))
    ous = [o for o in directory['unidades_organizativas'] if normalize(o['nombre']) != 'cafed']
    
    ou = (next((o for o in directory['unidades_organizativas'] if o['dn'] == draft.ou_dn), None)
          if draft.ou_dn else resolve_unique(ous, [draft.area, mapped_term, group['nombre'], group.get('cuenta', '')], ['nombre']))
    if not ou:
        raise ValueError('No se encontro una OU inequivoca dentro de CAFED. Selecciona la OU para continuar.')
    progress('Unidad organizativa identificada: ' + ou['dn'])
    progress('Comprobando en AD que el usuario no exista y validando el destino...')
    checked = prepare(AccountDraft(**dict(draft.model_dump(), username=username, group_dn=group['dn'], ou_dn=ou['dn'])))
    with _lock:
        plan = _plans.pop(checked['token'])
    progress('Usuario disponible. Validacion completada.')
    return plan[1]


def normalize(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', value)
                            if not unicodedata.combining(c)).casefold().split())


def suggest_username(given_names, paternal):
    first = normalize(given_names).split()
    surname = re.sub('[^a-z0-9]', '', normalize(paternal))
    return (first[0][0] + surname) if first and surname else ''


def registration_directory():
    directory = list_directory()
    root = 'OU=CAFED,' + directory['base_dn']
    group_root = ',OU=grupos,' + directory['base_dn']
    directory['unidades_organizativas'] = [o for o in directory['unidades_organizativas']
        if o['dn'].casefold() == root.casefold() or o['dn'].casefold().endswith(',' + root.casefold())]
    directory['grupos'] = [g for g in directory['grupos'] if g['dn'].casefold().endswith(group_root.casefold())]
    directory['upn_suffix'] = '.'.join(part[3:] for part in directory['base_dn'].split(','))
    return directory


def run_operation(payload):
    env = process_environment()
    script = Path(__file__).resolve().parent.parent / 'scripts' / 'register_ad_windows.ps1'
    shell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        result = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-File', str(script),
            '-Server', env['AD_HOST']], env=env,
            input=json.dumps(payload, ensure_ascii=False), capture_output=True,
            encoding='utf-8', timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
        data = json.loads(redact(result.stdout, env).lstrip('﻿').strip().splitlines()[-1])
        if not isinstance(data, dict) or not isinstance(data.get('ok'), bool):
            raise ValueError('Invalid response')
        return data
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return {'ok': False, 'estado': 'resultado_incierto' if payload['action'] == 'create' else 'rechazado',
                'mensaje': 'No se pudo confirmar la respuesta de AD. Revisa el directorio antes de volver a intentar.'}


_plans = {}
_lock = threading.Lock()


def prepare(draft):
    if not draft.reviewed:
        raise ValueError('Confirma la separacion de apellidos y nombres y revisa los datos extraidos.')
    surnames = ' '.join(filter(None, (draft.paternal, draft.maternal)))
    display = surnames + ' ' + draft.given_names
    if len(display) > 64:
        raise ValueError('El nombre completo supera 64 caracteres; requiere revision antes del alta.')
    for value in (draft.paternal, draft.maternal, draft.given_names):
        if any(not (c.isalpha() or c in " '-") for c in value):
            raise ValueError('Revisa los nombres: solo se admiten letras, espacios, guiones y apostrofos.')
    directory = registration_directory()
    ou = next((o for o in directory['unidades_organizativas'] if o['dn'] == draft.ou_dn), None)
    group = next((g for g in directory['grupos'] if g['dn'] == draft.group_dn), None)
    if not ou or not group:
        raise ValueError('Selecciona una OU de CAFED y un grupo valido del contenedor grupos.')
    payload = dict(username=draft.username, given_names=draft.given_names, surnames=surnames,
                   area=draft.area, ou_dn=ou['dn'], group_dn=group['dn'], upn_suffix=directory['upn_suffix'],
                   dni=draft.dni, servicios_a_crear=draft.servicios_a_crear)
    check = run_operation(dict(payload, action='validate'))
    if not check['ok']:
        if check.get('codigo_ldap') or check.get('estado') == 'resultado_incierto':
            raise RuntimeError(check.get('mensaje', 'No se pudo consultar Active Directory.'))
        raise ValueError(check.get('mensaje', 'No se pudo validar el alta.'))
        
    if "sgd" in draft.servicios_a_crear:
        from app.sgd_registration import check_usuario_sgd, check_empleado
        if check_empleado(draft.dni):
             raise ValueError("El DNI ya está registrado como empleado en SGD. No se pueden crear duplicados.")
        if draft.username and check_usuario_sgd(draft.username):
             raise ValueError(f"El usuario propuesto requiere corrección: '{draft.username}' ya está en uso en SGD.")

    token = secrets.token_urlsafe(32)
    with _lock:
        for key, (expiry, _) in list(_plans.items()):
            if expiry < time.monotonic():
                del _plans[key]
        if len(_plans) >= 500:
            raise ValueError('Hay demasiadas revisiones abiertas. Espera unos minutos.')
        _plans[token] = (time.monotonic() + 900, dict(payload, minimum_length=check['min_password_length']))
    return dict(token=token, nombre_completo=display, usuario=draft.username, upn=check['upn'],
                ou=ou, grupo=group, area=draft.area, dn=check['dn'],
                min_password_length=check['min_password_length'], complexity=check['complexity'])


def create(confirmation):
    password = confirmation.password.get_secret_value()
    if not password or password != confirmation.password_confirmation.get_secret_value():
        raise ValueError('Las contrasenas deben coincidir y no estar vacias.')
    if len(password) > 256:
        raise ValueError('La contrasena supera el limite admitido de 256 caracteres.')
    with _lock:
        plan = _plans.pop(confirmation.token, None)
    if not plan or plan[0] < time.monotonic():
        raise ValueError('La revision vencio o ya fue utilizada. Comprueba los datos de nuevo.')
    # The token is consumed before writing: never retry a possibly completed operation.
    return run_operation(dict(plan[1], action='create', password=password))


def generate_password(payload):
    # Contraseñas cortas pero que cumplen con complejidad de AD (Mayúsculas, minúsculas, números, símbolos)
    length = max(8, int(payload.get('minimum_length', 0)))
    if length > 256:
        raise ValueError('La longitud exigida necesita revision administrativa.')
    groups = ('ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '@*-!')
    excluded = [normalize(payload['username'])] + normalize(payload['given_names'] + ' ' + payload['surnames']).split()
    for _ in range(100):
        # Un formato de 8 caracteres típico y fácil de dictar: Ej. Bdef245*
        chars = [secrets.choice(groups[0])]  # 1 mayúscula
        chars += [secrets.choice(groups[1]) for _ in range(3)]  # 3 minúsculas
        chars += [secrets.choice(groups[2]) for _ in range(3)]  # 3 números
        chars.append(secrets.choice(groups[3]))  # 1 símbolo
        
        # Rellenar si AD exige más de 8 caracteres
        if length > 8:
            chars += [secrets.choice(groups[1] + groups[2]) for _ in range(length - len(chars))]
            
        password = ''.join(chars)
        if not any(len(word) >= 3 and word in password.lower() for word in excluded):
            return password
    raise ValueError('No se pudo generar una contrasena adecuada.')


def run_creation(payload, progress):
    env = process_environment()
    script = Path(__file__).resolve().parent.parent / 'scripts' / 'register_ad_windows.ps1'
    shell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    process = None
    timer = None
    final = None
    try:
        process = subprocess.Popen([str(shell), '-NoProfile', '-NonInteractive', '-File', str(script),
            '-Server', env['AD_HOST']], env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW)
        timer = threading.Timer(90, process.kill)
        timer.daemon = True
        timer.start()
        process.stdin.write(json.dumps(payload, ensure_ascii=False))
        process.stdin.close()
        for line in process.stdout:
            event = json.loads(redact(line, env).lstrip('﻿'))
            if event.get('tipo') == 'progreso':
                progress(event['mensaje'])
            elif isinstance(event.get('ok'), bool):
                final = event
        process.wait()
        if final is not None and (not final['ok'] or process.returncode == 0):
            return final
    except (OSError, ValueError):
        pass
    finally:
        if timer:
            timer.cancel()
        if process:
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdout:
                process.stdout.close()
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
    return {'ok': False, 'estado': 'resultado_incierto',
            'mensaje': 'No se pudo confirmar el resultado. Revisa la cuenta en AD antes de reintentar.'}


_jobs = {}


def start_generated(confirmation, automatic=None):
    with _lock:
        now = time.monotonic()
        for key, job in list(_jobs.items()):
            if job['expires'] < now and job['done']:
                del _jobs[key]
        if len(_jobs) >= 100:
            raise ValueError('Hay demasiados registros recientes. Espera unos minutos.')
        plan = None
        if automatic is None:
            plan = _plans.pop(confirmation.token, None)
            if not plan or plan[0] < now:
                raise ValueError('La revision vencio o ya fue utilizada. Comprueba los datos de nuevo.')
        elif not automatic.reviewed:
            raise ValueError('Debes confirmar que la informacion extraida es correcta.')
        job_id = secrets.token_urlsafe(32)
        _jobs[job_id] = {'expires': now + 900, 'done': False, 'events': [], 'result': None}

    def progress(message):
        with _lock:
            _jobs[job_id]['events'].append(message)

    def worker():
        result = {'ok': False, 'estado': 'rechazado', 'mensaje': 'No se pudo preparar la contrasena.'}
        writing = False
        try:
            servicios = automatic.servicios_a_crear if automatic is not None else ["dominio"]
            payload = None
            password = None
            
            if "dominio" in servicios:
                payload = automatic_payload(automatic, progress) if automatic is not None else plan[1]
                progress('Generando una contrasena aleatoria segura...')
                password = generate_password(payload)
                progress('Contrasena generada. Iniciando el registro en Active Directory...')
                writing = True
                result = run_creation(dict(payload, action='create', password=password), progress)
                result = dict(result, ou_dn=payload['ou_dn'], group_dn=payload['group_dn'])
                if result['ok']:
                    result = dict(result, usuario=payload['username'], password=password)
                    progress('Registro en AD completado. Usuario y contrasena disponibles.')
                else:
                    progress('Registro no completado: ' + result.get('mensaje', 'Revisa el estado en AD.'))
                    raise RuntimeError("No se pudo completar el registro en AD.")
            else:
                result = {'ok': True, 'estado': 'completado'}

            if "sgd" in servicios:
                if automatic is not None:
                    dni = automatic.dni
                    _username = payload['username'] if payload else automatic.username
                else:
                    dni = plan[1]['dni']
                    _username = plan[1]['username']
                
                _password = password
                
                if "dominio" not in servicios:
                    progress("Preparando acceso para SGD...")
                    _username = _username or suggest_username(automatic.given_names, automatic.paternal) if automatic else _username
                    _password = generate_password({'username': _username, 'given_names': automatic.given_names, 'surnames': automatic.paternal, 'minimum_length': 16}) if automatic else ""
                    result['usuario'] = _username
                    result['password'] = _password
                
                from app.sgd_registration import registrar_flujo_completo
                emp_code = registrar_flujo_completo(
                    dni=dni,
                    nombres=automatic.given_names if automatic else plan[1]['given_names'],
                    apellido_paterno=automatic.paternal if automatic else (plan[1]['surnames'].split()[0] if plan[1]['surnames'] else ""),
                    apellido_materno=automatic.maternal if automatic else (plan[1]['surnames'].split()[1] if len(plan[1]['surnames'].split())>1 else ""),
                    area=automatic.area if automatic else plan[1]['area'],
                    username=_username,
                    password=dni,
                    progress=progress
                )
                result['sgd_empleado'] = emp_code
                
                if "dominio" not in servicios:
                    result.update(estado='completado', ok=True)
                    
        except (ValueError, RuntimeError) as exc:
            import traceback
            traceback.print_exc()
            result = {'ok': False, 'estado': 'resultado_incierto' if writing else ('error_servicio' if isinstance(exc, RuntimeError) else 'requiere_correccion'),
                      'mensaje': f'Fallo durante el registro: {str(exc)}'}
            progress(result['mensaje'])
        except Exception:
            # Never serialize exception contents, input payloads, or credentials.
            result = {'ok': False, 'estado': 'resultado_incierto', 'mensaje': 'No se pudo confirmar el alta. Revisa el sistema antes de reintentar.'}
            progress(result['mensaje'])
        finally:
            with _lock:
                _jobs[job_id].update(done=True, result=result, expires=time.monotonic() + 900)
            def expire():
                with _lock:
                    _jobs.pop(job_id, None)
            cleanup = threading.Timer(900, expire)
            cleanup.daemon = True
            cleanup.start()
    threading.Thread(target=worker, daemon=True).start()
    return {'job_id': job_id}


def start_automatic(draft):
    return start_generated(None, automatic=draft)


def job_status(job_id):
    with _lock:
        job = _jobs.get(job_id)
        if not job or (job['done'] and job['expires'] < time.monotonic()):
            _jobs.pop(job_id, None)
            raise ValueError('El resultado vencio. Comprueba la cuenta en AD; no repitas el alta.')
        return {'done': job['done'], 'events': list(job['events']), 'result': job['result']}
