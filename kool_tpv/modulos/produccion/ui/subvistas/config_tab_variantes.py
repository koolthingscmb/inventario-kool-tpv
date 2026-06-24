"""Tab de configuración de Variantes de tipos de producción."""
import tkinter as tk
import customtkinter as ctk
from typing import List, Optional

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget


class ConfigTabVariantes:
    """Pestaña VARIANTES: 50% nav_list de variantes | 50% formulario."""

    def __init__(self, parent, config_service, config, colors, km, layout_config):
        self.parent = parent
        self.config_service = config_service  # ProduccionConfigService
        self.db = config_service.db
        self.service = ProduccionTiposVariantesService(self.db)
        
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        
        self._variante_id_edit = None
        self._nav = None
        self._all_tipos = []
        self._tipo_id_selected = tk.IntVar(value=0)
        
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: nav_list de variantes (50%) ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        columns = [
            ("tipo", 120, "TIPO"),
            ("nombre", 150, "VARIANTE"),
            ("coste", 80, "COSTE"),
            ("precio", 80, "P.REC"),
            ("estado", 40, "ACT"),
        ]
        self._nav = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Botones CRUD debajo de la lista
        frame_btns_left = tk.Frame(frame_lista, bg="#34495e")
        frame_btns_left.pack(fill="x", padx=6, pady=(0, 6))
        ctk.CTkButton(frame_btns_left, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar).pack(side=tk.LEFT, padx=(0, 4), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns_left, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar).pack(side=tk.LEFT, padx=(4, 0), expand=True, fill=tk.X)

        # --- DERECHA: formulario (50%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        form = tk.Frame(frame_right, bg="#34495e")
        form.pack(fill="both", expand=True, padx=20, pady=20)

        # Combo de Tipos
        tk.Label(form, text="TIPO DE PRODUCTO:", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(anchor="w", pady=(0, 5))
        
        self._all_tipos = self.config_service.tipos_repo.get_activos()
        tipo_nombres = [t.nombre for t in self._all_tipos]
        
        self._combo_tipo = ctk.CTkComboBox(form, values=tipo_nombres, width=300)
        self._combo_tipo.pack(fill="x", pady=(0, 15))

        # Nombre Variante
        tk.Label(form, text="NOMBRE VARIANTE (ej: A4, Sorpresa...):", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(anchor="w", pady=(0, 5))
        self._entry_nombre = ctk.CTkEntry(form, placeholder_text="Nombre de la variante...", width=300)
        self._entry_nombre.pack(fill="x", pady=(0, 15))

        # Fila Coste y Precio
        row_precios = tk.Frame(form, bg="#34495e")
        row_precios.pack(fill="x", pady=(0, 15))

        # Coste
        f_coste = tk.Frame(row_precios, bg="#34495e")
        f_coste.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        tk.Label(f_coste, text="COSTE (€):", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(anchor="w")
        self._entry_coste = ctk.CTkEntry(f_coste, placeholder_text="0.00")
        self._entry_coste.pack(fill="x")

        # Precio
        f_precio = tk.Frame(row_precios, bg="#34495e")
        f_precio.pack(side=tk.LEFT, fill="x", expand=True, padx=(5, 0))
        tk.Label(f_precio, text="P. REC (€):", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(anchor="w")
        self._entry_precio = ctk.CTkEntry(f_precio, placeholder_text="0.00")
        self._entry_precio.pack(fill="x")

        # Shopify ID
        tk.Label(form, text="SHOPIFY VARIANT ID (opcional):", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(anchor="w", pady=(0, 5))
        self._entry_shopify = ctk.CTkEntry(form, placeholder_text="ID de variante en Shopify...", width=300)
        self._entry_shopify.pack(fill="x", pady=(0, 15))

        # Activo y Requerimientos
        row_checks = tk.Frame(form, bg="#34495e")
        row_checks.pack(fill="x", pady=(0, 20))

        self._var_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(row_checks, text="Variante Activa", variable=self._var_activo,
                        fg_color="#27ae60", text_color=self._text).pack(side=tk.LEFT, padx=(0, 15))

        self._var_requiere_talla = ctk.IntVar(value=0)
        ctk.CTkCheckBox(row_checks, text="Requiere Talla", variable=self._var_requiere_talla,
                        fg_color="#3498db", text_color=self._text).pack(side=tk.LEFT, padx=(0, 15))

        self._var_requiere_color = ctk.IntVar(value=0)
        ctk.CTkCheckBox(row_checks, text="Requiere Color", variable=self._var_requiere_color,
                        fg_color="#9b59b6", text_color=self._text).pack(side=tk.LEFT)

        # Botón Guardar
        ctk.CTkButton(form, text="GUARDAR VARIANTE", fg_color="#27ae60", hover_color="#2ecc71",
                      height=40, font=get_font(self.config, "button"),
                      command=self._guardar).pack(fill="x")

        self._cargar_lista()

    def _cargar_lista(self):
        variantes = self.service.obtener_todos()
        tipos_map = {t.id: t.nombre for t in self.config_service.tipos_repo.get_todos()}
        
        items = []
        for v in variantes:
            items.append({
                "id": v.id,
                "tipo": tipos_map.get(v.tipo_id, f"ID:{v.tipo_id}"),
                "nombre": v.nombre,
                "coste": f"{v.coste_base/100:.2f} €",
                "precio": f"{v.precio_recomendado/100:.2f} €",
                "estado": "✓" if v.activo else "✗",
                "_obj": v
            })
        self._nav.set_items(items)

    def _on_selected(self, data):
        v = data.get("_obj")
        if not v: return
        
        self._variante_id_edit = v.id
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, v.nombre)
        
        # Seleccionar tipo en combo
        tipo_nombre = data.get("tipo")
        self._combo_tipo.set(tipo_nombre)
        
        # Precios (de céntimos a float para el entry)
        self._entry_coste.delete(0, tk.END)
        self._entry_coste.insert(0, f"{v.coste_base/100:.2f}")
        self._entry_precio.delete(0, tk.END)
        self._entry_precio.insert(0, f"{v.precio_recomendado/100:.2f}")
        
        self._entry_shopify.delete(0, tk.END)
        self._entry_shopify.insert(0, v.shopify_variant_id or "")
        
        self._var_activo.set(v.activo)
        self._var_requiere_talla.set(v.requiere_talla)
        self._var_requiere_color.set(v.requiere_color)

    def _guardar(self):
        tipo_nombre = self._combo_tipo.get()
        tipo_id = next((t.id for t in self._all_tipos if t.nombre == tipo_nombre), None)
        
        if not tipo_id:
            ToastWidget.show(self.parent, "Selecciona un tipo de producto", tipo="warning")
            return
            
        nombre = self._entry_nombre.get().strip()
        if not nombre:
            ToastWidget.show(self.parent, "Introduce un nombre para la variante", tipo="warning")
            return

        # Parsear precios a céntimos (int)
        try:
            coste_val = float(self._entry_coste.get().replace(",", ".") or "0")
            coste_cents = int(round(coste_val * 100))
            
            precio_val = float(self._entry_precio.get().replace(",", ".") or "0")
            precio_cents = int(round(precio_val * 100))
        except ValueError:
            ToastWidget.show(self.parent, "Los precios deben ser numéricos", tipo="error")
            return

        shopify_id = self._entry_shopify.get().strip() or None
        activo = self._var_activo.get()
        req_talla = self._var_requiere_talla.get()
        req_color = self._var_requiere_color.get()

        if self._variante_id_edit:
            ok = self.service.actualizar(
                self._variante_id_edit, tipo_id, nombre, 
                coste_cents, precio_cents, activo, shopify_id,
                req_talla, req_color
            )
        else:
            res = self.service.crear(tipo_id, nombre, coste_cents, precio_cents, shopify_id, req_talla, req_color)
            ok = res is not None

        if ok:
            ToastWidget.show(self.parent, "Variante guardada correctamente", tipo="success")
            self._limpiar()
            self._cargar_lista()
        else:
            ToastWidget.show(self.parent, "Error al guardar la variante", tipo="error")

    def _limpiar(self):
        self._variante_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._entry_coste.delete(0, tk.END)
        self._entry_precio.delete(0, tk.END)
        self._entry_shopify.delete(0, tk.END)
        self._var_activo.set(1)
        self._var_requiere_talla.set(0)
        self._var_requiere_color.set(0)
        self._combo_tipo.set("")

    def _eliminar(self):
        if not self._variante_id_edit: return
        if self.service.eliminar(self._variante_id_edit):
            ToastWidget.show(self.parent, "Variante eliminada", tipo="info")
            self._limpiar()
            self._cargar_lista()

    def refresh_nav(self):
        if self._nav and hasattr(self._nav, '_refresh_ui'):
            self._nav.update_idletasks()
            self._nav._refresh_ui()
