"""Sección CONTENIDO (IA) de la pantalla SUBIDA.

Botón GENERAR CONTENIDO, título SEO, METACAMPOS, meta descripción SEO y las cajas BODY HTML
(una por variante). Solo dibuja: qué variantes se muestran y qué hacen los botones lo decide la pantalla.
"""
import tkinter as tk
from typing import Any, Callable, Dict, List

import customtkinter as ctk


class EditorContenidoIA:
    def __init__(self, parent, bg: str, bg_medium: str, primary: str, secondary: str,
                 on_generar: Callable[[], None], on_metafields: Callable[[], None]):
        self._bg = bg
        self._bg_medium = bg_medium
        self._primary = primary

        ia_row = tk.Frame(parent, bg=bg)
        ia_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(ia_row, text="GENERAR CONTENIDO", width=220, height=40,
                      fg_color=primary, text_color="#000",
                      font=("Helvetica", 13, "bold"),
                      command=on_generar).pack(side="left")

        tk.Label(ia_row, text="TÍTULO SEO:", fg="#888", bg=bg,
                 font=("Helvetica", 10, "bold")).pack(side="left", padx=(20, 10))
        self.seo_title_entry = ctk.CTkEntry(ia_row, placeholder_text="Título para Google...",
                                            height=34, font=("Helvetica", 12))
        self.seo_title_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_meta = ctk.CTkButton(
            ia_row, text="METACAMPOS", width=120, height=34,
            fg_color=secondary, text_color="#FFF",
            font=("Helvetica", 11, "bold"), command=on_metafields)
        self.btn_meta.pack(side="left", padx=(10, 0))

        self.meta_status_lbl = tk.Label(ia_row, text="", fg="#7CFC90", bg=bg,
                                        font=("Helvetica", 9, "bold"))
        self.meta_status_lbl.pack(side="left", padx=5)

        cont_grid = tk.Frame(parent, bg=bg)
        cont_grid.pack(fill="both", expand=True, padx=10)
        cont_grid.columnconfigure(0, weight=1)
        cont_grid.columnconfigure(1, weight=1)

        def _content_cell(row, col, titulo, height):
            cell = tk.Frame(cont_grid, bg=bg)
            cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            tk.Label(cell, text=titulo, fg="#888", bg=bg,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(anchor="w")
            box = ctk.CTkTextbox(cell, height=height, font=("Consolas", 11),
                                 fg_color=bg_medium, text_color="#e0e0e0",
                                 border_width=1, border_color=primary)
            box.pack(fill="both", expand=True)
            return box

        self.seo_box = _content_cell(0, 0, "META DESCRIPCIÓN SEO", 90)
        self.bodies_frame = tk.Frame(cont_grid, bg=bg)
        self.bodies_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=4, pady=4)

    def reconstruir_cajas(self, cajas_actuales: Dict[str, Any], nombres: List[str]) -> Dict[str, Any]:
        """Dibuja una caja BODY HTML por nombre (conserva el texto de las que ya existían).

        Devuelve el nuevo diccionario {nombre: caja}, en el orden de 'nombres'.
        """
        textos = {n: b.get("1.0", "end-1c") for n, b in cajas_actuales.items()}
        for child in self.bodies_frame.winfo_children():
            child.destroy()
        cajas: Dict[str, Any] = {}

        for i, nombre in enumerate(nombres):
            cell = tk.Frame(self.bodies_frame, bg=self._bg)
            cell.grid(row=i, column=0, sticky="ew", pady=(0, 6))
            self.bodies_frame.columnconfigure(0, weight=1)
            tk.Label(cell, text=f"BODY HTML — {nombre.upper()}", fg="#888", bg=self._bg,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(anchor="w")
            box = ctk.CTkTextbox(cell, height=90, font=("Consolas", 11),
                                 fg_color=self._bg_medium, text_color="#e0e0e0",
                                 border_width=1, border_color=self._primary)
            box.pack(fill="both", expand=True)
            cajas[nombre] = box
            if nombre in textos:
                box.insert("1.0", textos[nombre])
        return cajas
