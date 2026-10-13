"""Versioned JSON storage with atomic writes and safe, one-time TSV migration.

Runtime files: data/paths.json and data/accounts.json. Legacy TSV files are
never modified or deleted. No sensitive data is sent to a network service.
"""

from __future__ import annotations

import csv
from datetime import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
PATH_COLUMNS = ("id", "name", "path", "status")  # legacy TXT
ACCOUNT_COLUMNS = ("id", "project_name", "user_name", "password")  # legacy TXT
PATH_FIELDS = ("id", "name", "path", "type", "status", "last_checked")
ACCOUNT_FIELDS = ("id", "project_name", "user_name", "password_hash", "role", "enabled")
VALID_STATUSES = {"EXISTS", "MISSING", "INVALID", "UNSUPPORTED", "UNCHECKED"}
VALID_TYPES = {"file", "folder", "unknown"}


class StorageError(Exception):
    """A file was corrupt, incompatible or could not be written."""


def executable_directory() -> Path:
    """Use EXE folder after PyInstaller build, source folder otherwise."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def check_path(path_text: str) -> str:
    """Check local files/folders or UNC paths. HTTP URLs are not local paths."""
    value = path_text.strip().strip('"')
    if not value:
        return "INVALID"
    if "://" in value:
        return "UNSUPPORTED"
    try:
        expanded = os.path.expandvars(os.path.expanduser(value))
        return "EXISTS" if Path(expanded).exists() else "MISSING"
    except (OSError, ValueError):
        return "INVALID"


def classify_path(path_text: str) -> str:
    """Recognize an existing file or directory, else report unknown."""
    if check_path(path_text) != "EXISTS":
        return "unknown"
    try:
        path = Path(os.path.expandvars(os.path.expanduser(path_text.strip().strip('"'))))
        if path.is_file():
            return "file"
        if path.is_dir():
            return "folder"
    except (ValueError, OSError):
        pass
    return "unknown"


def checked_at() -> str:
    """Human-readable local timestamp with explicit timezone offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def next_id(rows: Iterable[dict], prefix: str) -> str:
    indexes = []
    for row in rows:
        match = re.fullmatch(re.escape(prefix) + r"(\d+)", str(row["id"]))
        if match:
            indexes.append(int(match.group(1)))
    return f"{prefix}{max(indexes, default=0) + 1:04d}"


