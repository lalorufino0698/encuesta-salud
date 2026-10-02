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
    with patch.object(sgd, 'check_ciudadano', return_value=exists), patch.object(sgd, 'register_ciudadano') as insert, patch.object(ad, 'automatic_payload') as domain:
        job = ad.start_automatic(draft)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = ad.job_status(job['job_id'])
            if state['done']: break
            time.sleep(0.01)
        assert state['done'] and state['result']['ok']
        assert state['result']['sgd']['existe'] is exists
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
