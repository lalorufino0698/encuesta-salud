"""Checks for local access and directory-query failure handling (no live AD)."""
import json
import subprocess
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from app.ad_directory import list_directory
from app.domain_main import directory_list


class DirectoryTests(unittest.TestCase):
    def request(self, host='127.0.0.1'):
        return Request({'type': 'http', 'client': (host, 12345)})

    @patch('app.domain_main.ad_registration.registration_directory')
    def test_remote_requests_never_query_ad(self, query):
        with self.assertRaises(HTTPException) as caught:
            directory_list(self.request('172.16.0.100'))
        self.assertEqual(caught.exception.status_code, 403)
        query.assert_not_called()

    @patch('app.domain_main.ad_registration.registration_directory')
    def test_success_preserves_unicode_and_disables_cache(self, query):
        query.return_value = {'grupos': [{'nombre': 'Logística'}], 'unidades_organizativas': []}
        response = directory_list(self.request())
        self.assertEqual(json.loads(response.body), query.return_value)
        self.assertEqual(response.headers['cache-control'], 'no-store')

    @patch('app.domain_main.ad_registration.registration_directory', side_effect=RuntimeError('Sesion no disponible'))
    def test_failure_is_not_reported_as_empty_directory(self, query):
        with self.assertRaises(HTTPException) as caught:
            directory_list(self.request())
        self.assertEqual(caught.exception.status_code, 503)

    @patch('app.ad_directory.subprocess.run')
    def test_powershell_failure_is_reported(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'Credenciales invalidas')
        with self.assertRaisesRegex(RuntimeError, 'Credenciales invalidas'):
            list_directory()

    @patch('app.ad_directory.subprocess.run')
    def test_invalid_json_is_reported(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, 'not json', '')
        with self.assertRaisesRegex(RuntimeError, 'respuesta inesperada'):
            list_directory()

    @patch('app.ad_directory.subprocess.run', side_effect=subprocess.TimeoutExpired('powershell', 90))
    def test_timeout_is_reported(self, run):
        with self.assertRaisesRegex(RuntimeError, '90 segundos'):
            list_directory()


if __name__ == '__main__':
    unittest.main()
