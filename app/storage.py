"""Two human-readable TSV .txt files; safe atomic writes."""

from __future__ import annotations

import csv
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable

PATH_COLUMNS = ("id", "name", "path", "status")
ACCOUNT_COLUMNS = ("id", "project_name", "user_name", "password")


class StorageError(Exception):
    pass


def executable_directory() -> Path:
    """Use EXE folder after PyInstaller build, source folder otherwise."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def check_path(path_text: str) -> str:
    """Check local files/folders or Windows UNC paths (not HTTP URLs)."""
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


def next_id(rows: Iterable[dict[str, str]], prefix: str) -> str:
    indexes = []
    for row in rows:
        matched = re.fullmatch(re.escape(prefix) + r"(\d+)", row["id"])
        if matched:
            indexes.append(int(matched.group(1)))
    return f"{prefix}{max(indexes, default=0) + 1:04d}"


class DataStore:
    def __init__(self, root: Path):
        self.data_dir = root / "data"
        self.paths_file = self.data_dir / "paths.txt"
        self.accounts_file = self.data_dir / "accounts.txt"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._initialize_file(self.paths_file, PATH_COLUMNS)
            self._initialize_file(self.accounts_file, ACCOUNT_COLUMNS)
        except OSError as exc:
            raise StorageError(f"Cannot initialize data folder: {exc}") from exc

    @staticmethod
    def _initialize_file(file_path: Path, columns: tuple[str, ...]) -> None:
        if file_path.exists():
            return
        # Exclusive creation avoids overwriting an existing file from another app.
        with file_path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(columns)

    @staticmethod
    def _read(file_path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
        try:
            with file_path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                if reader.fieldnames != list(columns):
                    raise StorageError(
                        f"Unexpected columns in {file_path.name}.\n"
                        f"Expected: {', '.join(columns)}\n"
                        f"Actual: {reader.fieldnames}"
                    )
                result = []
                ids = set()
                for index, row in enumerate(reader, start=2):
                    if None in row or any(row.get(key) is None for key in columns):
                        raise StorageError(f"Invalid row {index} in {file_path.name}.")
                    rid = row["id"]
                    if not rid or rid in ids:
                        raise StorageError(f"Missing/duplicate id on row {index} in {file_path.name}.")
                    ids.add(rid)
                    result.append({column: row[column] for column in columns})
                return result
        except StorageError:
            raise
        except (OSError, UnicodeError, csv.Error) as exc:
            raise StorageError(f"Cannot read {file_path.name}: {exc}") from exc

    @staticmethod
    def _write(file_path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        temp_file: Path | None = None
        try:
            # Same directory is required for reliable atomic os.replace().
            with tempfile.NamedTemporaryFile(
                mode="w", newline="", encoding="utf-8",
                dir=file_path.parent, prefix=".tpm_", suffix=".tmp", delete=False,
            ) as handle:
                temp_file = Path(handle.name)
                writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_file, file_path)
        except (OSError, UnicodeError, csv.Error) as exc:
            raise StorageError(f"Cannot save {file_path.name}: {exc}") from exc
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def load_paths(self) -> list[dict[str, str]]:
        return self._read(self.paths_file, PATH_COLUMNS)

    def save_paths(self, rows: list[dict[str, str]]) -> None:
        self._write(self.paths_file, PATH_COLUMNS, rows)

    def load_accounts(self) -> list[dict[str, str]]:
        return self._read(self.accounts_file, ACCOUNT_COLUMNS)

    def save_accounts(self, rows: list[dict[str, str]]) -> None:
        self._write(self.accounts_file, ACCOUNT_COLUMNS, rows)
