import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class IABeneficiosTab:
    """Gestiona la pestaña de Beneficios de la IA."""

    def __init__(self, parent, db, primary_color, bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._primary_color = primary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium
        self._beneficios_data = []
        self._beneficios_entries = []

    def render(self):
        """Renderiza con scroll propio."""
        scroll = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        try:
            rows = self.db.fetch_all("SELECT texto FROM shopify_beneficios ORDER BY id")
            self._beneficios_data = [r[0] for r in (rows or [])]
        except Exception:
            self._beneficios_data = []

        container = tk.Frame(scroll, bg=self._bg_color)
        container.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            container, text="+ AÑADIR BENEFICIO", width=180, height=32,
            fg_color=self._primary_color, font=("Helvetica", 12, "bold"),
            command=self._add_beneficio_ui
        ).pack(anchor="w", pady=(0, 20))

        self._beneficios_grid = tk.Frame(container, bg=self._bg_color)
        self._beneficios_grid.pack(fill="x")
        self._beneficios_grid.columnconfigure(0, weight=1)
        self._beneficios_grid.columnconfigure(1, weight=1)
        self._refresh_beneficios_ui()

    def _refresh_beneficios_ui(self):
        if not hasattr(self, '_beneficios_grid'): return
        for child in self._beneficios_grid.winfo_children():
            child.destroy()
        self._beneficios_entries = []
        for i, texto in enumerate(self._beneficios_data):
            row, col = i // 2, i % 2
            item_frame = tk.Frame(self._beneficios_grid, bg=self._bg_medium, padx=10, pady=10)
            item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            entry = ctk.CTkEntry(item_frame, height=35, font=("Helvetica", 12))
            entry.insert(0, texto)
            entry.pack(side="left", fill="x", expand=True)
            self._beneficios_entries.append(entry)
            btn_del = tk.Label(item_frame, text="✕", font=("Helvetica", 12), fg="#666", bg=self._bg_medium, cursor="hand2")
            btn_del.pack(side="right", padx=(10, 0))
            # Lambda robusta para evitar TypeError
            btn_del.bind("<Button-1>", lambda e, idx=i: self._remove_beneficio(idx))

    def _add_beneficio_ui(self):
        self._harvest_data()
        self._beneficios_data.append("")
        self._refresh_beneficios_ui()

    def _remove_beneficio(self, index):
        self._harvest_data()
        if 0 <= index < len(self._beneficios_data):
            self._beneficios_data.pop(index)
        self._refresh_beneficios_ui()

    def _harvest_data(self):
        if self._beneficios_entries:
            self._beneficios_data = [e.get().strip() for e in self._beneficios_entries]

    def save(self) -> bool:
        self._harvest_data()
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM shopify_beneficios")
                for b in self._beneficios_data:
                    if b: cur.execute("INSERT INTO shopify_beneficios (texto) VALUES (?)", (b,))
            return True
        except Exception:
            return False
