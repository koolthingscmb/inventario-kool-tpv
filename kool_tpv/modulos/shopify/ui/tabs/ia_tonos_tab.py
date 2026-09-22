import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class IATonosTab:
    """Clase independiente para gestionar la pestaña de Tonos de la IA."""

    def __init__(self, parent, db, primary_color, bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._primary_color = primary_color
        self._bg_color = bg_color
        self._bg_medium = bg_medium

        self._tonos_data = []
        self._tonos_entries = []
        self._tonos_grid = None

    def render(self):
        """Renderiza la interfaz de la pestaña."""
        if not self._tonos_data:
            try:
                rows = self.db.fetch_all("SELECT nombre FROM shopify_tonos ORDER BY nombre")
                self._tonos_data = [r[0] for r in (rows or [])]
            except Exception:
                logger.exception("Error cargando tonos desde la BD")
                self._tonos_data = []

        container = tk.Frame(self.parent, bg=self._bg_color)
        container.pack(fill="x", padx=10, pady=10)

        btn_add = ctk.CTkButton(
            container, text="+ AÑADIR TONO", width=150, height=32,
            fg_color=self._primary_color, font=("Helvetica", 12, "bold"),
            command=self._add_tono_ui
        )
        btn_add.pack(anchor="w", pady=(0, 20))

        self._tonos_grid = tk.Frame(container, bg=self._bg_color)
        self._tonos_grid.pack(fill="x")

        for i in range(6):
            self._tonos_grid.columnconfigure(i, weight=1)

        self._refresh_tonos_grid()

    def _refresh_tonos_grid(self):
        if not self._tonos_grid:
            return

        for child in self._tonos_grid.winfo_children():
            child.destroy()
        self._tonos_entries = []

        for i, tono in enumerate(self._tonos_data):
            row = i // 6
            col = i % 6
            item_frame = tk.Frame(self._tonos_grid, bg=self._bg_medium, padx=5, pady=5)
            item_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

            entry = ctk.CTkEntry(item_frame, height=30, font=("Helvetica", 11))
            entry.insert(0, tono)
            entry.pack(side="left", fill="x", expand=True)
            self._tonos_entries.append(entry)

            btn_del = tk.Label(item_frame, text="✕", font=("Helvetica", 10), fg="#666", bg=self._bg_medium, cursor="hand2")
            btn_del.pack(side="right", padx=(5, 0))
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
        """Recoge los datos actuales de los entries."""
        if self._tonos_entries:
            self._tonos_data = [e.get().strip() for e in self._tonos_entries]

    def get_data(self) -> List[str]:
        """Devuelve los nombres de los tonos actuales (limpios)."""
        self._harvest_data()
        return [t for t in self._tonos_data if t]

    def save(self) -> bool:
        """Guarda los tonos en la base de datos."""
        tonos = self.get_data()
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM shopify_tonos")
                for t in tonos:
                    cur.execute("INSERT INTO shopify_tonos (nombre) VALUES (?)", (t,))
            return True
        except Exception:
            logger.exception("Error guardando tonos en IATonosTab")
            return False
