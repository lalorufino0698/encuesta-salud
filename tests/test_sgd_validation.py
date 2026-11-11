import time
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app import ad_registration as ad, sgd_registration as sgd
from app.domain_main import app

@pytest.mark.parametrize('exists', [True, False])
def test_validation_endpoint_read_only(exists):
    with patch.object(sgd, 'check_ciudadano', return_value=exists) as check, patch.object(sgd, 'register_ciudadano') as insert:
        with TestClient(app, base_url='http://127.0.0.1', client=('127.0.0.1', 50000)) as client:
            response = client.post('/api/sgd/validar-ciudadano', json={'dni':'01234567'}, headers={'X-AD-Review':'1'})
        assert response.status_code == 200
        assert response.json()['existe'] is exists
        assert response.json()['solo_validacion'] is True
        check.assert_called_once_with('01234567')
        insert.assert_not_called()

@pytest.mark.parametrize('exists', [True, False])
def test_automatic_sgd_never_inserts_or_calls_ad(exists):
    draft = ad.AutomaticAccount(paternal='PRUEBA', given_names='PERSONA', dni='01234567', area='OTIC', reviewed=True, servicios_a_crear=['sgd'])
    with patch.object(sgd, 'check_ciudadano', return_value=exists), patch.object(sgd, 'register_ciudadano') as insert, patch.object(sgd, 'registrar_flujo_completo', return_value='00123'), patch.object(ad, 'automatic_payload') as domain:
        job = ad.start_automatic(draft)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = ad.job_status(job['job_id'])
            if state['done']: break
            time.sleep(0.01)
        assert state['done'] and state['result']['ok']
        insert.assert_not_called()
        domain.assert_not_called()

def test_query_parameterizes_dni_and_only_selects():
    conn = MagicMock()
    conn.__enter__.return_value = conn
    with patch.object(sgd, 'get_connection', return_value=conn):
        assert sgd.check_ciudadano('01234567') is True
    conn.cursor.return_value.execute.assert_called_once_with('SELECT TOP 1 NULEM FROM IDOSGD.TDTX_ANI_SIMIL WHERE NULEM = ?', ('01234567',))
    conn.commit.assert_not_called()

def test_connection_failure_is_not_absence():
    with patch.object(sgd, 'check_ciudadano', side_effect=RuntimeError('private connection details')):
        with pytest.raises(RuntimeError, match='No se pudo validar') as exc:
            sgd.validate_ciudadano('01234567')
        assert 'private' not in str(exc.value)

@pytest.mark.parametrize('dni', ['', '123', 'abcdefgh', '123456789'])
def test_invalid_dni_never_queries(dni):
    with patch.object(sgd, 'check_ciudadano') as check:
        with pytest.raises(ValueError):
            sgd.validate_ciudadano(dni)
        check.assert_not_called()

@pytest.mark.parametrize('area, expected_code', [
    # Opciones de la lista desplegable en la web
    ('Administración', '00007'),
    ('administracion', '00007'),
    ('Gerencia de Administración', '00007'),
    ('GA', '00007'),
    ('Tecnologías', '00005'),
    ('Tecnologías (OTIC)', '00005'),
    ('OTIC', '00005'),
    ('Planificación', '00005'),
    ('GPP', '00005'),
    ('Asesoría Jurídica', '00006'),
    ('GAJ', '00006'),
    ('Control Institucional', '00003'),
    ('OCI', '00003'),
    ('Gerencia General', '00004'),
    ('GG', '00004'),
    ('Recursos Humanos', '00008'),
    ('SGRH', '00008'),
    ('Logística', '00009'),
    ('SGL', '00009'),
    ('Contabilidad', '00010'),
    ('SGC', '00010'),
    ('Tesorería', '00011'),
    ('SGT', '00011'),
    ('Desarrollo Educativo', '00012'),
    ('GDE', '00012'),
    ('Infraestructura', '00013'),
    ('GIE', '00013'),
    ('Becas', '00014'),
    ('BE', '00014'),
    ('Archivo', '00015'),
    ('AC', '00015'),
    ('Mesa de Partes', '00002'),
    ('MP', '00002'),
    ('Consejo Directivo', '00001'),
    ('SCD', '00001'),
    ('00007', '00007'),
])
def test_map_dependencia_correct_codes(area, expected_code):
    assert sgd.map_dependencia(area) == expected_code

