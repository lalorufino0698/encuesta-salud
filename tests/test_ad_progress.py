import time
import unittest
from unittest.mock import patch
from app import ad_registration as ad
from app.domain_extraction import extract_plain_text
from fastapi.testclient import TestClient
from app.domain_main import app


class ProgressTests(unittest.TestCase):
    def payload(self):
        return dict(username='eorozco', given_names='EDUARDO RUFINO', surnames='OROZCO MERINO', minimum_length=30, ou_dn='OU=Test,DC=example,DC=test', group_dn='CN=Test,DC=example,DC=test')

    def test_generated_password_categories_and_length(self):
        for _ in range(20):
            password = ad.generate_password(self.payload())
            self.assertEqual(len(password), 30)
            self.assertTrue(any(c.isupper() for c in password))
            self.assertTrue(any(c.islower() for c in password))
            self.assertTrue(any(c.isdigit() for c in password))
            self.assertTrue(any(not c.isalnum() for c in password))
            self.assertNotIn('orozco', password.lower())

    def test_labeled_text_requires_no_username(self):
        result = extract_plain_text('Nombres: EDUARDO RUFINO\nApellidos: OROZCO MERINO\nDNI: 01234567\nÁrea: OTIC', services=['dominio'])
        self.assertEqual(len(result['usuarios']), 1)
        user = result['usuarios'][0]
        self.assertEqual(user['dni'], '01234567')
        self.assertEqual(user['nombres'], 'EDUARDO RUFINO')
        self.assertEqual(user['area'], 'OTIC')
        self.assertEqual(user['servicios_a_crear'], ['dominio'])
        self.assertEqual([item['servicio'] for item in user['inserts_simulados']], ['dominio'])

    def test_incomplete_labeled_text_fails(self):
        with self.assertRaises(ValueError):
            extract_plain_text('Nombres: TEST\nApellidos: PRUEBA\nDNI: 12345678', services=['dominio'])

    def test_three_lines_names_first_without_labels(self):
        for dni_line in ('DNI 47296949', 'DNI: 47296949', '47296949'):
            text = 'pruebita pruedados pruebados\n' + dni_line + '\notic'
            result = extract_plain_text(text, services=['dominio'])
            user = result['usuarios'][0]
            self.assertEqual(user['nombres'], 'pruebita')
            self.assertEqual(user['apellidos'], 'pruedados pruebados')
            self.assertEqual(user['nombre_completo_original'], 'pruebita pruedados pruebados')
            self.assertEqual(user['dni'], '47296949')
            self.assertEqual(user['area'], 'otic')
            self.assertTrue(result['requiere_revision'])
            self.assertEqual(user['servicios_a_crear'], ['dominio'])

    def test_three_lines_multiple_given_names(self):
        result = extract_plain_text('EDUARDO RUFINO OROZCO MERINO\nDNI 01234567\nOTIC', services=['dominio'])
        user = result['usuarios'][0]
        self.assertEqual(user['nombres'], 'EDUARDO RUFINO')
        self.assertEqual(user['apellidos'], 'OROZCO MERINO')
        self.assertEqual(user['dni'], '01234567')

    def test_success_reveals_password_only_in_final_result(self):
        self.check_job(True)

    def test_failure_never_reveals_password(self):
        self.check_job(False)

    def test_progress_api_is_local_and_not_cached(self):
        with TestClient(app, base_url='http://127.0.0.1', client=('127.0.0.1', 50000)) as client:
            with patch.object(ad, 'job_status', return_value={'done': False, 'events': ['Armando usuario'], 'result': None}):
                response = client.get('/api/registro-ad/progreso/test', headers={'X-AD-Review': '1'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['cache-control'], 'no-store')
                self.assertIsNone(response.json()['result'])
                denied = client.get('/api/registro-ad/progreso/test')
                self.assertEqual(denied.status_code, 403)

    def check_job(self, success):
        token = 'fake-test-token'
        ad._plans[token] = (time.monotonic() + 100, self.payload())
        def fake_run(payload, progress):
            progress('Armando usuario...')
            progress('Asignando OU...')
            progress('Asignando grupo...')
            return {'ok': success, 'estado': 'creado' if success else 'parcial_deshabilitado', 'upn': 'fake@example.test'}
        with patch.object(ad, 'run_creation', side_effect=fake_run) as run:
            job_id = ad.start_generated(ad.GeneratedConfirmation(token=token))['job_id']
            for _ in range(100):
                state = ad.job_status(job_id)
                if state['done']:
                    break
                time.sleep(.01)
            self.assertTrue(state['done'])
            self.assertEqual(run.call_count, 1)
            password = run.call_args.args[0]['password']
            self.assertNotIn(password, ' '.join(state['events']))
            self.assertEqual('password' in state['result'], success)
            with self.assertRaises(ValueError):
                ad.start_generated(ad.GeneratedConfirmation(token=token))
            ad._jobs.pop(job_id, None)


if __name__ == '__main__':
    unittest.main()
