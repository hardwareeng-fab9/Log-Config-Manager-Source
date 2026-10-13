"""Core tests that can run without opening a window."""

import csv
from pathlib import Path
import tempfile
import unittest

from app.security import hash_password, verify_password
from app.storage import ACCOUNT_COLUMNS, PATH_COLUMNS, DataStore, StorageError, check_path, next_id


class TestCore(unittest.TestCase):
    def test_hash_and_wrong_password(self):
        encoded = hash_password("S0meEngineerPassword!")
        self.assertTrue(encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("S0meEngineerPassword!", encoded))
        self.assertFalse(verify_password("wrong", encoded))
        self.assertFalse(verify_password("test", "12345678"))
        self.assertNotIn("S0meEngineerPassword!", encoded)

    def test_password_salt_is_unique(self):
        a = hash_password("same_password")
        b = hash_password("same_password")
        self.assertNotEqual(a, b)
        self.assertTrue(verify_password("same_password", a))
        self.assertTrue(verify_password("same_password", b))

    def test_password_short(self):
        with self.assertRaises(ValueError):
            hash_password("short")

    def test_path_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            file = folder / "test.txt"
            file.write_text("test", encoding="utf-8")
            self.assertEqual(check_path(str(folder)), "EXISTS")
            self.assertEqual(check_path(str(file)), "EXISTS")
            self.assertEqual(check_path(str(folder / 'absent')), "MISSING")
            self.assertEqual(check_path(""), "INVALID")
            self.assertEqual(check_path("https://github.com/repo/example.txt"), "UNSUPPORTED")

    def test_round_trip_and_tab_quoting(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            p = [{"id": "P0001", "name": "pytest", "path": "C:\\A\\test\tpart", "status": "MISSING"}]
            a = [{"id": "A0001", "project_name": "TEST", "user_name": "engineer",
                  "password": hash_password("strong_password") }]
            store.save_paths(p)
            store.save_accounts(a)
            self.assertEqual(store.load_paths(), p)
            self.assertEqual(store.load_accounts(), a)
            self.assertEqual(next_id(store.load_paths(), "P"), "P0002")
            with (Path(tmp) / "data" / "paths.txt").open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                self.assertEqual(reader.fieldnames, list(PATH_COLUMNS))

    def test_bad_header_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            store.accounts_file.write_text("bad\tcolumns\n", encoding="utf-8")
            with self.assertRaises(StorageError):
                store.load_accounts()
            self.assertEqual(store.accounts_file.read_text(encoding="utf-8"), "bad\tcolumns\n")

    def test_initial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            self.assertEqual(store.load_paths(), [])
            self.assertEqual(store.load_accounts(), [])
            self.assertTrue(store.paths_file.exists())
            self.assertTrue(store.accounts_file.exists())


if __name__ == "__main__":
    unittest.main()
