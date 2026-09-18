"""Subvista ACTUALIZA SKU: asigna SKUs a las variantes de un producto Shopify.

Flujo: cargar producto en SUBIDA (EDITAR) -> botón SKUS -> esta vista mapea
cada variante a una fila de stock base por talla/color -> se puede añadir el
sufijo+código del diseño -> GUARDAR sube los SKUs con productVariantsBulkUpdate.
"""
import logging
import re
import threading
import unicodedata
import tkinter as tk
from typing import Dict, Any, List, Optional, Callable

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.notificaciones import show_error, ToastWidget
from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from ..services.shopify_product_service import ShopifyProductService

logger = logging.getLogger(__name__)


def _norm(texto: str) -> str:
    """Normaliza un valor para comparar tallas/colores: '38/44' -> '38-44'."""
    if not texto:
        return ""
    s = str(texto).upper().strip().replace("/", "-")
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9-]", "", s)


class ShopifyActualizaSku:
    """Subvista para editar los SKUs de las variantes de un producto cargado.

    Ocupa el área central de la SUBIDA; `on_volver` se invoca al cerrar para
    restaurar el formulario de edición.
    """

    def __init__(self, parent, db, producto: Dict[str, Any],
                 tipo_id: Optional[int] = None, tipo_nombre: str = "",
                 on_volver: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.producto = producto or {}
        self.tipo_id = tipo_id
        self.tipo_nombre = tipo_nombre
        self.on_volver = on_volver

        self.service = ShopifyProductService(db)
        self.stock_service = ProduccionStockBaseService(db)
        self.disenos_repo = ProduccionDisenosRepository(db)
        self.sufijos_repo = ProduccionSufijosRepository(db)

        try:
            cfg = load_colors('shopify')
            self._primary = cfg.get('primary', '#00A4DF')
            self._secondary = cfg.get('secondary', '#3498db')
            self._bg = cfg.get('background', '#000000')
            self._bg_medium = cfg.get('bg_medium', '#1a1a1a')
        except Exception:
            self._primary, self._secondary = '#00A4DF', '#3498db'
            self._bg, self._bg_medium = '#000000', '#1a1a1a'

        self._rows: List[Dict[str, Any]] = []
        self._disenos: List[Any] = []
        self._diseno_sel = None

        self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
        self._build()

        # Mapeo inicial: solo rellena entries vacíos (los SKUs existentes se conservan)
        self.frame.after(100, lambda: self._generar_skus(solo_vacios=True))

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self):
        top = tk.Frame(self.frame, bg=self._bg)
        top.pack(fill="x", padx=20, pady=(15, 0))
        ctk.CTkButton(top, text="← VOLVER", width=110, height=34,
                      fg_color=self._secondary,
                      command=self._volver).pack(side="left")
        ctk.CTkLabel(top, text="ACTUALIZAR SKUS", font=("Helvetica", 18, "bold"),
                     text_color=self._primary).pack(side="left", padx=15)
        ctk.CTkLabel(top, text=self.producto.get("title", ""),
                     font=("Helvetica", 12), text_color="#FFF").pack(side="left", padx=10)

        # --- DISEÑO ---
        diseno_frame = ctk.CTkFrame(self.frame, fg_color=self._bg_medium)
        diseno_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(diseno_frame, text="DISEÑO:", font=("Helvetica", 11, "bold"),
                     text_color=self._primary).pack(side="left", padx=8)
        self._diseno_entry = ctk.CTkEntry(diseno_frame, width=200, height=34,
                                          placeholder_text="nombre del diseño...")
        self._diseno_entry.pack(side="left", padx=5, pady=8)
        ctk.CTkButton(diseno_frame, text="BUSCAR", width=80, height=34,
                      fg_color=self._secondary,
                      command=self._buscar_diseno).pack(side="left", padx=5)
        self._diseno_combo = ctk.CTkOptionMenu(diseno_frame, values=["—"], width=280, height=34)
        self._diseno_combo.pack(side="left", padx=5)
        ctk.CTkButton(diseno_frame, text="AÑADIR", width=80, height=34,
                      fg_color=self._primary, text_color="#000",
                      command=self._anadir_diseno).pack(side="left", padx=5)

        # --- Cabecera de filas ---
        cab = tk.Frame(self.frame, bg=self._bg)
        cab.pack(fill="x", padx=20, pady=(8, 0))
        for texto, w in (("VARIANTE SHOPIFY", 20), ("STOCK BASE", 22), ("SKU", 34)):
            tk.Label(cab, text=texto, fg="#888", bg=self._bg, width=w, anchor="w",
                     font=("Helvetica", 9, "bold")).pack(side="left", padx=8)

        # --- Filas de variantes ---
        scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=5)
        variantes = (self.producto.get("variants") or {}).get("nodes") or []
        for v in variantes:
            self._crear_fila(scroll, v)
        if not variantes:
            ctk.CTkLabel(scroll, text="El producto no tiene variantes",
                         text_color="#888").pack(pady=20)

        # --- Acciones ---
        acciones = tk.Frame(self.frame, bg=self._bg)
        acciones.pack(fill="x", padx=20, pady=(5, 15))
        ctk.CTkButton(acciones, text="GENERAR SKU", width=160, height=40,
                      fg_color=self._secondary, font=("Helvetica", 12, "bold"),
                      command=lambda: self._generar_skus(solo_vacios=False)).pack(side="left")
        ctk.CTkButton(acciones, text="GUARDAR EN SHOPIFY", width=220, height=40,
                      fg_color=self._primary, text_color="#000",
                      font=("Helvetica", 13, "bold"),
                      command=self._guardar).pack(side="left", padx=12)
        self._status_lbl = tk.Label(acciones, text="", fg="#888", bg=self._bg,
                                    font=("Helvetica", 11), anchor="w")
        self._status_lbl.pack(side="left", padx=10)

    def _crear_fila(self, parent, variante):
        row = ctk.CTkFrame(parent, fg_color=self._bg_medium)
        row.pack(fill="x", pady=3)

        opts = " / ".join(str(o.get("value", "")) for o in variante.get("selectedOptions", []))
        if not opts:
            opts = variante.get("title") or "—"
        ctk.CTkLabel(row, text=opts, width=190, anchor="w",
                     text_color="#FFF").pack(side="left", padx=8)

        match_lbl = ctk.CTkLabel(row, text="", width=200, anchor="w",
                                 text_color="#888", font=("Helvetica", 10))
        match_lbl.pack(side="left", padx=4)

        entry = ctk.CTkEntry(row, width=340, height=32, placeholder_text="SKU")
        entry.pack(side="left", padx=8)
        sku_actual = variante.get("sku") or ""
        if sku_actual:
            entry.insert(0, sku_actual)

        self._rows.append({"variante": variante, "entry": entry,
                           "match_lbl": match_lbl, "match": None})

    def _volver(self):
        try:
            self.frame.destroy()
        except Exception:
            pass
        if self.on_volver:
            self.on_volver()

    # ------------------------------------------------------------------
    # Mapeo variante Shopify -> stock base
    # ------------------------------------------------------------------

    def _stock_rows_tipo(self) -> List[Dict[str, Any]]:
        if not self.tipo_id:
            return []
        try:
            return [r for r in self.stock_service.listar_todo()
                    if r.get("tipo_id") == self.tipo_id]
        except Exception:
            logger.exception("Error cargando stock base")
            return []

    def _extraer_opciones(self, variante, stock_rows):
        """Extrae (talla, color) de las opciones de la variante Shopify."""
        tallas_stock = {_norm(r.get("talla")) for r in stock_rows if r.get("talla")}
        colores_stock = {_norm(r.get("color")) for r in stock_rows if r.get("color")}
        talla_val = color_val = None
        for o in variante.get("selectedOptions", []) or []:
            n = _norm(o.get("name"))
            nv = _norm(o.get("value"))
            if not nv:
                continue
            if n in ("TALLA", "SIZE", "TAMANO") or (talla_val is None and nv in tallas_stock):
                talla_val = o.get("value")
            elif n in ("COLOR", "COLOUR") or (color_val is None and nv in colores_stock):
                color_val = o.get("value")
        return talla_val, color_val

    def _buscar_base(self, talla_val, color_val, stock_rows):
        """Devuelve (fila_stock, motivo_error) para la variante."""
        nt, nc = _norm(talla_val), _norm(color_val)
        if not (nt or nc):
            return None, "SIN OPCIONES"
        cands = [r for r in stock_rows
                 if (not nc or _norm(r.get("color")) == nc)
                 and (not nt or _norm(r.get("talla")) == nt)]
        if len(cands) == 1:
            return cands[0], None
        if not cands:
            return None, "SIN COINCIDENCIA"
        return None, f"{len(cands)} COINCIDENCIAS"

    def _generar_skus(self, solo_vacios=False):
        """Rellena los entries con el SKU del stock base mapeado."""
        stock_rows = self._stock_rows_tipo()
        ok = 0
        for r in self._rows:
            if solo_vacios and r["entry"].get().strip():
                continue
            talla_val, color_val = self._extraer_opciones(r["variante"], stock_rows)
            base, motivo = self._buscar_base(talla_val, color_val, stock_rows)
            if base:
                r["entry"].delete(0, "end")
                r["entry"].insert(0, base["sku"])
                info = " ".join(p for p in (base.get("variante"), base.get("color"),
                                            base.get("talla")) if p)
                r["match_lbl"].configure(text=info, text_color="#7CFC90")
                r["match"] = base
                ok += 1
            else:
                r["match_lbl"].configure(text=motivo or "", text_color="#e67e22")
                r["match"] = None
        self._status(f"{ok}/{len(self._rows)} variantes mapeadas")

    # ------------------------------------------------------------------
    # Diseño: sufijo + código
    # ------------------------------------------------------------------

    def _buscar_diseno(self):
        filtro = self._diseno_entry.get().strip()
        if not filtro:
            return
        try:
            self._disenos = self.disenos_repo.buscar(filtro)
        except Exception:
            logger.exception("Error buscando diseños")
            self._disenos = []
        if not self._disenos:
            self._diseno_combo.configure(values=["Sin resultados"])
            self._diseno_combo.set("Sin resultados")
            return
        valores = [f"{d.codigo} — {d.nombre}" for d in self._disenos]
        self._diseno_combo.configure(values=valores)
        self._diseno_combo.set(valores[0])

    def _anadir_diseno(self):
        sel = self._diseno_combo.get()
        dis = next((d for d in self._disenos
                    if f"{d.codigo} — {d.nombre}" == sel), None)
        if not dis:
            show_error(self.frame, "Busca y selecciona un diseño primero")
            return
        suf = ""
        if dis.sufijo_id:
            s = self.sufijos_repo.get_por_id(dis.sufijo_id)
            if s:
                suf = s.nombre
        extra = "-".join(p for p in (_norm(suf), _norm(dis.codigo)) if p)
        if not extra:
            return
        for r in self._rows:
            sku = r["entry"].get().strip()
            if sku and not sku.upper().endswith(extra):
                r["entry"].delete(0, "end")
                r["entry"].insert(0, f"{sku}-{extra}")
        self._diseno_sel = dis
        self._status(f"Diseño {dis.codigo} añadido a los SKUs")

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------

    def _guardar(self):
        variantes = [{"id": r["variante"].get("id"), "sku": r["entry"].get().strip()}
                     for r in self._rows
                     if r["variante"].get("id") and r["entry"].get().strip()]
        if not variantes:
            show_error(self.frame, "No hay SKUs que guardar")
            return
        self._status("Subiendo SKUs a Shopify...")

        def work():
            res = self.service.actualizar_skus(self.producto.get("id"), variantes)

            def done():
                if res.get("success"):
                    mapa = {v["id"]: v["sku"] for v in variantes}
                    for v in (self.producto.get("variants") or {}).get("nodes") or []:
                        if v.get("id") in mapa:
                            v["sku"] = mapa[v["id"]]
                    self._guardar_mapping()
                    ToastWidget.show(self.frame, "SKUs actualizados en Shopify",
                                     tipo="success")
                    self.frame.after(800, self._volver)
                else:
                    self._status(f"Error: {res.get('message')}")
            self.frame.after(0, done)
        threading.Thread(target=work, daemon=True).start()

    def _guardar_mapping(self):
        """Guarda el enlace diseño -> producto Shopify para futuras sincronizaciones."""
        if not self._diseno_sel:
            return
        try:
            self.service.repo.upsert_diseno_mapping(
                self._diseno_sel.codigo, self.tipo_nombre or "",
                self.producto.get("id"), self.producto.get("handle"))
        except Exception:
            logger.exception("Error guardando mapeo diseño-producto")

    def _status(self, texto):
        try:
            self._status_lbl.configure(text=texto)
        except Exception:
            pass
