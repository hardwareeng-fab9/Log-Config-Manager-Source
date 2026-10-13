"""GUI behavior tests. Runs with Windows display or xvfb-run on Linux."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from app.gui import TestPathManagerApp
from app.security import hash_password
from app.storage import DataStore


class TestGUI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = DataStore(Path(self.tmp.name))
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.tmp.cleanup()
            self.skipTest(f"Display unavailable: {exc}")
        self.root.withdraw()
        self.app = None

    def tearDown(self):
        if self.app is not None:
            self.root.destroy()
        else:
            self.root.destroy()
        self.tmp.cleanup()

    def test_empty_accounts_no_setup_and_path_edit_works(self):
        self.app = TestPathManagerApp(self.root, self.store)
        self.assertEqual(self.app.accounts, [])
        self.assertTrue(self.app._authorize("ADD Path"))
        self.assertIn("OFF", self.app.footer_var.get())
        self.app.add_path()
        self.app.path_name_var.set("test_folder")
        self.app.path_value_var.set(self.tmp.name)
        with patch("app.gui.messagebox.askyesno", return_value=True):
            self.app.save_path()
        self.assertEqual(len(self.store.load_paths()), 1)
        self.assertEqual(self.store.load_paths()[0]["status"], "EXISTS")
        self.assertEqual(self.store.load_accounts(), [])
        self.app.refresh_all()
        self.assertEqual(self.app.accounts, [])

    def test_optional_first_account_no_project_required(self):
        self.app = TestPathManagerApp(self.root, self.store)
        self.app.add_account()
        self.app.account_user_var.set("engineer")
        self.app.account_project_var.set("")
        self.app.account_password_var.set("StrongPassword123!")
        with patch("app.gui.messagebox.askyesno", return_value=True):
            self.app.save_account()
        accounts = self.store.load_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["project_name"], "DEFAULT")
        self.assertIn("ON", self.app.footer_var.get())
        with patch("app.gui.AdminAuthDialog") as dialog:
            dialog.return_value.authorized = None
            self.assertFalse(self.app._authorize("EDIT Path"))
            dialog.assert_called_once()
        # Deleting the last account is possible after authorization and confirmation.
        self.app.account_tree.selection_set(accounts[0]["id"])
        with patch("app.gui.messagebox.askyesno", return_value=True), \
             patch.object(self.app, "_authorize", return_value=True):
            self.app.delete_account()
        self.assertEqual(self.store.load_accounts(), [])
        self.assertIn("OFF", self.app.footer_var.get())


if __name__ == "__main__":
    unittest.main()
