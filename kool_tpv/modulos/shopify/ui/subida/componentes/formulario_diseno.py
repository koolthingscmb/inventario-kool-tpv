"""Formulario DATOS DEL DISEÑO de la pantalla SUBIDA.

Título base, tags, beneficio, tono, sufijo SKU, estado, tipo de producto, variante TPV y la etiqueta
con las variantes que se van a subir. Solo construye los widgets: la lógica (cambio de tipo, generar
tags...) la aporta la pantalla mediante callbacks.
"""
import logging
import tkinter as tk
from typing import Any, Callable, Dict, List

import customtkinter as ctk

from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.modulos.shopify.services.producto_prompts import TONO_POR_DEFECTO

logger = logging.getLogger(__name__)


class FormularioDiseno:
    def __init__(self, parent, db, tipo_service, entries: Dict[str, Any], bg: str, primary: str, secondary: str,
                 on_tipo_change: Callable[[], None], on_variante_change: Callable[[], None],
                 on_generar_tags: Callable[[], None]):
        """entries: diccionario de campos de la pantalla; aquí se rellenan titulo, tags, beneficio,
        tono y codigo_categoria."""
        self._bg = bg
        self._entries = entries

        self.frame = tk.Frame(parent, bg=bg)
        form = self.frame
        form.pack(fill="x", padx=10)
        for c in range(4):
            form.columnconfigure(c, weight=1)

        self._field(form, "titulo", "TÍTULO BASE", "Camiseta X | Tema", 0, 0)

        # Tags con botón GENERAR
        cell_tags = tk.Frame(form, bg=self._bg)
        cell_tags.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tags, text="TAGS", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        tags_row = tk.Frame(cell_tags, bg=self._bg)
        tags_row.pack(fill="x")
        self._entries["tags"] = ctk.CTkEntry(tags_row, placeholder_text="anime, friki, regalo",
                                             height=34, font=("Helvetica", 12))
        self._entries["tags"].pack(side="left", fill="x", expand=True)
        self.btn_tags = ctk.CTkButton(tags_row, text="GENERAR", width=80, height=34,
                                      fg_color=secondary, font=("Helvetica", 10, "bold"),
                                      command=on_generar_tags)
        self.btn_tags.pack(side="left", padx=(6, 0))

        # Beneficio como SearchableCombo
        cell_ben = tk.Frame(form, bg=self._bg)
        cell_ben.grid(row=0, column=2, sticky="ew", padx=6, pady=4)
        tk.Label(cell_ben, text="BENEFICIO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")

        try:
            r_ben = db.fetch_all("SELECT texto FROM shopify_beneficios ORDER BY id")
            ben_opts = [r[0] for r in (r_ben or [])]
        except Exception:
            ben_opts = []

        self.ben_combo = SearchableCombo(cell_ben, values=ben_opts, placeholder="Elegir beneficio...",
                                         width=200, module_name='shopify')
        self.ben_combo.pack(fill="x")
        self._entries["beneficio"] = self.ben_combo

        # Tono como SearchableCombo (cargado de BD)
        cell_tono = tk.Frame(form, bg=self._bg)
        cell_tono.grid(row=0, column=3, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tono, text="TONO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")

        try:
            r_tonos = db.fetch_all("SELECT nombre FROM shopify_tonos ORDER BY nombre")
            tonos_opts = [r[0] for r in (r_tonos or [])]
        except Exception:
            tonos_opts = []

        self.tono_combo = SearchableCombo(cell_tono, values=tonos_opts, placeholder="Tono...",
                                          width=150, module_name='shopify')
        self.tono_combo.pack(fill="x")
        self.tono_combo.set(TONO_POR_DEFECTO)
        self._entries["tono"] = self.tono_combo

        self._field(form, "codigo_categoria", "SUFIJO SKU", "FRI (opcional)", 1, 0)

        cell_estado = tk.Frame(form, bg=self._bg)
        cell_estado.grid(row=1, column=1, sticky="w", padx=6, pady=4)
        tk.Label(cell_estado, text="ESTADO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        self.status_menu = ctk.CTkOptionMenu(cell_estado, values=["ACTIVE", "DRAFT"],
                                             width=160, height=34)
        self.status_menu.set("ACTIVE")
        self.status_menu.pack(anchor="w")

        # Tipo de producto: combo buscable con los tipos de la BD
        cell_tipo = tk.Frame(form, bg=self._bg)
        cell_tipo.grid(row=1, column=2, sticky="ew", padx=6, pady=4)
        tk.Label(cell_tipo, text="TIPO PRODUCTO", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        self.tipos: List[Dict[str, Any]]
        try:
            todos = tipo_service.get_all_tipos()
            self.tipos = [t for t in todos if t.get("activo") == 1 and t.get("web_activo") == 1]
        except Exception:
            self.tipos = []

        self.tipo_combo = SearchableCombo(
            cell_tipo,
            options=[(t["id"], t["nombre"]) for t in self.tipos],
            command=lambda _v: on_tipo_change(),
            placeholder="Escribe para buscar...",
            width=240, module_name='shopify')
        self.tipo_combo.pack(fill="x")

        # Variante TPV (se usa en modo EDITAR)
        cell_variante = tk.Frame(form, bg=self._bg)
        cell_variante.grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        tk.Label(cell_variante, text="VARIANTE TPV", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")

        self.variante_combo = SearchableCombo(
            cell_variante,
            options=[],
            command=lambda _v: on_variante_change(),
            placeholder="Selecciona variante...",
            width=240, module_name='shopify')
        self.variante_combo.pack(fill="x")

        # Variantes activas del tipo: se suben todas las que tengan sync_web = 1
        cell_vars = tk.Frame(form, bg=self._bg)
        cell_vars.grid(row=2, column=0, columnspan=4, sticky="ew", padx=6, pady=4)
        tk.Label(cell_vars, text="VARIANTES A SUBIR:", fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(side="left")
        self.variantes_lbl = tk.Label(cell_vars, text="", fg=primary, bg=self._bg,
                                      font=("Helvetica", 10, "bold"), anchor="w")
        self.variantes_lbl.pack(side="left", padx=(10, 0))

    def _field(self, parent, key, label, placeholder, row, col):
        cell = tk.Frame(parent, bg=self._bg)
        cell.grid(row=row, column=col, sticky="ew", padx=6, pady=4)
        tk.Label(cell, text=label, fg="#888", bg=self._bg,
                 font=("Helvetica", 9, "bold"), anchor="w").pack(anchor="w")
        e = ctk.CTkEntry(cell, placeholder_text=placeholder, height=34, font=("Helvetica", 12))
        e.pack(fill="x")
        self._entries[key] = e
