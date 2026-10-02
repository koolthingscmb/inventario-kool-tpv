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
from kool_tpv.utils.dialogs.helpers import show_input_dialog
from kool_tpv.utils.dialogs.metaobject_select_dialog import show_metaobject_select_dialog
from ..services.shopify_product_service import ShopifyProductService
from ..services.shopify_metafields_service import ShopifyMetafieldsService

logger = logging.getLogger(__name__)

class ShopifyMetafieldsUI:
    """Subvista para editar los metacampos de un producto cargado."""

    def __init__(self, parent, db, producto: Dict[str, Any], on_volver: Optional[Callable] = None, on_aceptar: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.producto = producto or {}
        self.on_volver = on_volver
        self.on_aceptar = on_aceptar

        self.service = ShopifyProductService(db)
        self.meta_service = ShopifyMetafieldsService(db)

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
        
        ctk.CTkLabel(top, text=self.producto.get("title") or "NUEVO PRODUCTO",
                     font=("Helvetica", 12), text_color="#FFF").pack(side="left", padx=10)
        
        ctk.CTkButton(top, text="+ AÑADIR METACAMPO", width=160, height=34,
                      fg_color="#27ae60", text_color="#FFF",
                      font=("Helvetica", 11, "bold"),
                      command=self._anadir_nuevo_meta).pack(side="right", padx=20)

        # Acciones (Crear status_lbl aquí para que esté disponible durante la carga)
        acciones = tk.Frame(self.frame, bg=self._bg)
        acciones.pack(side="bottom", fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkButton(acciones, text="GUARDAR EN SHOPIFY", width=240, height=45,
                      fg_color=self._primary, text_color="#000",
                      font=("Helvetica", 14, "bold"),
                      command=self._guardar).pack(side="left")
        
        self._status_lbl = tk.Label(acciones, text="", fg="#888", bg=self._bg,
                                    font=("Helvetica", 11), anchor="w")
        self._status_lbl.pack(side="left", padx=15)

        # --- Cabecera de tabla (Triple columna: 6 columnas en total) ---
        cab = tk.Frame(self.frame, bg=self._bg)
        cab.pack(fill="x", padx=20, pady=(15, 0))
        
        # Clave (-30%), Valor (+ resto) repetido 3 veces
        # Ratio aproximado: 1 : 3
        weights = [10, 30, 10, 30, 10, 30] 
        for i, w in enumerate(weights):
            cab.columnconfigure(i, weight=w)

        headers = ["CLAVE", "VALOR / REFERENCIA"]
        for bloque in range(3): 
            for i, texto in enumerate(headers):
                col = (bloque * 2) + i
                lbl = tk.Label(cab, text=texto, fg="#888", bg=self._bg, anchor="w",
                               font=("Helvetica", 9, "bold"))
                lbl.grid(row=0, column=col, sticky="ew", padx=10, pady=5)

        # Separador visual bajo cabecera
        tk.Frame(self.frame, bg=self._primary, height=1).pack(fill="x", padx=20, pady=(0, 5))

        # --- Lista de metacampos ---
        self._scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=20, pady=0)
        self._weights = weights
        
        for i, w in enumerate(weights):
            self._scroll.columnconfigure(i, weight=w)

        # Cargar datos asíncronamente
        self._status("Cargando definiciones...")
        threading.Thread(target=self._cargar_datos_completos, daemon=True).start()

    def _cargar_datos_completos(self):
        """Carga definiciones y valores, y construye la lista."""
        try:
            # 1. Obtener definiciones custom
            definiciones = self.meta_service.obtener_definiciones_custom()
            
            # 2. Obtener valores reales del producto
            valores = {}
            if self.producto.get("id"):
                valores = self.meta_service.obtener_valores_producto(self.producto["id"])
            elif self.producto.get("metafields_list"):
                # Compatibilidad con productos nuevos que ya tienen metas preparados
                for m in self.producto["metafields_list"]:
                    valores[(m["namespace"], m["key"])] = m

            self.frame.after(0, lambda: self._render_metafields(definiciones, valores))
        except Exception as e:
            logger.exception("Error cargando metacampos")
            self.frame.after(0, lambda: self._status(f"Error: {str(e)}"))

    def _render_metafields(self, definiciones, valores):
        """Dibuja la lista combinando mapa (definiciones) y contenido (valores)."""
        self._rows = []
        for child in self._scroll.winfo_children():
            child.destroy()

        metafields_to_show = []
        for d in definiciones:
            id_meta = (d["namespace"], d["key"])
            val_obj = valores.get(id_meta, {})
            
            metafields_to_show.append({
                "namespace": d["namespace"],
                "key": d["key"],
                "type": d["type"]["name"],
                "value": val_obj.get("value", ""),
                "id": val_obj.get("id"),
                "description": d.get("description"),
                "validations": d.get("validations", [])
            })

        for idx, mf in enumerate(metafields_to_show):
            fila = idx // 3
            col_base = (idx % 3) * 2
            self._crear_bloque_metacampo(self._scroll, mf, fila, col_base)
            
        if not metafields_to_show:
            self._no_meta_lbl = ctk.CTkLabel(self._scroll, text="Sin definiciones custom disponibles",
                                             text_color="#666", font=("Helvetica", 12, "italic"))
            self._no_meta_lbl.pack(pady=40)
            self._status("Listo")
        else:
            self._status(f"Cargadas {len(metafields_to_show)} definiciones")

    def _anadir_nuevo_meta(self):
        """Añade una nueva fila de metacampo custom localmente."""
        # Si existía el label de 'Sin metacampos', lo quitamos
        if hasattr(self, '_no_meta_lbl') and self._no_meta_lbl.winfo_exists():
            self._no_meta_lbl.destroy()

        # Diálogo profesional de entrada (Kool Style)
        res = show_input_dialog(
            self.frame, 
            titulo="NUEVO METACAMPO",
            mensaje="Introduce la clave del nuevo metacampo (namespace: custom):"
        )
        
        if not res:
            return
            
        key = res.strip().lower().replace(" ", "_")
        
        # Evitar duplicados
        for r in self._rows:
            if r["metafield"].get("key") == key:
                show_error(self.frame, f"La clave '{key}' ya existe en la lista")
                return
        
        # Crear el objeto simulado de Shopify
        nuevo_mf = {
            "namespace": "custom",
            "key": key,
            "value": "",
            "type": "single_line_text_field" # Por defecto
        }
        
        idx = len(self._rows)
        fila = idx // 3
        col_base = (idx % 3) * 2
        
        self._crear_bloque_metacampo(self._scroll, nuevo_mf, fila, col_base)
        ToastWidget.show(self.frame, f"Metacampo '{key}' añadido a la lista", tipo="success")

    def _abrir_selector_metaobjetos(self, mf):
        """Abre un diálogo de selección múltiple para metaobjetos con resolución de dos pasos."""
        # 1. Buscar el ID de la definición en las validaciones
        definition_id = next(
            (v.get("value") for v in mf.get("validations", []) 
             if v.get("name") == "metaobject_definition_id"),
            None
        )
        
        if not definition_id:
            show_error(self.frame, "No se encontró la definición del metaobjeto para este campo")
            return

        self._status("Resolviendo tipo de objeto...")
        
        def work():
            # 2. Obtener el 'type' técnico a partir del ID de la definición
            tipo_meta = self.meta_service.obtener_tipo_metaobjeto_por_definicion(definition_id)
            if not tipo_meta:
                self.frame.after(0, lambda: show_error(self.frame, "No se pudo determinar el tipo de metaobjeto en Shopify"))
                self.frame.after(0, lambda: self._status("Error resolución"))
                return

            # 3. Cargar las entradas reales de ese tipo
            self.frame.after(0, lambda: self._status(f"Cargando opciones de {tipo_meta}..."))
            opciones = self.meta_service.obtener_entradas_metaobjeto(tipo_meta)
            self.frame.after(0, lambda: self._mostrar_dialogo_seleccion(mf, tipo_meta, opciones))
        
        threading.Thread(target=work, daemon=True).start()

    def _mostrar_dialogo_seleccion(self, mf, tipo_meta, opciones):
        self._status("Listo")
        if not opciones:
            show_error(self.frame, f"No hay entradas creadas para el tipo '{tipo_meta}' en Shopify")
            return

        # Encontrar la fila correspondiente para actualizar su 'var'
        fila_meta = next((r for r in self._rows if r["metafield"]["key"] == mf["key"]), None)
        if not fila_meta: return
        
        seleccionados_actuales = fila_meta["var"] or []

        # Mostrar el diálogo profesional (Kool Style)
        nuevos_seleccionados = show_metaobject_select_dialog(
            self.frame, tipo_meta, opciones, seleccionados_actuales
        )
        
        if nuevos_seleccionados is not None:
            fila_meta["var"] = nuevos_seleccionados
            n = len(nuevos_seleccionados)
            # Actualizar el texto del botón
            fila_meta["widget"].configure(text=f"{n} seleccionados ({tipo_meta.capitalize()})")
            ToastWidget.show(self.frame, f"Selección de {tipo_meta} actualizada", tipo="success")

    def _crear_bloque_metacampo(self, parent, mf, fila, col_base):
        # Todo sobre el fondo negro principal (self._bg)
        bg_main = self._bg
        
        # Clave (Key)
        lbl_key = tk.Label(parent, text=mf.get("key", ""), anchor="w",
                           fg="#FFF", bg=bg_main, font=("Consolas", 10, "bold"))
        lbl_key.grid(row=fila, column=col_base, sticky="nsew", padx=(10, 2), pady=6)

        # Valor / Widget
        val_frame = tk.Frame(parent, bg=bg_main)
        val_frame.grid(row=fila, column=col_base + 1, sticky="nsew", padx=(2, 15), pady=2)

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
        elif mf_type == 'list.metaobject_reference':
            # Obtener el tipo de metaobjeto de las validaciones
            tipo_meta = ""
            for v in mf.get("validations", []):
                if v["name"] == "type":
                    tipo_meta = v["value"]
                    break
            
            label_text = f"Gestionar {tipo_meta.capitalize() or 'Referencias'}"
            widget = ctk.CTkButton(val_frame, text=label_text, height=32,
                                  fg_color=self._secondary, font=("Helvetica", 11),
                                  command=lambda m=mf: self._abrir_selector_metaobjetos(m))
            widget.pack(fill="x", expand=True, padx=5, pady=4)
            # Guardamos los GIDs seleccionados en una variable asociada
            try:
                import json
                iniciales = json.loads(val) if val else []
            except:
                iniciales = []
            var = iniciales 
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
        all_metafields = []
        for r in self._rows:
            mf = r["metafield"]
            mf_type = r["type"]
            
            if mf_type == 'boolean':
                new_val = "true" if r["var"].get() else "false"
            elif mf_type == 'list.metaobject_reference':
                new_val = json.dumps(r["var"]) # Es una lista de GIDs
            elif mf_type in ('rich_text_field', 'multi_line_text_field') or mf.get('key') == 'componentes':
                new_val = r["widget"].get("1.0", "end-1c").strip()
            else:
                new_val = r["widget"].get().strip()
            
            meta_item = {
                "namespace": mf["namespace"],
                "key": mf["key"],
                "value": new_val,
                "type": mf["type"]
            }
            all_metafields.append(meta_item)

            # Solo si ha cambiado respecto al original (si existía original)
            orig_val = str(mf.get("value", ""))
            if new_val != orig_val:
                changes.append(meta_item)
        
        # Si no hay producto ID (modo NUEVO), devolvemos la lista al padre sin llamar a la API
        if not self.producto.get("id"):
            if self.on_aceptar:
                self.on_aceptar(all_metafields)
            ToastWidget.show(self.frame, "Metacampos preparados localmente", tipo="success")
            self.frame.after(500, self._volver)
            return

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
                    
                    if self.on_aceptar:
                        self.on_aceptar(all_metafields)
                        
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
