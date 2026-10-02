import unittest
from unittest.mock import patch
from app.ad_config import process_environment, redact


class ConfigTests(unittest.TestCase):
    @patch('app.ad_config.os.environ', {})
    @patch('app.ad_config.dotenv_values')
    def test_credentials_loaded_without_interpolation(self, values):
        values.return_value = {'AD_USERNAME': 'operator', 'AD_PASSWORD': 'fake${literal}#secret', 'AD_DOMAIN': 'LAB'}
        env = process_environment()
        self.assertEqual(env['AD_PASSWORD'], 'fake${literal}#secret')
        self.assertFalse(values.call_args.kwargs['interpolate'])
        self.assertEqual(redact('fake${literal}#secret', env), '[REDACTADO]')

    @patch('app.ad_config.os.environ', {})
    @patch('app.ad_config.dotenv_values', return_value={'AD_USERNAME': 'operator', 'AD_PASSWORD': ''})
    def test_partial_credentials_fail(self, values):
        with self.assertRaises(RuntimeError):
            process_environment()

    @patch('app.ad_config.os.environ', {'AD_USERNAME': 'environment-user', 'AD_PASSWORD': 'fake'})
    @patch('app.ad_config.dotenv_values', return_value={'AD_USERNAME': 'file-user', 'AD_PASSWORD': 'other'})
    def test_environment_takes_precedence(self, values):
        self.assertEqual(process_environment()['AD_USERNAME'], 'environment-user')
