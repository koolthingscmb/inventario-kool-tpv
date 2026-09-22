import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class IABeneficiosTab:
    """Clase independiente para gestionar la pestaña de Beneficios de la IA."""

    def __init__(self, parent, db, primary_color, bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._primary_color = primary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium

        self._beneficios_data = []
        self._beneficios_entries = []
        self._beneficios_grid = None

    def render(self):
        """Renderiza la interfaz de la pestaña."""
        if not self._beneficios_data:
            try:
                rows = self.db.fetch_all("SELECT texto FROM shopify_beneficios ORDER BY id")
                self._beneficios_data = [r[0] for r in (rows or [])]
            except Exception:
                logger.exception("Error cargando beneficios desde la BD")
                self._beneficios_data = []

        container = tk.Frame(self.parent, bg=self._bg_color)
        container.pack(fill="x", padx=10, pady=10)

        btn_add = ctk.CTkButton(
            container, text="+ AÑADIR BENEFICIO", width=180, height=32,
            fg_color=self._primary_color, font=("Helvetica", 12, "bold"),
            command=self._add_beneficio_ui
        )
        btn_add.pack(anchor="w", pady=(0, 20))

        self._beneficios_grid = tk.Frame(container, bg=self._bg_color)
        self._beneficios_grid.pack(fill="x")

        # Grid de 2 columnas para beneficios (frases largas)
        self._beneficios_grid.columnconfigure(0, weight=1)
        self._beneficios_grid.columnconfigure(1, weight=1)

        self._refresh_beneficios_ui()

    def _refresh_beneficios_ui(self):
        if not self._beneficios_grid:
            return

        for child in self._beneficios_grid.winfo_children():
            child.destroy()
        self._beneficios_entries = []

        for i, texto in enumerate(self._beneficios_data):
            row = i // 2
            col = i % 2
            item_frame = tk.Frame(self._beneficios_grid, bg=self._bg_medium, padx=10, pady=10)
            item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

            entry = ctk.CTkEntry(item_frame, height=35, font=("Helvetica", 12))
            entry.insert(0, texto)
            entry.pack(side="left", fill="x", expand=True)
            self._beneficios_entries.append(entry)

            btn_del = tk.Label(item_frame, text="✕", font=("Helvetica", 12), fg="#666", bg=self._bg_medium, cursor="hand2")
            btn_del.pack(side="right", padx=(10, 0))
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
        """Recoge los datos actuales de los entries."""
        if self._beneficios_entries:
            self._beneficios_data = [e.get().strip() for e in self._beneficios_entries]

    def get_data(self) -> List[str]:
        """Devuelve las frases de beneficios actuales (limpias)."""
        self._harvest_data()
        return [b for b in self._beneficios_data if b]

    def save(self) -> bool:
        """Guarda los beneficios en la base de datos."""
        beneficios = self.get_data()
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM shopify_beneficios")
                for b in beneficios:
                    cur.execute("INSERT INTO shopify_beneficios (texto) VALUES (?)", (b,))
            return True
        except Exception:
            logger.exception("Error guardando beneficios en IABeneficiosTab")
            return False
