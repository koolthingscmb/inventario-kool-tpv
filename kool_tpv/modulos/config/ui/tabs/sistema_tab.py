"""Tab SISTEMA del panel de configuración UI — Gestión de backups."""
import tkinter as tk
import tkinter.messagebox as messagebox
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import customtkinter as ctk

from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService
from kool_tpv.modulos.config.ui.config_tab_helper import section_title


class SistemaTab:
    """Gestión de backups de archivos JSON de configuración UI."""

    def __init__(self, parent, service: UIConfigService):
        self.parent = parent
        self.service = service
        self._bg = "#2c3e50"
        self._fg = "#ecf0f1"
        self._values: Dict[str, tk.StringVar] = {}
        self._selected_file = tk.StringVar()
        self._selected_backup = tk.StringVar()
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True)

        section_title(scroll, "Sistema — Backups de configuración", self._bg).pack(
            fill="x", pady=(10, 5), padx=10
        )

        self._render_file_selector(scroll)
        self._separator(scroll)
        self._render_backup_actions(scroll)
        self._separator(scroll)
        self._render_backup_list(scroll)
        self._separator(scroll)
        self._render_reset_section(scroll)
        self._separator(scroll)
        self._render_logs_section(scroll)

    # ── SELECTOR DE ARCHIVO ──────────────────────────────────────

    def _render_file_selector(self, parent):
        self._section_header(parent, "ARCHIVO DE CONFIGURACIÓN", "#3498db")

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        tk.Label(
            row, text="Archivo:", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        ).pack(side="left", padx=(0, 6))

        json_files = self.service.listar_json_disponibles()
        if json_files:
            self._selected_file.set(json_files[0])
        ctk.CTkOptionMenu(
            row, variable=self._selected_file,
            values=json_files, width=200,
            command=lambda _: self._refresh_backups()
        ).pack(side="left")

    # ── ACCIONES DE BACKUP ───────────────────────────────────────

    def _render_backup_actions(self, parent):
        self._section_header(parent, "ACCIONES", "#2ecc71")

        row = tk.Frame(parent, bg=self._bg)
        row.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(
            row, text="CREAR BACKUP", width=130, height=32,
            fg_color="#2ecc71", hover_color="#27ae60",
            font=("Helvetica", 10, "bold"),
            command=self._crear_backup
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row, text="RESTAURAR SELECCIONADO", width=180, height=32,
            fg_color="#e67e22", hover_color="#d35400",
            font=("Helvetica", 10, "bold"),
            command=self._restaurar_backup
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row, text="ELIMINAR SELECCIONADO", width=170, height=32,
            fg_color="#e74c3c", hover_color="#c0392b",
            font=("Helvetica", 10, "bold"),
            command=self._eliminar_backup
        ).pack(side="left")

        self._status_label = tk.Label(
            parent, text="", font=("Helvetica", 10),
            fg=self._fg, bg=self._bg, anchor="w"
        )
        self._status_label.pack(fill="x", padx=10, pady=(4, 0))

    # ── LISTA DE BACKUPS ─────────────────────────────────────────

    def _render_backup_list(self, parent):
        self._section_header(parent, "BACKUPS DISPONIBLES", "#9b59b6")

        list_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        list_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self._backup_listbox = tk.Listbox(
            list_frame, bg="#1a1a1a", fg="#e0e0e0",
            selectbackground="#9b59b6", selectforeground="#ffffff",
            font=("Courier", 10), height=12,
            activestyle="none", highlightthickness=0, bd=0
        )
        self._backup_listbox.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                 command=self._backup_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._backup_listbox.configure(yscrollcommand=scrollbar.set)

        self._backup_listbox.bind("<<ListboxSelect>>", self._on_backup_select)

        self._refresh_backups()

    # ── RESET ────────────────────────────────────────────────────

    def _render_reset_section(self, parent):
        self._section_header(parent, "RESET — RESTAURAR VALORES POR DEFECTO", "#e74c3c")

        warn = tk.Label(
            parent,
            text="⚠ Esto restaurará TODOS los archivos JSON de configuración\n"
                 "a su backup más antiguo (estado original).\n"
                 "Se creará un backup de seguridad antes de resetear.",
            font=("Helvetica", 10), fg="#e74c3c", bg=self._bg,
            anchor="w", justify="left"
        )
        warn.pack(fill="x", padx=10, pady=4)

        ctk.CTkButton(
            parent, text="RESTAURAR VALORES POR DEFECTO", width=250, height=36,
            fg_color="#e74c3c", hover_color="#c0392b",
            font=("Helvetica", 11, "bold"),
            command=self._reset_defaults
        ).pack(padx=10, pady=(4, 8), anchor="w")

    def _reset_defaults(self):
        archivo = self._selected_file.get()
        if not archivo:
            self._status_label.configure(text="⚠ Selecciona un archivo", fg="#e74c3c")
            return

        confirm1 = messagebox.askyesno(
            "Confirmar Reset",
            f"¿Restaurar '{archivo}' a su backup más antiguo?\n"
            "Se creará un backup de seguridad antes de resetear.",
            icon="warning",
            parent=self.parent
        )
        if not confirm1:
            self._status_label.configure(text="Reset cancelado", fg="#95a5a6")
            return

        confirm2 = messagebox.askyesno(
            "Última confirmación",
            f"¿Estás SEGURO?\n"
            "Los cambios actuales de '{archivo}' se perderán\n"
            "y se restaurará el estado original.",
            icon="warning",
            parent=self.parent
        )
        if not confirm2:
            self._status_label.configure(text="Reset cancelado", fg="#95a5a6")
            return

        backups = self.service.listar_backups(archivo)
        if not backups:
            self._status_label.configure(text="✗ No hay backups disponibles para reset", fg="#e74c3c")
            return

        oldest = backups[-1]
        ok = self.service.restaurar_backup(archivo, str(oldest))
        if ok:
            self._status_label.configure(
                text=f"✓ Reset completado desde: {oldest.name}", fg="#2ecc71"
            )
            self._refresh_backups()
        else:
            self._status_label.configure(text="✗ Error al restaurar", fg="#e74c3c")

    # ── LÓGICA ───────────────────────────────────────────────────

    def _refresh_backups(self):
        if not hasattr(self, "_backup_listbox"):
            return
        self._backup_listbox.delete(0, tk.END)
        self._selected_backup.set("")

        archivo = self._selected_file.get()
        if not archivo:
            return

        backups = self.service.listar_backups(archivo)
        if not backups:
            self._backup_listbox.insert(tk.END, "  (sin backups)")
            return

        for bp in backups:
            stat = bp.stat()
            size_kb = stat.st_size / 1024
            mtime = datetime.fromtimestamp(stat.st_mtime)
            ts = mtime.strftime("%Y-%m-%d %H:%M:%S")
            label = f"  {ts}  |  {size_kb:7.1f} KB  |  {bp.name}"
            self._backup_listbox.insert(tk.END, label)

    def _on_backup_select(self, event):
        sel = self._backup_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        archivo = self._selected_file.get()
        backups = self.service.listar_backups(archivo)
        if idx < len(backups):
            self._selected_backup.set(str(backups[idx]))

    def _crear_backup(self):
        archivo = self._selected_file.get()
        if not archivo:
            self._status_label.configure(text="⚠ Selecciona un archivo", fg="#e74c3c")
            return
        bp = self.service.crear_backup(archivo)
        if bp:
            self._status_label.configure(text=f"✓ Backup creado: {bp.name}", fg="#2ecc71")
            self._refresh_backups()
        else:
            self._status_label.configure(text="✗ Error al crear backup", fg="#e74c3c")

    def _restaurar_backup(self):
        archivo = self._selected_file.get()
        if not archivo:
            self._status_label.configure(text="⚠ Selecciona un archivo", fg="#e74c3c")
            return
        bp_path = self._selected_backup.get()
        if not bp_path:
            self._status_label.configure(text="⚠ Selecciona un backup de la lista", fg="#e74c3c")
            return
        ok = self.service.restaurar_backup(archivo, bp_path)
        if ok:
            self._status_label.configure(text=f"✓ Restaurado desde backup", fg="#2ecc71")
            self._refresh_backups()
        else:
            self._status_label.configure(text="✗ Error al restaurar", fg="#e74c3c")

    def _eliminar_backup(self):
        bp_path = self._selected_backup.get()
        if not bp_path:
            self._status_label.configure(text="⚠ Selecciona un backup de la lista", fg="#e74c3c")
            return
        from pathlib import Path
        p = Path(bp_path)
        if p.exists():
            p.unlink()
            self._status_label.configure(text=f"✓ Backup eliminado", fg="#2ecc71")
            self._refresh_backups()
        else:
            self._status_label.configure(text="✗ Backup no encontrado", fg="#e74c3c")

    # ── HELPERS ──────────────────────────────────────────────────

    def _render_logs_section(self, parent):
        self._section_header(parent, "LOGS — ÚLTIMOS CAMBIOS", "#f39c12")

        log_frame = tk.Frame(parent, bg="#1a1a1a", relief="solid", bd=1)
        log_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self._log_listbox = tk.Listbox(
            log_frame, bg="#1a1a1a", fg="#e0e0e0",
            selectbackground="#f39c12", selectforeground="#000000",
            font=("Courier", 9), height=10,
            activestyle="none", highlightthickness=0, bd=0
        )
        self._log_listbox.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(log_frame, orient="vertical",
                                 command=self._log_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._log_listbox.configure(yscrollcommand=scrollbar.set)

        self._refresh_logs()

    def _refresh_logs(self):
        if not hasattr(self, "_log_listbox"):
            return
        self._log_listbox.delete(0, tk.END)

        backup_dir = self.service.backup_dir
        if not backup_dir.exists():
            self._log_listbox.insert(tk.END, "  (sin logs)")
            return

        entries = []
        for p in backup_dir.iterdir():
            if not p.is_file() or not p.name.endswith(".backup"):
                continue
            parts = p.stem.rsplit("_", 2)
            if len(parts) < 3:
                continue
            file_name = parts[0]
            ts_str = f"{parts[1]}_{parts[2]}"
            try:
                ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            except ValueError:
                continue
            size_kb = p.stat().st_size / 1024
            entries.append((ts, file_name, size_kb, p.name))

        entries.sort(key=lambda e: e[0], reverse=True)

        if not entries:
            self._log_listbox.insert(tk.END, "  (sin cambios registrados)")
            return

        max_show = 50
        for ts, file_name, size_kb, name in entries[:max_show]:
            time_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            self._log_listbox.insert(
                tk.END,
                f"  {time_str}  |  {file_name:30s}  |  {size_kb:7.1f} KB"
            )

        if len(entries) > max_show:
            self._log_listbox.insert(tk.END, f"  ... y {len(entries) - max_show} más")

    # ── HELPERS ──────────────────────────────────────────────────

    def _section_header(self, parent, label: str, accent: str):
        tk.Label(
            parent, text=f"  [{label}]",
            font=("Helvetica", 11, "bold"),
            fg=accent, bg=self._bg, anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

    def _separator(self, parent):
        tk.Frame(parent, bg="#555555", height=2).pack(fill="x", padx=10, pady=10)
