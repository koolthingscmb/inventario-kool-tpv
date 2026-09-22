import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class IATonosTab:
    """Gestiona la pestaña de Tonos de la IA."""

    def __init__(self, parent, db, primary_color, bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._primary_color = primary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        self._tonos_data = []
        self._tonos_entries = []

    def render(self):
        """Renderiza con scroll propio."""
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        try:
            rows = self.db.fetch_all("SELECT nombre FROM shopify_tonos ORDER BY nombre")
            self._tonos_data = [r[0] for r in (rows or [])]
        except Exception:
            self._tonos_data = []

        container = tk.Frame(scroll, bg=self._bg_color)
        container.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            container, text="+ AÑADIR TONO", width=150, height=32,
            fg_color=self._primary_color, font=("Helvetica", 12, "bold"),
            command=self._add_tono_ui
        ).pack(anchor="w", pady=(0, 20))

        self._tonos_grid = tk.Frame(container, bg=self._bg_color)
        self._tonos_grid.pack(fill="x")
        for i in range(6):
            self._tonos_grid.columnconfigure(i, weight=1)

        self._refresh_tonos_grid()

    def _refresh_tonos_grid(self):
        if not hasattr(self, '_tonos_grid'): return
        for child in self._tonos_grid.winfo_children():
            child.destroy()
        self._tonos_entries = []
        for i, tono in enumerate(self._tonos_data):
            row, col = i // 6, i % 6
            item_frame = tk.Frame(self._tonos_grid, bg=self._bg_medium, padx=5, pady=5)
            item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            entry = ctk.CTkEntry(item_frame, height=30, font=("Helvetica", 11))
            entry.insert(0, tono)
            entry.pack(side="left", fill="x", expand=True)
            self._tonos_entries.append(entry)
            btn_del = tk.Label(item_frame, text="✕", font=("Helvetica", 10), fg="#666", bg=self._bg_medium, cursor="hand2")
            btn_del.pack(side="right", padx=(5, 0))
            # Lambda robusta para evitar TypeError
            btn_del.bind("<Button-1>", lambda e, idx=i: self._remove_tono(idx))

    def _add_tono_ui(self):
        self._harvest_data()
        self._tonos_data.append("")
        self._refresh_tonos_grid()

    def _remove_tono(self, index):
        self._harvest_data()
        if 0 <= index < len(self._tonos_data):
            self._tonos_data.pop(index)
        self._refresh_tonos_grid()

    def _harvest_data(self):
        if self._tonos_entries:
            self._tonos_data = [e.get().strip() for e in self._tonos_entries]

    def save(self) -> bool:
        self._harvest_data()
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM shopify_tonos")
                for t in self._tonos_data:
                    if t: cur.execute("INSERT INTO shopify_tonos (nombre) VALUES (?)", (t,))
            return True
        except Exception:
            return False
