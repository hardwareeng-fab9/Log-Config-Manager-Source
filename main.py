"""Start TestPath Manager from source or from the Windows EXE."""

import tkinter as tk
from tkinter import messagebox

from app.gui import TestPathManagerApp
from app.storage import DataStore, StorageError, executable_directory


def main() -> None:
    root = tk.Tk()
    try:
        store = DataStore(executable_directory())
        TestPathManagerApp(root, store)
        root.mainloop()
    except (StorageError, PermissionError) as exc:
        messagebox.showerror("TestPath Manager — Data error", str(exc), parent=root)
        root.destroy()


if __name__ == "__main__":
    main()
