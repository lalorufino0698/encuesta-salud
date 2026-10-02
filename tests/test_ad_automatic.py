import time
import unittest
from unittest.mock import patch
from app import ad_registration as ad

BASE = 'DC=example,DC=test'
GROUP = {'nombre': 'GDE', 'cuenta': 'Gerencia de Desarrollo Educativo', 'dn': 'CN=GDE,OU=grupos,' + BASE}
OU = {'nombre': 'Educativo', 'dn': 'OU=Educativo,OU=CAFED,' + BASE}
CAT = {'grupos': [GROUP], 'unidades_organizativas': [OU], 'base_dn': BASE, 'upn_suffix': 'example.test'}


class AutomaticTests(unittest.TestCase):
    def draft(self):
        return ad.AutomaticAccount(paternal='OROZCO', maternal='MERINO', given_names='EDUARDO RUFINO', area='Gerencia de Desarrollo Educativo', reviewed=True)

    def test_group_acronym_and_full_name(self):
        for term in ('GDE', 'gerencia de desarrollo educativo'):
            self.assertEqual(ad.resolve_unique([GROUP], [term], ['nombre', 'cuenta']), GROUP)

    def test_ou_phrase_matching(self):
        self.assertEqual(ad.resolve_unique([OU], ['Gerencia de Desarrollo Educativo'], ['nombre']), OU)

    def test_ambiguous_match_stops(self):
        other = dict(GROUP, dn='CN=GDE,OU=other,' + BASE)
        self.assertIsNone(ad.resolve_unique([GROUP, other], ['GDE'], ['nombre', 'cuenta']))

    def test_similar_spelling_is_not_a_match(self):
        self.assertIsNone(ad.resolve_unique([GROUP], ['GDEEE'], ['nombre', 'cuenta']))

    @patch.object(ad, 'registration_directory', return_value=CAT)
    def test_resolves_and_validates_before_password(self, catalog):
        with patch.object(ad, 'run_operation', return_value={'ok': True, 'upn': 'eorozco@example.test', 'dn': 'CN=Test,' + OU['dn'], 'min_password_length': 12, 'complexity': True}) as validate:
            messages = []
            payload = ad.automatic_payload(self.draft(), messages.append)
            self.assertEqual(payload['username'], 'eorozco')
            self.assertEqual(payload['group_dn'], GROUP['dn'])
            self.assertEqual(payload['ou_dn'], OU['dn'])
            self.assertEqual(validate.call_args.args[0]['action'], 'validate')
            self.assertNotIn('password', payload)

    def test_existing_user_never_generates_password_or_writes(self):
        with patch.object(ad, 'automatic_payload', side_effect=ValueError('El usuario ya existe')), patch.object(ad, 'generate_password') as password, patch.object(ad, 'run_creation') as write:
            job = ad.start_automatic(self.draft())['job_id']
            for _ in range(100):
                state = ad.job_status(job)
                if state['done']: break
                time.sleep(.01)
            self.assertTrue(state['done'])
            self.assertEqual(state['result']['estado'], 'requiere_correccion')
            password.assert_not_called(); write.assert_not_called()

    def test_confirmation_required(self):
        with self.assertRaises(ValueError):
            ad.start_automatic(self.draft().model_copy(update={'reviewed': False}))

    def test_service_failure_does_not_request_person_corrections(self):
        with patch.object(ad, 'automatic_payload', side_effect=RuntimeError('Permisos insuficientes')), patch.object(ad, 'run_creation') as write:
            job = ad.start_automatic(self.draft())['job_id']
            for _ in range(100):
                state = ad.job_status(job)
                if state['done']: break
                time.sleep(.01)
            self.assertTrue(state['done'])
            self.assertEqual(state['result']['estado'], 'error_servicio')
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
