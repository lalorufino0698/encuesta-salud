import unittest
from unittest.mock import patch
from app.dni_lookup import fetch_dni_data


class DniTests(unittest.TestCase):
    @patch('app.dni_lookup._json', side_effect=[{'names': 'Ana', 'paternalLastName': 'Pérez', 'maternalLastName': 'Lima'}])
    def test_primary(self, call):
        result = fetch_dni_data('12345678')
        self.assertEqual(result['origen'], 'principal')
        self.assertEqual(result['nombre_completo'], 'ANA PÉREZ LIMA')

    @patch('app.dni_lookup._json', side_effect=[RuntimeError(), {'consultarResponse': {'return': {'coResultado': '0000', 'datosPersona': {'prenombres': 'Ana', 'apPrimer': 'Pérez', 'apSegundo': 'Lima'}}}}])
    def test_fallback(self, call):
        self.assertEqual(fetch_dni_data('12345678')['origen'], 'secundaria')
        self.assertEqual(call.call_count, 2)

    def test_invalid_dni(self):
        with self.assertRaises(ValueError):
            fetch_dni_data('1234ABCD')
