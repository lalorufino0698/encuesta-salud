import unittest
from unittest.mock import patch
from starlette.requests import Request
from fastapi import HTTPException
from app import ad_registration as registration
from app.domain_main import check_registration_access

BASE = 'DC=example,DC=test'
OU = 'OU=Legal,OU=CAFED,' + BASE
GROUP = 'CN=Legal,OU=grupos,' + BASE
CATALOG = {'base_dn': BASE, 'upn_suffix': 'example.test',
           'grupos': [{'nombre': 'Legal', 'dn': GROUP, 'cuenta': 'Asesoria Juridica'}],
           'unidades_organizativas': [{'nombre': 'Legal', 'dn': OU}]}


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        registration._plans.clear()

    def draft(self, **changes):
        data = dict(paternal='OROZCO', maternal='MERINO', given_names='EDUARDO RUFINO',
                    username='eorozco', area='Legal', ou_dn=OU, group_dn=GROUP, reviewed=True)
        data.update(changes)
        return registration.AccountDraft(**data)

    def checked_plan(self):
        with patch.object(registration, 'registration_directory', return_value=CATALOG), \
             patch.object(registration, 'run_operation', return_value={
                 'ok': True, 'upn': 'eorozco@example.test', 'dn': 'CN=Test,' + OU,
                 'min_password_length': 12, 'complexity': True}) as run:
            plan = registration.prepare(self.draft())
            self.assertEqual(run.call_args.args[0]['action'], 'validate')
            self.assertNotIn('password', run.call_args.args[0])
            return plan

    def confirmation(self, token):
        return registration.Confirmation(token=token, password='FakeTestOnly!123', password_confirmation='FakeTestOnly!123')

    def test_username_rule(self):
        self.assertEqual(registration.suggest_username('EDUARDO RUFINO', 'OROZCO'), 'eorozco')
        self.assertEqual(registration.suggest_username('Ángel', 'De la Cruz'), 'adelacruz')

    def test_review_required(self):
        with self.assertRaisesRegex(ValueError, 'Confirma'):
            registration.prepare(self.draft(reviewed=False))

    @patch.object(registration, 'registration_directory', return_value=CATALOG)
    @patch.object(registration, 'run_operation')
    def test_unlisted_group_cannot_be_submitted(self, run, catalog):
        with self.assertRaises(ValueError):
            registration.prepare(self.draft(group_dn='CN=Domain Admins,' + BASE))
        run.assert_not_called()

    def test_token_is_consumed_even_on_partial_failure(self):
        plan = self.checked_plan()
        outcome = {'ok': False, 'estado': 'parcial_deshabilitado'}
        with patch.object(registration, 'run_operation', return_value=outcome) as run:
            self.assertEqual(registration.create(self.confirmation(plan['token'])), outcome)
            with self.assertRaises(ValueError):
                registration.create(self.confirmation(plan['token']))
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0]['username'], 'eorozco')

    def test_expired_token_never_writes(self):
        registration._plans['expired'] = (0, {})
        with patch.object(registration, 'run_operation') as run:
            with self.assertRaises(ValueError):
                registration.create(self.confirmation('expired'))
            run.assert_not_called()

    def test_password_mismatch_never_writes(self):
        data = self.confirmation('unused').model_copy(update={'password_confirmation': registration.SecretStr('different')})
        with patch.object(registration, 'run_operation') as run:
            with self.assertRaises(ValueError):
                registration.create(data)
            run.assert_not_called()

    @patch.object(registration, 'list_directory')
    def test_catalog_filters_ous_and_groups(self, listing):
        listing.return_value = {'base_dn': BASE,
            'grupos': CATALOG['grupos'] + [{'nombre': 'Other', 'dn': 'CN=Other,CN=Users,' + BASE}],
            'unidades_organizativas': CATALOG['unidades_organizativas'] + [{'dn': 'OU=Other,' + BASE}]}
        result = registration.registration_directory()
        self.assertEqual(result['grupos'], CATALOG['grupos'])
        self.assertEqual(result['unidades_organizativas'], CATALOG['unidades_organizativas'])

    def test_local_origin_guard(self):
        def request(client='127.0.0.1', host='127.0.0.1:8001', origin='http://127.0.0.1:8001', marker=True):
            headers = [(b'host', host.encode()), (b'origin', origin.encode())]
            if marker: headers.append((b'x-ad-review', b'1'))
            return Request({'type': 'http', 'scheme': 'http', 'path': '/', 'query_string': b'',
                            'headers': headers, 'client': (client, 10), 'server': ('127.0.0.1', 8001)})
        check_registration_access(request())
        for kwargs in ({'client': '172.16.0.10'}, {'host': 'evil.test'}, {'origin': 'http://evil.test'}, {'marker': False}):
            with self.assertRaises(HTTPException):
                check_registration_access(request(**kwargs))


if __name__ == '__main__':
    unittest.main()
