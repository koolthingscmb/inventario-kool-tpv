"""Pestaña EQUIVALENCIAS: edita `metacampos_alias.json` contra Shopify en vivo.

Cada valor oficial de los metacampos cómic tiene su fila con un campo de
palabras separadas por comas: son las variantes que traen las editoriales
("misterio, intriga, thriller" -> "Suspense"). Los valores se piden a
Shopify al abrir la pestaña (`MetacamposComicService.obtener_opciones`,
en un hilo) y se agrupan por metacampo — nada está escrito a mano.

Las equivalencias que apuntan a valores que ya no existen en Shopify se
muestran aparte, en el bloque "SIN EFECTO", y se conservan tal cual al
guardar (vaciar su casilla las borra).

La escritura real y la validación viven en
`ComparadorMetacamposService.guardar_alias` — la UI solo pinta filas.
"""
import logging
import threading
import tkinter as tk
from typing import Dict, List, Optional

import customtkinter as ctk

from kool_tpv.modulos.almacen.services.comparador_metacampos_service import (
    ComparadorMetacamposService,
)
from kool_tpv.modulos.almacen.services.metacampos_comic_service import (
    MetacamposComicService,
)
from kool_tpv.utils.widgets.notificaciones import show_error, show_success

logger = logging.getLogger(__name__)


