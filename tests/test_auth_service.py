import unittest
import hashlib
from kool_tpv.utils.auth_service import AuthService


class FakeDB:
    def __init__(self, admins):
        # admins: list of tuples (id, nombre, password_hash)
        self._admins = admins

    def fetch_all(self, query):
        return self._admins


class TestAuthService(unittest.TestCase):
    def test_validate_admin_password_success(self):
        pw = 's3cret'
        pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
        fake_db = FakeDB([(1, 'admin1', pw_hash)])
        svc = AuthService(fake_db)
        res = svc.validate_admin_password(pw)
        self.assertIsInstance(res, tuple)
        self.assertTrue(res[0])
        self.assertIsInstance(res[1], dict)
        self.assertEqual(res[1].get('id'), 1)
        self.assertEqual(res[1].get('nombre'), 'admin1')

    def test_validate_admin_password_failure(self):
        pw = 's3cret'
        pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
        fake_db = FakeDB([(1, 'admin1', pw_hash)])
        svc = AuthService(fake_db)
        res = svc.validate_admin_password('wrong')
        self.assertIsInstance(res, tuple)
        self.assertFalse(res[0])
        self.assertIsNone(res[1])


if __name__ == '__main__':
    unittest.main()