class DataStore:
    def __init__(self, root: Path):
        self.data_dir = Path(root) / "data"
        self.paths_file = self.data_dir / "paths.json"
        self.accounts_file = self.data_dir / "accounts.json"
        self.migration_messages: list[str] = []
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._init_or_migrate(self.paths_file, "paths", self.data_dir / "paths.txt")
            self._init_or_migrate(self.accounts_file, "accounts", self.data_dir / "accounts.txt")
            # Detect corrupt data early, before any GUI makes edits.
            self.load_paths()
            self.load_accounts()
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError(f"Cannot initialize data folder {self.data_dir}: {exc}") from exc

    def _init_or_migrate(self, json_file: Path, kind: str, txt_file: Path) -> None:
        if json_file.exists():
            # Existing JSON is authoritative; never clobber with old TXT.
            return
        if txt_file.is_file():
            legacy = self._read_legacy(txt_file, PATH_COLUMNS if kind == "paths" else ACCOUNT_COLUMNS)
            if kind == "paths":
                rows = [
                    {"id": r["id"], "name": r["name"], "path": r["path"],
                     "type": classify_path(r["path"]), "status": r["status"], "last_checked": ""}
                    for r in legacy
                ]
            else:
                rows = [
                    {"id": r["id"], "project_name": r["project_name"],
                     "user_name": r["user_name"], "password_hash": r["password"],
                     "role": "engineer", "enabled": True}
                    for r in legacy
                ]
            self._validate_rows(rows, kind, json_file)
            self._create_exclusive(json_file, {"version": SCHEMA_VERSION, kind: rows})
            self.migration_messages.append(
                f"Imported {len(rows)} {kind} from {txt_file.name} to {json_file.name}; TXT retained as backup."
            )
        else:
            self._create_exclusive(json_file, {"version": SCHEMA_VERSION, kind: []})

    @staticmethod
    def _create_exclusive(path: Path, payload: dict) -> None:
        try:
            # Exclusive creation: never overwrite a file which appeared concurrently.
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            return  # another app created it, and load_* will validate it
        except (OSError, UnicodeError, TypeError) as exc:
            raise StorageError(f"Cannot create {path.name}: {exc}") from exc

    @staticmethod
    def _read_legacy(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if reader.fieldnames != list(columns):
                    raise StorageError(f"Invalid TXT header in {path.name}; expected: {', '.join(columns)}")
                rows = []
                for lineno, row in enumerate(reader, start=2):
                    if None in row or any(row.get(k) is None for k in columns):
                        raise StorageError(f"Invalid row {lineno} in legacy {path.name}")
                    rows.append({k: row[k] for k in columns})
                return rows
        except StorageError:
            raise
        except (OSError, UnicodeError, csv.Error) as exc:
            raise StorageError(f"Cannot read legacy {path.name}: {exc}") from exc

    @staticmethod
    def _validate_rows(rows: object, kind: str, path: Path) -> None:
        if not isinstance(rows, list):
            raise StorageError(f"{path.name}: '{kind}' must be an array.")
        required = PATH_FIELDS if kind == "paths" else ACCOUNT_FIELDS
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict) or not all(field in row for field in required):
                raise StorageError(f"{path.name}: record {index} requires fields: {', '.join(required)}")
            if any(not isinstance(row[field], str) for field in required if field != "enabled"):
                raise StorageError(f"{path.name}: record {index} has a non-string field.")
            rid = row["id"]
            if not rid or rid in seen:
                raise StorageError(f"{path.name}: empty or duplicate ID '{rid}'.")
            seen.add(rid)
            if kind == "paths":
                if not row["name"].strip() or not row["path"].strip():
                    raise StorageError(f"{path.name}: record {rid} missing name or path.")
                if row["status"] not in VALID_STATUSES or row["type"] not in VALID_TYPES:
                    raise StorageError(f"{path.name}: invalid status/type for {rid}.")
            else:
                if not row["user_name"].strip() or not row["project_name"].strip():
                    raise StorageError(f"{path.name}: incomplete account {rid}.")
                if not row["password_hash"].startswith("pbkdf2_sha256$"):
                    raise StorageError(f"{path.name}: account {rid} must use a password hash (not plaintext).")
                if row["role"] not in ("admin", "engineer"):
                    raise StorageError(f"{path.name}: invalid role for {rid}.")
                if type(row["enabled"]) is not bool:
                    raise StorageError(f"{path.name}: enabled must be true/false for {rid}.")

    @classmethod
    def _read(cls, path: Path, kind: str) -> list[dict]:
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or payload.get("version") != SCHEMA_VERSION:
                raise StorageError(f"{path.name}: JSON version must be {SCHEMA_VERSION}.")
            rows = payload.get(kind)
            cls._validate_rows(rows, kind, path)
            return rows
        except StorageError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise StorageError(f"Cannot read {path.name}: {exc}") from exc

    @classmethod
    def _write(cls, path: Path, kind: str, rows: list[dict]) -> None:
        cls._validate_rows(rows, kind, path)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                prefix=".tpm_", suffix=".tmp", delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump({"version": SCHEMA_VERSION, kind: rows}, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        except (OSError, UnicodeError, TypeError, ValueError) as exc:
            raise StorageError(f"Cannot save {path.name}: {exc}") from exc
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def load_paths(self) -> list[dict]:
        return self._read(self.paths_file, "paths")

    def save_paths(self, rows: list[dict]) -> None:
        self._write(self.paths_file, "paths", rows)

    def load_accounts(self) -> list[dict]:
        return self._read(self.accounts_file, "accounts")

    def save_accounts(self, rows: list[dict]) -> None:
        self._write(self.accounts_file, "accounts", rows)
