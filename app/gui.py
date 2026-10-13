"""Tkinter GUI: path editor, engineer credentials, admin confirmation, event log."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from .storage import DataStore, StorageError, check_path, classify_path, checked_at, next_id


class AdminAuthDialog(simpledialog.Dialog):
    """Confirm an Engineer password when one or more accounts are configured."""

    def __init__(self, parent: tk.Misc, accounts: list[dict[str, str]], action: str,
                 suggested: tuple[str, str] | None = None):
        self.accounts = accounts
        self.action = action
        self.suggested = suggested
        self.authorized: dict[str, str] | None = None
        super().__init__(parent, "Engineer Authorization")

    def body(self, master: tk.Misc) -> tk.Widget:
        ttk.Label(master, text="Engineer approval required:", foreground="#9f2c2c").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(master, text=self.action, wraplength=400).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self.password = tk.StringVar()
        if len(self.accounts) == 1:
            # A single-manager setup: only the Engineer password is needed.
            only = self.accounts[0]
            self.project = tk.StringVar(value=only["project_name"])
            self.username = tk.StringVar(value=only["user_name"])
            ttk.Label(master, text="Engineer").grid(row=2, column=0, sticky="w", pady=5)
            ttk.Label(master, text=f"{only['user_name']} ({only['project_name']})").grid(
                row=2, column=1, sticky="w", pady=5)
            ttk.Label(master, text="Password").grid(row=3, column=0, sticky="w", pady=5)
            entry = ttk.Entry(master, textvariable=self.password, show="*", width=33)
            entry.grid(row=3, column=1, sticky="ew", pady=5)
            return entry
        projects = sorted({a["project_name"] for a in self.accounts}, key=str.casefold)
        suggested_project = self.suggested[0] if self.suggested and self.suggested[0] in projects else projects[0]
        self.project = tk.StringVar(value=suggested_project)
        self.username = tk.StringVar(value=self.suggested[1] if self.suggested else "")
        ttk.Label(master, text="Project").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=5)
        combo = ttk.Combobox(master, textvariable=self.project, values=projects, state="readonly", width=31)
        combo.grid(row=2, column=1, sticky="ew", pady=5)
        ttk.Label(master, text="Engineer username").grid(row=3, column=0, sticky="w", pady=5)
        name = ttk.Entry(master, textvariable=self.username, width=33)
        name.grid(row=3, column=1, sticky="ew", pady=5)
        ttk.Label(master, text="Password").grid(row=4, column=0, sticky="w", pady=5)
        password_entry = ttk.Entry(master, textvariable=self.password, show="*", width=33)
        password_entry.grid(row=4, column=1, sticky="ew", pady=5)
        return password_entry if self.username.get() else name

    def validate(self) -> bool:
        project = self.project.get().strip().casefold()
        username = self.username.get().strip().casefold()
        for row in self.accounts:
            if not row.get("enabled", True):
                continue
            if row["project_name"].casefold() == project and row["user_name"].casefold() == username:
                if verify_password(self.password.get(), row["password_hash"]):
                    self.authorized = row
                    self.password.set("")
                    return True
                break
        self.password.set("")
        messagebox.showerror("Access denied", "Invalid project, engineer username or password.", parent=self)
        return False


class TestPathManagerApp:
    def __init__(self, root: tk.Tk, store: DataStore):
        self.root = root
        self.store = store
        self.paths = store.load_paths()
        self.accounts = store.load_accounts()
        self.path_mode: str | None = None
        self.account_mode: str | None = None
        self.path_edit_id: str | None = None
        self.account_edit_id: str | None = None
        self.last_login: tuple[str, str] | None = None

        root.title("TestPath Manager  |  Path & Engineer Access Control")
        root.geometry("1240x780")
        root.minsize(1000, 650)
        self._make_styles()
        self._make_layout()
        self._populate_paths()
        self._populate_accounts()
        self._set_path_mode(None)
        self._set_account_mode(None)
        self._update_counts()
        self.log("Application launched. JSON files are stored beside the executable.")
        for migration_message in self.store.migration_messages:
            self.log(migration_message, "OK")
        self.log(f"Path records: {len(self.paths)} | Engineer accounts: {len(self.accounts)}")
        if self.accounts:
            self.log("Engineer password protection is ON (configured accounts found).", "OK")
        else:
            self.log("No Engineer account. Protection is OFF; no registration is required.", "WARN")

    def _make_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.root.configure(background="#edf2f7")
        style.configure("TFrame", background="#edf2f7")
        style.configure("TLabel", background="#edf2f7", foreground="#243246", font=("Segoe UI", 10))
        style.configure("TButton", padding=(11, 7), font=("Segoe UI", 9))
        style.configure("Accent.TButton", background="#2167b6", foreground="white")
        style.map("Accent.TButton", background=[("active", "#185598"), ("disabled", "#bac6d5")])
        style.configure("Danger.TButton", foreground="#b12836")
        style.configure("Heading.TLabel", font=("Segoe UI Semibold", 18), foreground="#163b65")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#60718a")
        style.configure("TLabelframe", background="#edf2f7")
        style.configure("TLabelframe.Label", background="#edf2f7", foreground="#1b4977",
                        font=("Segoe UI Semibold", 10))
        style.configure("TNotebook", background="#edf2f7")
        style.configure("TNotebook.Tab", padding=(20, 10), font=("Segoe UI Semibold", 10))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=29,
                        background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#d3e5fb")], foreground=[("selected", "#183554")])

    def _make_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(20, 14, 20, 8))
        header.pack(fill="x")
        ttk.Label(header, text="TestPath Manager", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header, text=f"Path configuration  •  Engineer access control  |  Data: {self.store.data_dir}",
                  style="Sub.TLabel").pack(anchor="w", pady=(3, 0))

        self.split = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.split.pack(fill="both", expand=True, padx=14, pady=(4, 8))
        top = ttk.Frame(self.split)
        bottom = ttk.Frame(self.split)
        self.split.add(top, weight=4)
        self.split.add(bottom, weight=1)
        self.tabs = ttk.Notebook(top)
        self.tabs.pack(fill="both", expand=True)
        self.path_tab = ttk.Frame(self.tabs, padding=12)
        self.account_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.path_tab, text="  Path Management  ")
        self.tabs.add(self.account_tab, text="  Engineer Accounts  ")
        self._make_paths_tab()
        self._make_accounts_tab()
        self._make_event_log(bottom)
        self.footer_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.footer_var, style="Sub.TLabel",
                  padding=(20, 0, 20, 10)).pack(fill="x")
        self.root.bind("<Escape>", self._escape)

    @staticmethod
    def _make_tree(parent: tk.Misc, columns: tuple[str, ...],
                   headers: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=(9, 5))
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for col, heading, width in zip(columns, headers, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=60, stretch=col not in ("id", "status", "password_hash"))
        ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        return tree

    def _make_paths_tab(self) -> None:
        self.path_tab.grid_columnconfigure(0, weight=4)
        self.path_tab.grid_columnconfigure(1, weight=2)
        self.path_tab.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(self.path_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = ttk.LabelFrame(self.path_tab, text="  Path Details  ", padding=14)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(left, text="Configured file and folder paths", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        row = ttk.Frame(left)
        row.pack(fill="x", pady=(8, 2))
        self.path_check_btn = ttk.Button(row, text="Check Selected", command=self.check_selected_path)
        self.path_check_btn.pack(side="left", padx=(0, 6))
        self.path_check_all_btn = ttk.Button(row, text="Check All", command=self.check_all_paths)
        self.path_check_all_btn.pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Reload JSON", command=self.refresh_all).pack(side="left")
        self.path_tree = self._make_tree(left, ("id", "name", "path", "status"),
                                         ("ID", "Name", "Path", "Status"), (84, 170, 350, 120))
        self.path_tree.bind("<<TreeviewSelect>>", self._on_path_select)

        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=2)
        self.path_id_var = tk.StringVar()
        self.path_name_var = tk.StringVar()
        self.path_value_var = tk.StringVar()
        self.path_status_var = tk.StringVar(value="—")
        ttk.Label(right, text="Path ID", font=("Segoe UI Semibold", 9)).grid(row=0, column=0, sticky="w")
        ttk.Label(right, text="Path name", font=("Segoe UI Semibold", 9)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Entry(right, textvariable=self.path_id_var, state="readonly", width=12).grid(
            row=1, column=0, sticky="ew", pady=(3, 9))
        self.path_name_entry = ttk.Entry(right, textvariable=self.path_name_var)
        self.path_name_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(3, 9))
        ttk.Label(right, text="Full path (type or browse)", font=("Segoe UI Semibold", 9)).grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.path_value_entry = ttk.Entry(right, textvariable=self.path_value_var)
        self.path_value_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 5))
        browse = ttk.Frame(right)
        browse.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 13))
        self.path_file_btn = ttk.Button(browse, text="Choose File...", command=self.browse_file)
        self.path_file_btn.pack(side="left", padx=(0, 6))
        self.path_folder_btn = ttk.Button(browse, text="Choose Folder...", command=self.browse_folder)
        self.path_folder_btn.pack(side="left")
        status_line = ttk.Frame(right)
        status_line.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(status_line, text="Status:", font=("Segoe UI Semibold", 9)).pack(side="left")
        ttk.Label(status_line, textvariable=self.path_status_var).pack(side="left", padx=(9, 0))
        self.path_field_check_btn = ttk.Button(right, text="Check Entered Path", command=self.check_entered_path)
        self.path_field_check_btn.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Separator(right).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 13))
        controls = ttk.Frame(right)
        controls.grid(row=8, column=0, columnspan=2, sticky="ew")
        for i in range(3):
            controls.grid_columnconfigure(i, weight=1)
        self.path_add_btn = ttk.Button(controls, text="Add", command=self.add_path)
        self.path_edit_btn = ttk.Button(controls, text="Edit", command=self.edit_path)
        self.path_update_btn = ttk.Button(controls, text="Update / Save", style="Accent.TButton", command=self.save_path)
        self.path_cancel_btn = ttk.Button(controls, text="Cancel", command=self.cancel_path)
        self.path_delete_btn = ttk.Button(controls, text="Delete", style="Danger.TButton", command=self.delete_path)
        self.path_add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        self.path_edit_btn.grid(row=0, column=1, sticky="ew", padx=4, pady=3)
        self.path_delete_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=3)
        self.path_update_btn.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 4), pady=3)
        self.path_cancel_btn.grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=3)
        ttk.Label(right, text="Optional protection: Engineer password is requested only when accounts exist.",
                  style="Sub.TLabel", wraplength=310).grid(
                      row=9, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _make_accounts_tab(self) -> None:
        self.account_tab.grid_columnconfigure(0, weight=4)
        self.account_tab.grid_columnconfigure(1, weight=2)
        self.account_tab.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(self.account_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        right = ttk.LabelFrame(self.account_tab, text="  Engineer Account Details  ", padding=14)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(left, text="Engineer credentials by project", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(left, text="Passwords are stored as salted hashes; actual passwords cannot be displayed.",
                  style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(7, 2))
        self.account_tree = self._make_tree(left,
                                            ("id", "project_name", "user_name", "password_hash"),
                                            ("ID", "Project Name", "User Name", "Password"),
                                            (80, 220, 200, 120))
        self.account_tree.bind("<<TreeviewSelect>>", self._on_account_select)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=2)
        self.account_id_var = tk.StringVar()
        self.account_project_var = tk.StringVar()
        self.account_user_var = tk.StringVar()
        self.account_password_var = tk.StringVar()
        ttk.Label(right, text="Account ID", font=("Segoe UI Semibold", 9)).grid(row=0, column=0, sticky="w")
        ttk.Label(right, text="Project name (optional)", font=("Segoe UI Semibold", 9)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Entry(right, textvariable=self.account_id_var, state="readonly", width=12).grid(
            row=1, column=0, sticky="ew", pady=(3, 12))
        self.account_project_entry = ttk.Entry(right, textvariable=self.account_project_var)
        self.account_project_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(3, 12))
        ttk.Label(right, text="Engineer user name", font=("Segoe UI Semibold", 9)).grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.account_user_entry = ttk.Entry(right, textvariable=self.account_user_var)
        self.account_user_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 12))
        ttk.Label(right, text="New password", font=("Segoe UI Semibold", 9)).grid(
            row=4, column=0, columnspan=2, sticky="w")
        self.account_password_entry = ttk.Entry(right, textvariable=self.account_password_var, show="*")
        self.account_password_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(3, 5))
        ttk.Label(right, text="On Edit, leave password blank to keep it unchanged.",
                  style="Sub.TLabel", wraplength=320).grid(
                      row=6, column=0, columnspan=2, sticky="w", pady=(0, 17))
        ttk.Separator(right).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 13))
        controls = ttk.Frame(right)
        controls.grid(row=8, column=0, columnspan=2, sticky="ew")
        for i in range(3):
            controls.grid_columnconfigure(i, weight=1)
        self.account_add_btn = ttk.Button(controls, text="Add", command=self.add_account)
        self.account_edit_btn = ttk.Button(controls, text="Edit", command=self.edit_account)
        self.account_update_btn = ttk.Button(controls, text="Update / Save", style="Accent.TButton",
                                             command=self.save_account)
        self.account_cancel_btn = ttk.Button(controls, text="Cancel", command=self.cancel_account)
        self.account_delete_btn = ttk.Button(controls, text="Delete", style="Danger.TButton",
                                             command=self.delete_account)
        self.account_add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        self.account_edit_btn.grid(row=0, column=1, sticky="ew", padx=4, pady=3)
        self.account_delete_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=3)
        self.account_update_btn.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 4), pady=3)
        self.account_cancel_btn.grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=3)
        ttk.Label(right, text="No account is required. Add one only to enable password protection.",
                  style="Sub.TLabel", wraplength=310).grid(
                      row=9, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _make_event_log(self, parent: tk.Misc) -> None:
        frame = ttk.LabelFrame(parent, text="  EVENT LOG — User Actions & Validation  ", padding=(9, 7))
        frame.pack(fill="both", expand=True, pady=(5, 0))
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Session activity", style="Sub.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Clear View", command=self.clear_log).pack(side="right")
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True, pady=(5, 0))
        self.events = tk.Text(text_frame, height=8, font=("Consolas", 9), wrap="word",
                              background="#122033", foreground="#dce7f7", insertbackground="white",
                              relief="flat", padx=10, pady=8, state="disabled")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.events.yview)
        self.events.configure(yscrollcommand=scrollbar.set)
        self.events.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.events.tag_configure("INFO", foreground="#d9e7f8")
        self.events.tag_configure("OK", foreground="#70e0b2")
        self.events.tag_configure("WARN", foreground="#ffd18b")
        self.events.tag_configure("ERROR", foreground="#ffa5ae")

    def log(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.events.configure(state="normal")
        self.events.insert("end", f"[{timestamp}] [{level:5s}] {message}\n", level)
        self.events.see("end")
        self.events.configure(state="disabled")

    def clear_log(self) -> None:
        self.events.configure(state="normal")
        self.events.delete("1.0", "end")
        self.events.configure(state="disabled")
        self.log("Event log view cleared.")

    def _update_counts(self) -> None:
        self.footer_var.set(
            f"Path entries: {len(self.paths)}    |    Engineer accounts: {len(self.accounts)}    |    "
            "JSON format: UTF-8 (v1)    |    Protection: "
            + ("ON (Engineer password)" if self.accounts else "OFF (no account)")
        )

    def _authorize(self, action: str) -> bool:
        if not self.accounts:
            self.log(f"No password configured; proceeding with: {action}")
            return True
        eligible = [a for a in self.accounts if a.get("enabled", True)]
        if not eligible:
            self._error("No enabled Engineer account can authorize this operation.")
            return False
        dialog = AdminAuthDialog(self.root, eligible, action, self.last_login)
        if dialog.authorized is None:
            self.log(f"Engineer authorization canceled/denied for: {action}", "WARN")
            return False
        engineer = dialog.authorized
        self.last_login = (engineer["project_name"], engineer["user_name"])
        self.log(f"Authorized by {engineer['project_name']} / {engineer['user_name']}: {action}", "OK")
        return True

    def _error(self, message: str) -> None:
        self.log(message.replace("\n", " | "), "ERROR")
        messagebox.showerror("TestPath Manager", message, parent=self.root)

    @staticmethod
    def _selected_id(tree: ttk.Treeview) -> str | None:
        selection = tree.selection()
        return tree.set(selection[0], "id") if selection else None

    @staticmethod
    def _set_entry(entry: ttk.Entry, value: str) -> None:
        old_state = str(entry.cget("state"))
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state=old_state)

    @staticmethod
    def _enable(button: ttk.Button, enabled: bool) -> None:
        button.configure(state="normal" if enabled else "disabled")

    def _populate_paths(self, selected_id: str | None = None) -> None:
        self.path_tree.delete(*self.path_tree.get_children())
        for row in self.paths:
            self.path_tree.insert("", "end", iid=row["id"],
                                  values=(row["id"], row["name"], row["path"], row["status"]))
        if selected_id and self.path_tree.exists(selected_id):
            self.path_tree.selection_set(selected_id)
            self.path_tree.see(selected_id)
        elif self.path_mode is None:
            self._show_path_selection()
        self._update_counts()

    def _show_path_selection(self) -> None:
        rid = self._selected_id(self.path_tree)
        row = next((p for p in self.paths if p["id"] == rid), None)
        self.path_id_var.set(row["id"] if row else "")
        self.path_name_var.set(row["name"] if row else "")
        self.path_value_var.set(row["path"] if row else "")
        self.path_status_var.set(row["status"] if row else "—")
        self._set_path_mode(None)

    def _on_path_select(self, _event: object = None) -> None:
        if self.path_mode is None:
            self._show_path_selection()

    def _set_path_mode(self, mode: str | None) -> None:
        self.path_mode = mode
        editing = mode is not None
        self.path_name_entry.configure(state="normal" if editing else "readonly")
        self.path_value_entry.configure(state="normal" if editing else "readonly")
        self._enable(self.path_file_btn, editing)
        self._enable(self.path_folder_btn, editing)
        self._enable(self.path_add_btn, not editing)
        self._enable(self.path_edit_btn, not editing and self._selected_id(self.path_tree) is not None)
        self._enable(self.path_delete_btn, not editing and self._selected_id(self.path_tree) is not None)
        self._enable(self.path_update_btn, editing)
        self._enable(self.path_cancel_btn, editing)
        self._enable(self.path_check_btn, not editing and self._selected_id(self.path_tree) is not None)
        self._enable(self.path_check_all_btn, not editing and bool(self.paths))

    def add_path(self) -> None:
        self.path_edit_id = None
        self.path_id_var.set(next_id(self.paths, "P"))
        self.path_name_var.set("")
        self.path_value_var.set("")
        self.path_status_var.set("—")
        self._set_path_mode("add")
        self.path_name_entry.focus_set()
        self.log("Started adding a Path record.")

    def edit_path(self) -> None:
        rid = self._selected_id(self.path_tree)
        if not rid:
            return
        self.path_edit_id = rid
        self._set_path_mode("edit")
        self.path_name_entry.focus_set()
        self.log(f"Editing Path {rid}.")

    def cancel_path(self) -> None:
        if self.path_mode:
            self.log("Canceled Path changes.")
        self.path_edit_id = None
        self._show_path_selection()

    def browse_file(self) -> None:
        if self.path_mode is None:
            return
        result = filedialog.askopenfilename(parent=self.root, title="Select a file")
        if result:
            self.path_value_var.set(result)
            self.check_entered_path()

    def browse_folder(self) -> None:
        if self.path_mode is None:
            return
        result = filedialog.askdirectory(parent=self.root, title="Select a folder", mustexist=True)
        if result:
            self.path_value_var.set(result)
            self.check_entered_path()

    def check_entered_path(self) -> None:
        path = self.path_value_var.get().strip()
        status = check_path(path)
        self.path_status_var.set(status)
        self.log(f"Check entered path: {status} — {path}", "OK" if status == "EXISTS" else "WARN")

    def save_path(self) -> None:
        if self.path_mode is None:
            return
        name = self.path_name_var.get().strip()
        path = self.path_value_var.get().strip()
        if not name or not path:
            messagebox.showwarning("Missing details", "Both Path name and Path are required.", parent=self.root)
            return
        if any(p["name"].casefold() == name.casefold() and p["id"] != self.path_edit_id for p in self.paths):
            messagebox.showwarning("Duplicate name", "A Path record already has that name.", parent=self.root)
            return
        rid = self.path_edit_id if self.path_mode == "edit" else next_id(self.paths, "P")
        action = f"{self.path_mode.upper()} Path {rid}: {name}"
        if not self._authorize(action):
            return
        if not messagebox.askyesno("Confirm update", f"Save changes to Path {rid} ({name})?", parent=self.root):
            self.log(f"Save canceled for Path {rid}.", "WARN")
            return
        previous = next((p for p in self.paths if p["id"] == rid), None)
        detected_type = classify_path(path)
        if detected_type == "unknown" and previous and previous["path"] == path:
            detected_type = previous["type"]
        row = {"id": rid, "name": name, "path": path,
               "type": detected_type, "status": check_path(path), "last_checked": checked_at()}
        updated = ([p for p in self.paths if p["id"] != rid] + [row]
                   if self.path_mode == "edit" else self.paths + [row])
        try:
            self.store.save_paths(updated)
        except StorageError as exc:
            self._error(str(exc))
            return
        self.paths = updated
        self.path_edit_id = None
        self._set_path_mode(None)
        self._populate_paths(selected_id=rid)
        self.log(f"Saved Path {rid}: {name} [{row['status']}]", "OK")

    def delete_path(self) -> None:
        rid = self._selected_id(self.path_tree)
        row = next((p for p in self.paths if p["id"] == rid), None)
        if not row:
            return
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete Path {rid} ({row['name']})?",
                                   icon="warning", parent=self.root):
            return
        if not self._authorize(f"DELETE Path {rid}: {row['name']}"):
            return
        updated = [p for p in self.paths if p["id"] != rid]
        try:
            self.store.save_paths(updated)
        except StorageError as exc:
            self._error(str(exc))
            return
        self.paths = updated
        self._populate_paths()
        self._show_path_selection()
        self.log(f"Deleted Path {rid}: {row['name']}", "WARN")

    def check_selected_path(self) -> None:
        rid = self._selected_id(self.path_tree)
        if rid:
            self._check_path_ids({rid})

    def check_all_paths(self) -> None:
        if self.paths:
            self._check_path_ids({row["id"] for row in self.paths})

    def _check_path_ids(self, ids: set[str]) -> None:
        selected = self._selected_id(self.path_tree)
        changed = 0
        updated = []
        for row in self.paths:
            item = row.copy()
            if item["id"] in ids:
                new_status = check_path(item["path"])
                if new_status != item["status"]:
                    changed += 1
                item["status"] = new_status
                item["last_checked"] = checked_at()
                detected_type = classify_path(item["path"])
                if detected_type != "unknown":
                    item["type"] = detected_type
                self.log(f"Path {item['id']} ({item['name']}): {new_status}",
                         "OK" if new_status == "EXISTS" else "WARN")
            updated.append(item)
        if ids:
            try:
                self.store.save_paths(updated)
            except StorageError as exc:
                self._error(str(exc))
                return
        self.paths = updated
        self._populate_paths(selected_id=selected)
        self.log(f"Validated {len(ids)} path(s). Status changes: {changed}.")

    def _populate_accounts(self, selected_id: str | None = None) -> None:
        self.account_tree.delete(*self.account_tree.get_children())
        for row in self.accounts:
            self.account_tree.insert("", "end", iid=row["id"],
                                     values=(row["id"], row["project_name"], row["user_name"], "********"))
        if selected_id and self.account_tree.exists(selected_id):
            self.account_tree.selection_set(selected_id)
            self.account_tree.see(selected_id)
        elif self.account_mode is None:
            self._show_account_selection()
        self._update_counts()

    def _show_account_selection(self) -> None:
        rid = self._selected_id(self.account_tree)
        row = next((a for a in self.accounts if a["id"] == rid), None)
        self.account_id_var.set(row["id"] if row else "")
        self.account_project_var.set(row["project_name"] if row else "")
        self.account_user_var.set(row["user_name"] if row else "")
        self.account_password_var.set("")
        self._set_account_mode(None)

    def _on_account_select(self, _event: object = None) -> None:
        if self.account_mode is None:
            self._show_account_selection()

    def _set_account_mode(self, mode: str | None) -> None:
        self.account_mode = mode
        editing = mode is not None
        for widget in (self.account_project_entry, self.account_user_entry, self.account_password_entry):
            widget.configure(state="normal" if editing else "readonly")
        selected = self._selected_id(self.account_tree) is not None
        self._enable(self.account_add_btn, not editing)
        self._enable(self.account_edit_btn, not editing and selected)
        self._enable(self.account_delete_btn, not editing and selected)
        self._enable(self.account_update_btn, editing)
        self._enable(self.account_cancel_btn, editing)

    def add_account(self) -> None:
        self.account_edit_id = None
        self.account_id_var.set(next_id(self.accounts, "A"))
        self.account_project_var.set("")
        self.account_user_var.set("")
        self.account_password_var.set("")
        self._set_account_mode("add")
        self.account_project_entry.focus_set()
        self.log("Started adding an Engineer account.")

    def edit_account(self) -> None:
        rid = self._selected_id(self.account_tree)
        if not rid:
            return
        self.account_edit_id = rid
        self.account_password_var.set("")
        self._set_account_mode("edit")
        self.account_project_entry.focus_set()
        self.log(f"Editing Engineer Account {rid}; authorization required to save.")

    def cancel_account(self) -> None:
        if self.account_mode:
            self.log("Canceled Engineer Account changes.")
        self.account_edit_id = None
        self._show_account_selection()

    def save_account(self) -> None:
        if self.account_mode is None:
            return
        project = self.account_project_var.get().strip()
        username = self.account_user_var.get().strip()
        password = self.account_password_var.get()
        if not username:
            messagebox.showwarning("Missing details", "Engineer username is required.", parent=self.root)
            return
        # Project is optional; a missing name is saved as DEFAULT.
        project = project or "DEFAULT"
        if any(a["project_name"].casefold() == project.casefold()
               and a["user_name"].casefold() == username.casefold()
               and a["id"] != self.account_edit_id for a in self.accounts):
            messagebox.showwarning("Duplicate account", "This username already exists in that project.",
                                   parent=self.root)
            return
        if (self.account_mode == "add" or password) and len(password) < MIN_PASSWORD_LENGTH:
            messagebox.showwarning("Weak password", f"Enter a password with at least {MIN_PASSWORD_LENGTH} characters.",
                                   parent=self.root)
            return
        rid = self.account_edit_id if self.account_mode == "edit" else next_id(self.accounts, "A")
        action = f"{self.account_mode.upper()} Engineer {rid}: {project} / {username}"
        if not self._authorize(action):
            return
        if not messagebox.askyesno("Confirm account update", f"Save Engineer Account {rid} ({username})?",
                                   parent=self.root):
            return
        old = next((a for a in self.accounts if a["id"] == rid), None)
        encoded = hash_password(password) if password else old["password_hash"]  # type: ignore[index]
        row = {"id": rid, "project_name": project, "user_name": username,
               "password_hash": encoded, "role": old["role"] if old else "engineer",
               "enabled": old["enabled"] if old else True}
        updated = ([a for a in self.accounts if a["id"] != rid] + [row]
                   if self.account_mode == "edit" else self.accounts + [row])
        try:
            self.store.save_accounts(updated)
        except StorageError as exc:
            self._error(str(exc))
            return
        self.accounts = updated
        self.account_edit_id = None
        self.account_password_var.set("")
        self._set_account_mode(None)
        self._populate_accounts(selected_id=rid)
        self.log(f"Saved Engineer Account {rid}: {project} / {username}.", "OK")
        if len(self.accounts) == 1:
            self.log("Engineer password protection is now ON.", "OK")

    def delete_account(self) -> None:
        rid = self._selected_id(self.account_tree)
        row = next((a for a in self.accounts if a["id"] == rid), None)
        if not row:
            return
        removing_last = len(self.accounts) == 1
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete Engineer Account {rid} ({row['user_name']})?",
                                   icon="warning", parent=self.root):
            return
        if not self._authorize(f"DELETE Engineer Account {rid}: {row['user_name']}"):
            return
        if removing_last and not messagebox.askyesno(
                "Turn off protection",
                "This is the last Engineer account. Deleting it will disable password protection. Continue?",
                icon="warning", parent=self.root):
            return
        updated = [a for a in self.accounts if a["id"] != rid]
        try:
            self.store.save_accounts(updated)
        except StorageError as exc:
            self._error(str(exc))
            return
        self.accounts = updated
        self._populate_accounts()
        self._show_account_selection()
        self.log(f"Deleted Engineer Account {rid}: {row['project_name']} / {row['user_name']}.", "WARN")
        if not self.accounts:
            self.log("Engineer password protection is now OFF.", "WARN")

    def refresh_all(self) -> None:
        if self.path_mode or self.account_mode:
            if not messagebox.askyesno("Discard edits", "Reloading JSON will discard unsaved edits. Continue?",
                                       parent=self.root):
                return
        try:
            paths = self.store.load_paths()
            accounts = self.store.load_accounts()
        except StorageError as exc:
            self._error(str(exc))
            return
        self.paths, self.accounts = paths, accounts
        self.path_edit_id = None
        self.account_edit_id = None
        self._set_path_mode(None)
        self._set_account_mode(None)
        self._populate_paths()
        self._populate_accounts()
        self.log("Reloaded paths.json and accounts.json.", "OK")
        if not self.accounts:
            self.log("No Engineer accounts loaded; protection is OFF.", "WARN")

    def _escape(self, _event: object = None) -> None:
        if self.path_mode:
            self.cancel_path()
        if self.account_mode:
            self.cancel_account()
