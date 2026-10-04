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
                 variante_id: Optional[int] = None, variante_nombre: str = "",
                 on_volver: Optional[Callable] = None,
                 on_aceptar: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.producto = producto or {}
        self.tipo_id = tipo_id
        self.tipo_nombre = tipo_nombre
        self.variante_id = variante_id
        self.variante_nombre = variante_nombre
        self.on_volver = on_volver
        self.on_aceptar = on_aceptar

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
        ctk.CTkButton(top, text="ACEPTAR CAMBIOS", width=160, height=34,
                      fg_color="#27ae60", # Verde aceptar
                      font=("Helvetica", 11, "bold"),
                      command=self._aceptar).pack(side="left", padx=10)
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
        for texto, w in (("ALMACÉN TPV", 24), ("STOCK", 8), ("ESTADO SHOPIFY", 20), ("SKU FINAL", 30)):
            tk.Label(cab, text=texto, fg="#888", bg=self._bg, width=w, anchor="w",
                     font=("Helvetica", 9, "bold")).pack(side="left", padx=8)

        # --- Filas de variantes (Scrollable) ---
        self._scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Frame interno para las filas (el que limpiaremos)
        self._filas_container = tk.Frame(self._scroll, bg=self._bg)
        self._filas_container.pack(fill="both", expand=True)

        # --- Acciones (Botones abajo, FUERA del scroll) ---
        acciones = tk.Frame(self.frame, bg=self._bg)
        acciones.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkButton(acciones, text="ACEPTAR Y PREPARAR ACTUALIZACIÓN", width=320, height=40,
                      fg_color="#27ae60", text_color="#FFF",
                      font=("Helvetica", 13, "bold"),
                      command=self._aceptar).pack(side="left")
        
        self._status_lbl = tk.Label(acciones, text="", fg="#888", bg=self._bg,
                                    font=("Helvetica", 11), anchor="w")
        self._status_lbl.pack(side="left", padx=10)

        # Cargamos los datos
        self._cargar_filas_tpv()

    def _cargar_filas_tpv(self):
        """Carga la lista principal basada en el stock del TPV para la variante elegida."""
        for child in self._filas_container.winfo_children():
            child.destroy()
        self._rows = []

        stock_tpv = self._stock_rows_tipo()
        variantes_shopify = (self.producto.get("variants") or {}).get("nodes") or []

        for row_tpv in stock_tpv:
            # Buscar si esta fila de TPV ya existe en Shopify por color/talla
            match_shopify = self._buscar_match_shopify(row_tpv, variantes_shopify)
            self._crear_fila_tpv(self._filas_container, row_tpv, match_shopify)

        if not stock_tpv:
            ctk.CTkLabel(self._filas_container, text="No hay stock configurado en el TPV para esta variante",
                         text_color="#888").pack(pady=20)

    def _buscar_match_shopify(self, row_tpv, variantes_shopify):
        """Busca una variante en Shopify que coincida con el color/talla del TPV."""
        nt = _norm(row_tpv.get("talla"))
        nc = _norm(row_tpv.get("color"))
        
        for vs in variantes_shopify:
            v_talla, v_color = self._extraer_opciones(vs, [row_tpv]) # Pasamos row_tpv para normalizar
            if _norm(v_talla) == nt and _norm(v_color) == nc:
                return vs
        return None

    def _crear_fila_tpv(self, parent, row_tpv, match_shopify):
        row = ctk.CTkFrame(parent, fg_color=self._bg_medium)
        row.pack(fill="x", pady=3)

        # 1. Info TPV (Color / Talla)
        info_tpv = f"{row_tpv.get('color', '-')} / {row_tpv.get('talla', '-')}"
        ctk.CTkLabel(row, text=info_tpv, width=210, anchor="w",
                     font=("Helvetica", 11, "bold"), text_color="#FFF").pack(side="left", padx=8)

        # 2. Stock TPV
        cant = row_tpv.get('cantidad', 0)
        ctk.CTkLabel(row, text=str(cant), width=60, anchor="center",
                     text_color="#7CFC90" if cant > 0 else "#e74c3c").pack(side="left", padx=8)

        # 3. Estado Shopify
        status_txt = "EN SHOPIFY" if match_shopify else "NUEVA (Por crear)"
        status_color = "#7CFC90" if match_shopify else "#e67e22"
        ctk.CTkLabel(row, text=status_txt, width=170, anchor="w",
                     font=("Helvetica", 10), text_color=status_color).pack(side="left", padx=8)

        # 4. Entry SKU
        entry = ctk.CTkEntry(row, width=320, height=32, placeholder_text="SKU")
        entry.pack(side="left", padx=8)
        
        # Sugerir el SKU del TPV si no tiene uno puesto
        sku_sugerido = row_tpv.get("sku") or ""
        if match_shopify and match_shopify.get("sku"):
            sku_sugerido = match_shopify["sku"]
        
        if sku_sugerido:
            entry.insert(0, sku_sugerido)

        self._rows.append({
            "tpv": row_tpv,
            "shopify": match_shopify,
            "entry": entry
        })


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
            # Usar el servicio de producto que ya tiene la lógica de flags y precios
            if self.variante_id:
                return self.service.get_variantes_stock(self.variante_id)
            
            # Fallback por tipo si no hay variante (comportamiento antiguo)
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
        """Rellena los entries con el SKU sugerido basado en el diseño y stock TPV."""
        ok = 0
        for r in self._rows:
            if solo_vacios and r["entry"].get().strip():
                continue
            
            # El SKU base viene del TPV
            sku_base = r["tpv"].get("sku") or ""
            if sku_base:
                r["entry"].delete(0, "end")
                r["entry"].insert(0, sku_base)
                ok += 1
        
        self._status(f"Generados {ok} SKUs base desde TPV")

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
                # Evitar doble guion si el SKU ya termina en guion
                if sku.endswith("-"):
                    new_sku = f"{sku}{extra}"
                else:
                    new_sku = f"{sku}-{extra}"
                
                r["entry"].delete(0, "end")
                r["entry"].insert(0, new_sku)
        self._diseno_sel = dis
        self._status(f"Diseño {dis.codigo} añadido a los SKUs")

    # ------------------------------------------------------------------
    # Salida: Aceptar y Volver
    # ------------------------------------------------------------------

    def _aceptar(self):
        """Prepara los datos y cierra la vista notificando al padre."""
        try:
            variantes_preparadas = []
            for r in self._rows:
                sku = r["entry"].get().strip()
                if not sku:
                    continue
                
                # Datos base de la variante para el motor de sincronización
                v_data = {
                    "sku": sku,
                    "color": r["tpv"].get("color"),
                    "talla": r["tpv"].get("talla"),
                    "cantidad": r["tpv"].get("cantidad", 0),
                    "precio_web": r["tpv"].get("precio_web"), # Centimos
                    "requiere_color": r["tpv"].get("requiere_color", 1),
                    "requiere_talla": r["tpv"].get("requiere_talla", 1)
                }
                
                # Regla de oro:
                # 1. Si NO está en Shopify y tiene Stock 0 -> NO la subimos/creamos.
                # 2. Si YA está en Shopify y tiene Stock 0 -> SÍ la subimos (para marcar como agotado).
                if not r["shopify"] and v_data["cantidad"] <= 0:
                    continue

                # Si ya existe en Shopify, heredar su precio si el TPV no tiene uno
                if r["shopify"] and not v_data["precio_web"]:
                    try:
                        v_data["precio"] = float(r["shopify"].get("price") or 0)
                        # El precio de Shopify ya lleva el recargo de tallas: no volver a sumarlo
                        v_data["precio_ya_final"] = True
                    except: pass
                    
                variantes_preparadas.append(v_data)

            # Notificar al padre con los datos preparados
            if self.on_aceptar:
                datos_regreso = {
                    "variantes": variantes_preparadas,
                    "diseno": self._diseno_sel,
                    "genero": self.variante_nombre
                }
                self.on_aceptar(datos_regreso)
            
            self._volver()
        except Exception:
            logging.exception("Error en _aceptar de SKUs")
            self._volver()

    def _volver(self):
        """Cierra la vista y restaura el padre."""
        try:
            self.frame.destroy()
        except Exception:
            pass
        if self.on_volver:
            self.on_volver()

    def _on_power(self):
        """Si pulsan el botón Power, cerramos guardando los cambios locales."""
        self._aceptar()
        return True

    def _status(self, texto):
        try:
            self._status_lbl.configure(text=texto)
        except Exception:
            pass
