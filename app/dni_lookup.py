import json
import re
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PRIMARY = 'https://graphperu.daustinn.com/api/query/'
SECONDARY = 'https://apiscina.muniplibre.gob.pe/piscina/sel-reniec'
TERTIARY_KMENTE = 'https://kmente.com/prueba-gratis'


def _json(url, method='GET', body=None):
    data = None if body is None else json.dumps(body).encode('utf-8')
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request, timeout=12) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f'HTTP {response.status}')
        return json.loads(response.read().decode('utf-8'))


def _lookup_kmente(dni):
    """Consulta de contingencia en kmente.com (Prueba gratis RENIEC)."""
    payload = urllib.parse.urlencode({'modo': 'reniec_gratis', 'dni': dni, 'telefono': ''}).encode('utf-8')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': TERTIARY_KMENTE,
        'Origin': 'https://kmente.com'
    }
    request = Request(TERTIARY_KMENTE, data=payload, method='POST', headers=headers)
    with urlopen(request, timeout=12) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f'HTTP {response.status}')
        html = response.read().decode('utf-8', errors='ignore')

    idx = html.find('rgm2-table')
    if idx == -1:
        return None
    end_idx = html.find('</table>', idx)
    table_content = html[idx:end_idx] if end_idx != -1 else html[idx:idx + 3000]

    fields = {}
    for k, v in re.findall(r'<tr><td>(.*?)</td><td>(.*?)</td></tr>', table_content):
        fields[k.strip().lower()] = v.strip()

    full_name = fields.get('nombres completos', '').strip().upper()
    if not full_name:
        return None

    padre = fields.get('padre', '')
    madre = fields.get('madre', '')
    ap_paterno = ''
    ap_materno = ''
    if padre:
        parts = re.split(r'[-–\s]+', padre)
        if len(parts) > 2:
            ap_paterno = parts[2].upper()
    if madre:
        parts = re.split(r'[-–\s]+', madre)
        if len(parts) > 2:
            ap_materno = parts[2].upper()

    tokens = full_name.split()
    if ap_paterno and ap_materno and ap_paterno in tokens and ap_materno in tokens:
        p_idx = tokens.index(ap_paterno)
        m_idx = tokens.index(ap_materno)
        if p_idx < m_idx:
            surnames = f'{ap_paterno} {ap_materno}'
            names = ' '.join([t for i, t in enumerate(tokens) if i not in (p_idx, m_idx)])
        else:
            surnames = ' '.join(tokens[-2:]) if len(tokens) >= 2 else tokens[0]
            names = ' '.join(tokens[:-2]) if len(tokens) >= 2 else ''
    elif len(tokens) >= 3:
        surnames = f'{tokens[-2]} {tokens[-1]}'
        names = ' '.join(tokens[:-2])
    elif len(tokens) == 2:
        surnames = tokens[1]
        names = tokens[0]
    else:
        surnames = ''
        names = full_name

    return {
        'encontrado': True,
        'origen': 'terciaria',
        'dni': dni,
        'nombres': names.strip(),
        'apellidos': surnames.strip(),
        'nombre_completo': full_name.strip()
    }


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
    try:
        data = _lookup_kmente(dni)
        if data and data.get('encontrado'):
            return data
    except Exception:
        pass
    return {'encontrado': False, 'origen': None, 'dni': dni, 'nombres': '', 'apellidos': '', 'nombre_completo': 'Persona no encontrada'}
