"""DNI lookup with an explicit primary-to-secondary fallback."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PRIMARY = 'https://graphperu.daustinn.com/api/query/'
SECONDARY = 'https://apiscina.muniplibre.gob.pe/piscina/sel-reniec'


def _json(url, method='GET', body=None):
    data = None if body is None else json.dumps(body).encode('utf-8')
    request = Request(url, data=data, method=method, headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
    with urlopen(request, timeout=12) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f'HTTP {response.status}')
        return json.loads(response.read().decode('utf-8'))


def fetch_dni_data(dni):
    if not isinstance(dni, str) or not dni.isdigit() or len(dni) != 8:
        raise ValueError('El DNI debe tener exactamente 8 dígitos.')
    try:
        data = _json(PRIMARY + dni)
        if data.get('names') or data.get('paternalLastName'):
            names = str(data.get('names') or '').strip().upper()
            surnames = f"{data.get('paternalLastName') or ''} {data.get('maternalLastName') or ''}".strip().upper()
            return {'encontrado': True, 'origen': 'principal', 'dni': dni, 'nombres': names, 'apellidos': surnames, 'nombre_completo': f'{names} {surnames}'.strip()}
    except Exception:
        pass
    try:
        data = _json(SECONDARY, 'POST', {'nuDniConsulta': dni})
        result = ((data.get('consultarResponse') or {}).get('return') or {})
        person = result.get('datosPersona')
        if result.get('coResultado') == '0000' and person:
            names = str(person.get('prenombres') or '').strip().upper()
            surnames = f"{person.get('apPrimer') or ''} {person.get('apSegundo') or ''}".strip().upper()
            return {'encontrado': True, 'origen': 'secundaria', 'dni': dni, 'nombres': names, 'apellidos': surnames, 'nombre_completo': f'{names} {surnames}'.strip()}
    except Exception:
        pass
    return {'encontrado': False, 'origen': None, 'dni': dni, 'nombres': '', 'apellidos': '', 'nombre_completo': 'Persona no encontrada'}
