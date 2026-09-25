"""Subvista METACAMPOS: edita los metacampos de un producto Shopify.

Flujo: cargar producto en SUBIDA (EDITAR) -> botón METACAMPOS -> esta vista lista
todos los metacampos del producto -> permite editar valores -> GUARDAR sube
los cambios con metafieldsSet.
"""
import logging
import threading
import tkinter as tk
from typing import Dict, Any, List, Optional, Callable

import customtkinter as ctk

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.widgets.notificaciones import show_error, ToastWidget
from ..services.shopify_product_service import ShopifyProductService

logger = logging.getLogger(__name__)

class ShopifyMetafieldsUI:
    """Subvista para editar los metacampos de un producto cargado."""

    def __init__(self, parent, db, producto: Dict[str, Any], on_volver: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.producto = producto or {}
        self.on_volver = on_volver

        self.service = ShopifyProductService(db)

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

        self.frame = ctk.CTkFrame(parent, fg_color=self._bg)
        self._build()

    def _build(self):
        top = tk.Frame(self.frame, bg=self._bg)
        top.pack(fill="x", padx=20, pady=(15, 0))
        
        ctk.CTkButton(top, text="← VOLVER", width=110, height=34,
                      fg_color=self._secondary,
                      command=self._volver).pack(side="left")
        
        ctk.CTkLabel(top, text="EDITAR METACAMPOS", font=("Helvetica", 18, "bold"),
                     text_color=self._primary).pack(side="left", padx=15)
        
        ctk.CTkLabel(top, text=self.producto.get("title", ""),
                     font=("Helvetica", 12), text_color="#FFF").pack(side="left", padx=10)

        # --- Cabecera de tabla (Doble columna: 6 columnas en total) ---
        cab = tk.Frame(self.frame, bg=self._bg)
        cab.pack(fill="x", padx=20, pady=(15, 0))
        
        # Ajuste de proporciones solicitado:
        # Namespace (-50%), Clave (-30%), Valor (+ resto)
        # Ratio aproximado: 0.5 : 0.7 : 3.0
        weights = [5, 7, 30, 5, 7, 30] 
        for i, w in enumerate(weights):
            cab.columnconfigure(i, weight=w)

        headers = ["NAMESPACE", "CLAVE", "VALOR / REFERENCIA"]
        for bloque in range(2): 
            for i, texto in enumerate(headers):
                col = (bloque * 3) + i
                lbl = tk.Label(cab, text=texto, fg="#888", bg=self._bg, anchor="w",
                               font=("Helvetica", 9, "bold"))
                lbl.grid(row=0, column=col, sticky="ew", padx=10, pady=5)

        # Separador visual bajo cabecera
        linea = tk.Frame(self.frame, bg=self._primary, height=1)
        linea.pack(fill="x", padx=20, pady=(0, 5))

        # --- Lista de metacampos ---
        scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=0)
        
        for i, w in enumerate(weights):
            scroll.columnconfigure(i, weight=w)

        nodes = (self.producto.get("metafields") or {}).get("nodes") or []
        # Filtrar SOLO namespace 'custom' para evitar description_tag y otros campos de sistema
        metafields = [m for m in nodes if m.get("namespace") == "custom"]
        
        for idx, mf in enumerate(metafields):
            fila = idx // 2
            col_base = (idx % 2) * 3
            self._crear_bloque_metacampo(scroll, mf, fila, col_base)
            
        if not metafields:
            msg = "Sin metacampos editables (custom/global)"
            ctk.CTkLabel(scroll, text=msg,
                         text_color="#666", font=("Helvetica", 12, "italic")).pack(pady=40)

        # --- Acciones ---
        acciones = tk.Frame(self.frame, bg=self._bg)
        acciones.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkButton(acciones, text="GUARDAR EN SHOPIFY", width=240, height=45,
                      fg_color=self._primary, text_color="#000",
                      font=("Helvetica", 14, "bold"),
                      command=self._guardar).pack(side="left")
        
        self._status_lbl = tk.Label(acciones, text="", fg="#888", bg=self._bg,
                                    font=("Helvetica", 11), anchor="w")
        self._status_lbl.pack(side="left", padx=15)

    def _crear_bloque_metacampo(self, parent, mf, fila, col_base):
        # Todo sobre el fondo negro principal (self._bg)
        bg_main = self._bg
        
        # Namespace (reducido -50%)
        lbl_ns = tk.Label(parent, text=mf.get("namespace", ""), anchor="w",
                          fg="#888", bg=bg_main, font=("Consolas", 10))
        lbl_ns.grid(row=fila, column=col_base, sticky="nsew", padx=(10, 2), pady=6)
        
        # Key (reducido -30%)
        lbl_key = tk.Label(parent, text=mf.get("key", ""), anchor="w",
                           fg="#FFF", bg=bg_main, font=("Consolas", 11, "bold"))
        lbl_key.grid(row=fila, column=col_base + 1, sticky="nsew", padx=2, pady=6)

        # Valor / Widget
        val_frame = tk.Frame(parent, bg=bg_main)
        val_frame.grid(row=fila, column=col_base + 2, sticky="nsew", padx=(2, 15), pady=2)

        val = mf.get("value", "")
        mf_type = mf.get("type", "string")
        mf_key = mf.get("key", "")
        is_ref = mf.get("reference") is not None
        
        widget = None
        var = None

        if mf_type == 'boolean':
            var = tk.BooleanVar(value=(str(val).lower() == 'true'))
            widget = ctk.CTkCheckBox(
                val_frame, text="", variable=var,
                fg_color=self._primary, hover_color=self._secondary,
                width=20
            )
            widget.pack(side="left", padx=5, pady=4)
        elif mf_type in ('rich_text_field', 'multi_line_text_field') or mf_key == 'componentes':
            # Widget de texto multilínea con altura dinámica elástica
            widget = ctk.CTkTextbox(val_frame, height=60, font=("Helvetica", 11),
                                   fg_color=self._bg_medium, border_width=1,
                                   wrap="word")
            widget.pack(fill="x", expand=True, padx=5, pady=5)
            widget.insert("1.0", val)
            
            # Ajuste inicial y vinculación a eventos para que crezca al escribir o redimensionar
            self.frame.after(10, lambda w=widget: self._ajustar_altura_textbox(w))
            widget.bind("<KeyRelease>", lambda e, w=widget: self._ajustar_altura_textbox(w))
        else:
            widget = ctk.CTkEntry(val_frame, height=34, font=("Helvetica", 12),
                                 fg_color=self._bg_medium, border_width=1)
            widget.pack(fill="x", expand=True, padx=5, pady=4)
            widget.insert(0, val)
        
        if is_ref:
            ref_url = mf["reference"].get("image", {}).get("url", "")
            if ref_url:
                lbl_ref = tk.Label(val_frame, text=f"URL: {ref_url[:35]}...", 
                                   fg=self._primary, bg=bg_main, font=("Helvetica", 7))
                lbl_ref.pack(anchor="w", padx=5)

        self._rows.append({
            "metafield": mf,
            "widget": widget,
            "var": var,
            "type": mf_type
        })

    def _volver(self):
        try:
            self.frame.destroy()
        except Exception:
            pass
        if self.on_volver:
            self.on_volver()

    def _ajustar_altura_textbox(self, widget):
        """Ajusta la altura del CTKTextbox según las líneas visuales reales de texto."""
        try:
            # Acceder al widget tk.Text interno de CustomTkinter
            tk_text = widget._textbox
            # Contar líneas reales renderizadas (teniendo en cuenta el wrap)
            # 'count -displaylines' es la forma oficial de tk para esto
            res = tk_text.tk.call(tk_text._w, "count", "-displaylines", "1.0", "end")
            num_lineas = int(res) if res else 1
            
            # Calcular píxeles (aprox 18px por línea para fuente 11)
            # Mínimo 2 líneas (40px), máximo 250px
            nueva_altura = min(max(num_lineas * 20, 60), 250)
            
            # Solo actualizar si hay un cambio significativo para evitar parpadeos
            if abs(widget.cget("height") - nueva_altura) > 5:
                widget.configure(height=nueva_altura)
        except Exception:
            pass

    def _guardar(self):
        # Preparar datos para la mutación
        changes = []
        for r in self._rows:
            mf = r["metafield"]
            mf_type = r["type"]
            
            if mf_type == 'boolean':
                new_val = "true" if r["var"].get() else "false"
            elif mf_type in ('rich_text_field', 'multi_line_text_field') or mf.get('key') == 'componentes':
                new_val = r["widget"].get("1.0", "end-1c").strip()
            else:
                new_val = r["widget"].get().strip()
            
            # Solo si ha cambiado
            if new_val != str(mf.get("value")):
                changes.append({
                    "namespace": mf["namespace"],
                    "key": mf["key"],
                    "value": new_val,
                    "type": mf["type"]
                })
        
        if not changes:
            ToastWidget.show(self.frame, "No hay cambios que guardar", tipo="info")
            return

        self._status(f"Guardando {len(changes)} metacampos...")

        def work():
            res = self.service.metafields_set(self.producto.get("id"), changes)
            
            def done():
                if res.get("success"):
                    # Actualizar el objeto producto local con los nuevos valores
                    for change in changes:
                        for mf in (self.producto.get("metafields") or {}).get("nodes") or []:
                            if mf["namespace"] == change["namespace"] and mf["key"] == change["key"]:
                                mf["value"] = change["value"]
                    
                    ToastWidget.show(self.frame, "Metacampos actualizados correctamente", tipo="success")
                    self.frame.after(1000, self._volver)
                else:
                    self._status(f"Error: {res.get('message')}")
                    show_error(self.frame, f"Error al guardar: {res.get('message')}")
            
            self.frame.after(0, done)
            
        threading.Thread(target=work, daemon=True).start()

    def _status(self, texto):
        try:
            self._status_lbl.configure(text=texto)
        except Exception:
            pass
