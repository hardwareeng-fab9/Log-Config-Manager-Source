"""JSON storage, password and v1.1 migration tests (headless)."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from app.security import hash_password, verify_password
from app.storage import (ACCOUNT_COLUMNS, PATH_COLUMNS, DataStore, StorageError,
                         check_path, classify_path, next_id)


class TestCore(unittest.TestCase):
    def test_hash_and_wrong_password(self):
        encoded = hash_password("S0meEngineerPassword!")
        self.assertTrue(encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("S0meEngineerPassword!", encoded))
        self.assertFalse(verify_password("wrong", encoded))
        self.assertFalse(verify_password("test", "12345678"))
        self.assertNotIn("S0meEngineerPassword!", encoded)

    def test_password_salt_is_unique(self):
        a, b = hash_password("same_password"), hash_password("same_password")
        self.assertNotEqual(a, b)
        self.assertTrue(verify_password("same_password", a))
        self.assertTrue(verify_password("same_password", b))

    def test_password_short(self):
        with self.assertRaises(ValueError):
            hash_password("short")

    def test_path_status_and_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            file = folder / "test.txt"
            file.write_text("test", encoding="utf-8")
            self.assertEqual(check_path(str(folder)), "EXISTS")
            self.assertEqual(check_path(str(file)), "EXISTS")
            self.assertEqual(classify_path(str(folder)), "folder")
            self.assertEqual(classify_path(str(file)), "file")
            self.assertEqual(classify_path(str(folder / 'absent')), "unknown")
            self.assertEqual(check_path(str(folder / 'absent')), "MISSING")
            self.assertEqual(check_path(""), "INVALID")
            self.assertEqual(check_path("https://github.com/repo/example.txt"), "UNSUPPORTED")

    def test_round_trip_unicode_specials_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            paths = [{"id": "P0001", "name": "Nguồn 5V 🔌", "path": "C:\\A\\test\tpart",
                      "type": "unknown", "status": "MISSING", "last_checked": ""}]
            accounts = [{"id": "A0001", "project_name": "Dự án FCT", "user_name": "engineer",
                         "password_hash": hash_password("strong_password"),
                         "role": "engineer", "enabled": True}]
            store.save_paths(paths)
            store.save_accounts(accounts)
            self.assertEqual(store.load_paths(), paths)
            self.assertEqual(store.load_accounts(), accounts)
            self.assertEqual(next_id(store.load_paths(), "P"), "P0002")
            data = json.loads(store.paths_file.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], 1)
            self.assertEqual(data["paths"], paths)
            self.assertNotIn("strong_password", store.accounts_file.read_text(encoding="utf-8"))

    def test_initial_files_no_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            self.assertEqual(store.load_paths(), [])
            self.assertEqual(store.load_accounts(), [])
            self.assertTrue(store.paths_file.exists())
            self.assertTrue(store.accounts_file.exists())
            self.assertFalse((store.data_dir / "paths.txt").exists())
            self.assertEqual(json.loads(store.paths_file.read_text())["paths"], [])
            self.assertEqual(store.migration_messages, [])

    def test_corrupt_json_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            store.accounts_file.write_text('{"version":1,"accounts":', encoding="utf-8")
            with self.assertRaises(StorageError):
                store.load_accounts()
            with self.assertRaises(StorageError):
                DataStore(Path(tmp))
            self.assertEqual(store.accounts_file.read_text(encoding="utf-8"), '{"version":1,"accounts":')

    def test_wrong_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            store.paths_file.write_text('{"version": 55, "paths": []}', encoding="utf-8")
            with self.assertRaises(StorageError):
                store.load_paths()

    def test_schema_validation_and_duplicate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            row = {"id": "P0001", "name": "X", "path": "Z:/missing", "type": "unknown",
                   "status": "MISSING", "last_checked": ""}
            with self.assertRaises(StorageError):
                store.save_paths([row, row])
            with self.assertRaises(StorageError):
                store.save_paths([{**row, "type": "bad"}])
            with self.assertRaises(StorageError):
                store.save_accounts([{"id": "A0001", "project_name": "X", "user_name": "u",
                                      "password_hash": "plaintext", "role": "engineer", "enabled": True}])
            self.assertEqual(store.load_paths(), [])
            self.assertEqual(store.load_accounts(), [])

    @staticmethod
    def write_legacy(file: Path, columns: tuple, records: list[dict]) -> None:
        with file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, delimiter="\t")
            writer.writeheader()
            writer.writerows(records)

    def test_auto_migration_preserves_txt_and_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            path = data / "existing folder"
            path.mkdir()
            legacy_paths = data / "paths.txt"
            legacy_accounts = data / "accounts.txt"
            self.write_legacy(legacy_paths, PATH_COLUMNS, [
                {"id": "P0003", "name": "Thư mục FCT", "path": str(path), "status": "EXISTS"}])
            old_hash = hash_password("AdminPassword!123")
            self.write_legacy(legacy_accounts, ACCOUNT_COLUMNS, [
                {"id": "A0002", "project_name": "DEFAULT", "user_name": "Boss", "password": old_hash}])
            before_paths = legacy_paths.read_bytes()
            before_accounts = legacy_accounts.read_bytes()
            store = DataStore(Path(tmp))
            self.assertEqual(len(store.migration_messages), 2)
            self.assertEqual(store.load_paths()[0]["id"], "P0003")
            self.assertEqual(store.load_paths()[0]["type"], "folder")
            self.assertEqual(store.load_accounts()[0]["password_hash"], old_hash)
            self.assertTrue(verify_password("AdminPassword!123", store.load_accounts()[0]["password_hash"]))
            self.assertEqual(legacy_paths.read_bytes(), before_paths)
            self.assertEqual(legacy_accounts.read_bytes(), before_accounts)
            self.assertEqual(DataStore(Path(tmp)).migration_messages, [])

    def test_json_authoritative_even_when_txt_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(Path(tmp))
            self.write_legacy(store.data_dir / "paths.txt", PATH_COLUMNS, [
                {"id": "P0042", "name": "old", "path": "X", "status": "MISSING"}])
            again = DataStore(Path(tmp))
            self.assertEqual(again.load_paths(), [])
            self.assertEqual(again.migration_messages, [])

    def test_invalid_legacy_preserved_no_json_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            txt = data / "paths.txt"
            txt.write_text("bad\tcolumns\n", encoding="utf-8")
            with self.assertRaises(StorageError):
                DataStore(Path(tmp))
            self.assertEqual(txt.read_text(), "bad\tcolumns\n")
            self.assertFalse((data / "paths.json").exists())


if __name__ == "__main__":
    unittest.main()