class AliasTab:
    """Editor de equivalencias: valor oficial -> palabras de editorial."""

    _ANCHO_VALOR = 22

    def __init__(self, parent, db, primary_color, secondary_color,
                 bg_color, bg_medium):
        self.parent = parent
        self.db = db
        self._primary = primary_color
        self._secondary = secondary_color
        self._bg = bg_color
        self._bg_medium = bg_medium

        self._comparador = ComparadorMetacamposService(db)
        self._listas: Dict[str, Dict[str, str]] = {}
        self._rows: List[dict] = []          # {oficial, entry, frame}
        self._orphan_rows: List[dict] = []   # {valor, entry, frame}
        self._rows_frame: Optional[tk.Frame] = None
        self._status_lbl: Optional[tk.Label] = None
        self._scroll: Optional[ctk.CTkScrollableFrame] = None

    # ---------- render ----------

    def render(self):
        self._scroll = ctk.CTkScrollableFrame(self.parent,
                                            fg_color="transparent")
        self._scroll.pack(fill="both", expand=True)

        tk.Label(
            self._scroll,
            text="Palabras que traen las editoriales y su valor oficial en "
                 "los metacampos, separadas por comas. OBTENER las usa para "
                 "sugerirte demografía, género, temáticas y contenido.",
            font=("Helvetica", 11), fg="#AAAAAA", bg=self._bg,
            wraplength=800, justify="left", anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 10))

        self._status_lbl = tk.Label(
            self._scroll, text="Cargando valores de Shopify...",
            font=("Helvetica", 11, "italic"), fg="#888888", bg=self._bg,
            anchor="w")
        self._status_lbl.pack(fill="x", padx=10, pady=(0, 6))

        self._rows_frame = tk.Frame(self._scroll, bg=self._bg)
        self._rows_frame.pack(fill="x", padx=10, pady=(2, 10))

        threading.Thread(target=self._cargar_opciones,
                         daemon=True).start()

    def _cargar_opciones(self):
        """Hilo: pide las listas vivas de Shopify y vuelve a la UI."""
        try:
            opciones, err = MetacamposComicService(self.db).obtener_opciones()
        except Exception as e:
            logger.exception("Error cargando metacampos de Shopify")
            opciones, err = None, str(e)
        try:
            self.parent.after(0, lambda: self._on_opciones(opciones, err))
        except Exception:
            pass

    def _on_opciones(self, opciones, err):
        if not opciones:
            if self._status_lbl and self._status_lbl.winfo_exists():
                self._status_lbl.configure(
                    text=f"Sin valores de Shopify ({err or 'error'}). "
                         "No se puede editar hasta reconectar.",
                    fg="#e67e22")
            return

        self._listas = {
            clave: {
                MetacamposComicService.normalizar(e.get("nombre")):
                    e.get("nombre")
                for e in datos.get("entradas") or []
            }
            for clave, datos in opciones.items()
        }
        oficiales = {n for d in self._listas.values() for n in d.values()}

        # invertir el JSON: valor oficial -> [palabras]
        por_valor: Dict[str, List[str]] = {}
        huerfanas: Dict[str, List[str]] = {}
        for palabra, valor in self._comparador.listar_alias().items():
            oficial = self._oficial_de(valor)
            if oficial:
                por_valor.setdefault(oficial, []).append(palabra)
            else:
                huerfanas.setdefault(valor, []).append(palabra)

        self._pintar(opciones, por_valor, huerfanas, len(oficiales))

    def _oficial_de(self, valor: str) -> Optional[str]:
        norm = MetacamposComicService.normalizar(valor)
        for datos in self._listas.values():
            if norm in datos:
                return datos[norm]
        return None

    # ---------- pintado ----------

    def _pintar(self, opciones, por_valor, huerfanas, total):
        if self._status_lbl and self._status_lbl.winfo_exists():
            self._status_lbl.configure(
                text=f"{total} valores oficiales cargados de Shopify.",
                fg="#2ECC71")

        for clave, titulo, _unico in MetacamposComicService.GRUPOS:
            datos = opciones.get(clave) or {}
            entradas = sorted(
                (e.get("nombre") for e in datos.get("entradas") or [] if e.get("nombre")),
                key=str.lower)
            if not entradas:
                continue

            tk.Label(
                self._rows_frame, text=titulo,
                font=("Helvetica", 12, "bold"), fg=self._primary,
                bg=self._bg, anchor="w"
            ).pack(fill="x", pady=(12, 4), padx=2)

            rejilla = tk.Frame(self._rows_frame, bg=self._bg)
            rejilla.pack(fill="x")

            for i, nombre in enumerate(entradas):
                self._fila_valor(rejilla, nombre, por_valor.get(nombre, []),
                                 row=i // 2, col=i % 2)

        if huerfanas:
            tk.Label(
                self._rows_frame,
                text="⚠ SIN EFECTO — apuntan a valores que ya no existen en Shopify",
                font=("Helvetica", 12, "bold"), fg="#e67e22",
                bg=self._bg, anchor="w"
            ).pack(fill="x", pady=(16, 4), padx=2)

            rejilla = tk.Frame(self._rows_frame, bg=self._bg)
            rejilla.pack(fill="x")
            for i, (valor, palabras) in enumerate(sorted(huerfanas.items())):
                self._fila_valor(rejilla, valor, palabras,
                                 row=i // 2, col=i % 2, huerfana=True)

    def _fila_valor(self, parent, nombre, palabras, row, col, huerfana=False):
        frame = tk.Frame(parent, bg=self._bg)
        frame.grid(row=row, column=col, padx=4, pady=3, sticky="w")

        fg = "#e67e22" if huerfana else "#FFFFFF"
        tk.Label(frame, text=f"{nombre} ⚠" if huerfana else nombre,
                 font=("Helvetica", 11),
                 fg=fg, bg=self._bg, width=self._ANCHO_VALOR,
                 anchor="w").pack(side="left")

        entry = ctk.CTkEntry(
            frame, width=330, height=30, font=("Helvetica", 11),
            placeholder_text="palabras de la editorial, separadas por comas")
        if palabras:
            entry.insert(0, ", ".join(palabras))
        entry.pack(side="left")

        (self._orphan_rows if huerfana else self._rows).append(
            {'frame': frame, 'entry': entry,
             'oficial': None if huerfana else nombre,
             'valor': nombre if huerfana else None})

    # ---------- guardar ----------

    def save(self) -> bool:
        """Cosecha las filas y las valida/escribe vía el servicio."""
        filas: Dict[str, str] = {}
        for r in self._rows:
            if not r['frame'].winfo_exists():
                continue
            for palabra in r['entry'].get().split(','):
                palabra = palabra.strip()
                if palabra:
                    filas[palabra] = r['oficial']

        huerfanas: Dict[str, str] = {}
        for r in self._orphan_rows:
            if not r['frame'].winfo_exists():
                continue
            for palabra in r['entry'].get().split(','):
                palabra = palabra.strip()
                if palabra:
                    huerfanas[palabra] = r['valor']

        ok, errores = self._comparador.guardar_alias(
            filas, listas=self._listas or None, preservar=huerfanas)
        if ok:
            total = len(filas) + len(huerfanas)
            show_success(self.parent,
                         f"Equivalencias guardadas ({total} palabras).")
            return True
        show_error(self.parent,
                   "No se guardaron las equivalencias:\n- " +
                   "\n- ".join(errores[:8]))
        return False
