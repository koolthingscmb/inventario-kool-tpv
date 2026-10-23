"""CrearProductoUI (refactor): Interfaz Terminal Pro para altas de producto.

Nueva versión:
- 2 pestañas: [01] GENERAL y [02] SHOPIFY
- Grid de 8 columnas por fila para alineación.
- Estilo Terminal: fondo #1a1a1a, `Courier New`, texto verde (#00FF00).
- Searchable ComboBoxes con modo estricto (mapeo nombre->id).
- Guardado con transacción que actualiza `productos` y `precios`.
"""
from typing import Dict, Optional, List, Tuple
import logging
import re
import threading
import webbrowser
import tkinter as tk

import customtkinter as ctk

from kool_tpv.utils.utils import (
    COLOR_BG_TERMINAL,
    COLOR_BG_SIDEBAR,
    COLOR_MATRIX,
    COLOR_ERROR,
    FONT_TERMINAL,
    FONT_BUTTONS,
    SIDEBAR_WIDTH,
)


from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.config_loader import create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.dialogs.input_dialog import InputDialog
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.utils import barcode_gen_utils
from kool_tpv.utils.sku_generator import generate_sku
from kool_tpv.modulos.shopify.services.seo_ficha_service import SeoFichaService
from kool_tpv.modulos.almacen.services.obtener_datos_service import ObtenerDatosService
from kool_tpv.modulos.almacen.services.portadas_service import PortadasService
from kool_tpv.modulos.almacen.services.metacampos_comic_service import MetacamposComicService
from kool_tpv.modulos.almacen.services.comparador_metacampos_service import ComparadorMetacamposService
from kool_tpv.utils.dialogs.metaobject_select_dialog import show_metacampos_agrupados_dialog

logger = logging.getLogger(__name__)




class CrearProductoUI:
    def __init__(self, parent, db: Optional[object] = None, producto_id: Optional[int] = None, module_name: str = 'almacen', owner=None):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.producto_id = producto_id
        self.owner = owner
        self.repo = ProductoRepository(db) if db is not None else None
        self._tech_extra = {}
        self._metacampos = {}  # clave metacampo Shopify -> nombre o lista de nombres
        self._foto = None  # get_data() al cargar el producto: detecta cambios sin guardar
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'accent': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL, 'light': '#666666'}
        try:
            self.colors_shopify = load_colors('shopify')
        except Exception:
            self.colors_shopify = self.colors
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # Header removed: breadcrumb is provided by BaseModuleView

        # Build stacked frames: GENERAL above SHOPIFY (no TabView)
        self.general_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.general_frame.pack(fill='both', expand=False, padx=12, pady=8)

        # La zona Shopify usa los colores del módulo Shopify en sus campos y botones
        shop_primary = self.colors_shopify.get('primary', self.colors.get('primary', COLOR_MATRIX))
        self._shop_primary = shop_primary
        self.shopify_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.shopify_frame.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        # Common styles
        lbl_font = get_font('label', module=self.module_name)
        entry_kwargs = {"fg_color": self.colors.get('background', COLOR_BG_TERMINAL), "text_color": self.colors['text'], "border_width": 2, "border_color": self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)), "corner_radius": 4}
        shop_entry_kwargs = dict(entry_kwargs)
        shop_entry_kwargs['border_color'] = shop_primary
        shop_txt = self.colors_shopify.get('light', self.colors.get('light'))
        shop_entry_kwargs['text_color'] = shop_txt

        # Build GENERAL frame with 8-column grid (7 filas requeridas)
        for c in range(8):
            self.general_frame.grid_columnconfigure(c, weight=1, uniform='col')

        # Fila 1: ID (1) | NOMBRE (3) | ORIGINAL (2) | OBTENER (1)
        ctk.CTkLabel(self.general_frame, text="ID:", text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        # Use a StringVar so we can react when ID is set/changed and refresh 'Tesoro'
        try:
            self.e_id_var = tk.StringVar(value='')
        except Exception:
            self.e_id_var = None
        if self.e_id_var is not None:
            self.e_id = ctk.CTkEntry(self.general_frame, textvariable=self.e_id_var, placeholder_text="ID (auto)", state='disabled', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors.get('light', '#666666'), border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
        else:
            self.e_id = ctk.CTkEntry(self.general_frame, placeholder_text="ID (auto)", state='disabled', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors.get('light', '#666666'), border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
        self.e_id.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="NOMBRE:", text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.general_frame, placeholder_text="Nombre del producto", **entry_kwargs)
        self.e_nombre.grid(row=0, column=3, columnspan=2, sticky='ew', padx=6, pady=6)
        self.e_nombre.bind('<FocusOut>', lambda e: self._auto_generate_sku())

        ctk.CTkLabel(self.general_frame, text="ORIGINAL:", text_color=self.colors['text'], font=lbl_font).grid(row=0, column=5, sticky='w', padx=6, pady=6)
        self.e_nombre_original = ctk.CTkEntry(self.general_frame, placeholder_text='Título original', **entry_kwargs)
        self.e_nombre_original.grid(row=0, column=6, sticky='ew', padx=6, pady=6)

        # Botón OBTENER
        try:
            self.btn_obtener = ButtonFactory.create_button(
                parent=self.general_frame,
                text='OBTENER',
                command=self._on_obtener,
                style_key="mini_action",
                module='almacen',
                palette_key='accent'
            )
            self.btn_obtener.grid(row=0, column=7, sticky='ew', padx=6, pady=6)
        except Exception:
            logger.exception('Error creando botón OBTENER')

        # Fila 2: SKU (3) | EDITORIAL (2) | IR (1) | NOMBRE_BOTÓN (2)
        ctk.CTkLabel(self.general_frame, text="SKU:", text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_sku = ctk.CTkEntry(self.general_frame, placeholder_text='SKU', **entry_kwargs)
        self.e_sku.grid(row=1, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="EDITORIAL:", text_color=self.colors['text'], font=lbl_font).grid(row=1, column=3, sticky='w', padx=6, pady=6)
        self.cb_editorial = SearchableCombo(self.general_frame, placeholder='Buscar editorial')
        self.cb_editorial.grid(row=1, column=4, sticky='ew', padx=6, pady=6)
        
        # Botón IR para editorial
        try:
            self.btn_ir_editorial = ButtonFactory.create_button(
                parent=self.general_frame,
                text='IR',
                command=self._on_buscar_editorial,
                style_key="mini_action",
                module='almacen',
                palette_key='secondary'
            )
            self.btn_ir_editorial.grid(row=1, column=5, sticky='ew', padx=6, pady=6)
        except Exception:
            logger.exception('Error creando botón IR editorial')

        ctk.CTkLabel(self.general_frame, text="BOTÓN:", text_color=self.colors['text'], font=lbl_font).grid(row=1, column=6, sticky='w', padx=6, pady=6)
        self.e_nombre_btn = ctk.CTkEntry(self.general_frame, placeholder_text='Texto botón', **entry_kwargs)
        self.e_nombre_btn.grid(row=1, column=7, sticky='ew', padx=6, pady=6)

        # Fila 3: CATEGORIA | TIPO | PROVEEDOR (sin cambios)
        ctk.CTkLabel(self.general_frame, text="CATEGORÍA:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.cb_categoria = SearchableCombo(self.general_frame, placeholder='Buscar categoría')
        self.cb_categoria.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="TIPO:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=3, sticky='w', padx=6, pady=6)
        self.cb_tipo = SearchableCombo(self.general_frame, placeholder='Buscar tipo')
        self.cb_tipo.grid(row=2, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="PROVEEDOR:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=6, sticky='w', padx=6, pady=6)
        self.cb_proveedor = SearchableCombo(self.general_frame, placeholder='Buscar proveedor')
        self.cb_proveedor.grid(row=2, column=7, sticky='ew', padx=6, pady=6)

        # Fila 4: PVP | COSTE | IVA
        ctk.CTkLabel(self.general_frame, text="PVP:", text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_pvp = ctk.CTkEntry(self.general_frame, placeholder_text='0.00', **entry_kwargs)
        self.e_pvp.grid(row=3, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="COSTE:", text_color=self.colors['text'], font=lbl_font).grid(row=3, column=3, sticky='w', padx=6, pady=6)
        self.e_coste = ctk.CTkEntry(self.general_frame, placeholder_text='0.00', **entry_kwargs)
        self.e_coste.grid(row=3, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="TIPO_IVA:", text_color=self.colors['text'], font=lbl_font).grid(row=3, column=6, sticky='w', padx=6, pady=6)
        self.cb_iva = SearchableCombo(self.general_frame, placeholder='IVA')
        self.cb_iva.grid(row=3, column=7, sticky='ew', padx=6, pady=6)

        # Fila 5: PVP_VARIABLE | PRODUCIDO | ACTIVO | TESORO
        self.chk_pvp_var_var = tk.BooleanVar(value=False)
        ctk.CTkLabel(self.general_frame, text="PVP_VARIABLE:", text_color=self.colors['text'], font=lbl_font).grid(row=4, column=0, sticky='w', padx=6, pady=6)
        self.chk_pvp_var = ctk.CTkCheckBox(self.general_frame, text='', variable=self.chk_pvp_var_var, fg_color=self.colors['secondary'])
        self.chk_pvp_var.grid(row=4, column=1, sticky='w', padx=6, pady=6)

        self.chk_fabricado_var = tk.BooleanVar(value=False)
        ctk.CTkLabel(self.general_frame, text="PRODUCIDO:", text_color=self.colors['text'], font=lbl_font).grid(row=4, column=2, sticky='w', padx=6, pady=6)
        self.chk_fabricado = ctk.CTkCheckBox(self.general_frame, text='', variable=self.chk_fabricado_var, fg_color=self.colors['secondary'])
        self.chk_fabricado.grid(row=4, column=3, sticky='w', padx=6, pady=6)


        # Fila 6: STOCK_ACTUAL | AJUSTAR | STOCK_MINIMO | VENTAS
        ctk.CTkLabel(self.general_frame, text="STOCK_ACTUAL:", text_color=self.colors['text'], font=lbl_font).grid(row=5, column=0, sticky='w', padx=6, pady=6)
        
        # Campo stock_actual como readonly para forzar uso del botón AJUSTAR
        self.e_stock_actual = ctk.CTkEntry(
            self.general_frame, 
            placeholder_text='0', 
            state='readonly',
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('light', '#666666'),
            border_color=self.colors.get('border', self.colors.get('light', '#666666')),
            border_width=2
        )
        self.e_stock_actual.grid(row=5, column=1, sticky='ew', padx=6, pady=6)
        
        # Botón AJUSTAR usando ButtonFactory ⭐
        try:
            self.btn_ajustar = ButtonFactory.create_button(
                parent=self.general_frame,
                text='AJUSTAR',
                command=self._on_ajustar_stock,
                style_key="mini_action",
                module='almacen',
                palette_key='accent'
            )
            self.btn_ajustar.grid(row=5, column=2, sticky='ew', padx=6, pady=6)
        except Exception:
            logger.exception('Error creando botón AJUSTAR')

        ctk.CTkLabel(self.general_frame, text="STOCK_MINIMO:", text_color=self.colors['text'], font=lbl_font).grid(row=5, column=3, sticky='w', padx=6, pady=6)
        self.e_stock_min = ctk.CTkEntry(self.general_frame, placeholder_text='0', **entry_kwargs)
        self.e_stock_min.grid(row=5, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="VENTAS:", text_color=self.colors['text'], font=lbl_font).grid(row=5, column=6, sticky='w', padx=6, pady=6)
        # Use a StringVar bound to the Entry so the UI can be updated even when readonly
        try:
            self.e_ventas_var = tk.StringVar(value='0')
        except Exception:
            self.e_ventas_var = None
        try:
            if self.e_ventas_var is not None:
                self.e_ventas = ctk.CTkEntry(self.general_frame, textvariable=self.e_ventas_var, state='readonly', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors.get('light', '#666666'), border_color=self.colors.get('border', self.colors.get('light', '#666666')), border_width=2)
            else:
                self.e_ventas = ctk.CTkEntry(self.general_frame, placeholder_text='0', state='readonly', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors.get('light', '#666666'), border_color=self.colors.get('border', self.colors.get('light', '#666666')), border_width=2)
        except Exception:
            # fallback: disabled entry if readonly not supported
            try:
                self.e_ventas = ctk.CTkEntry(self.general_frame, placeholder_text='0', state='disabled', fg_color=COLOR_BG_TERMINAL, text_color="#666666", border_color=self.colors['light'], border_width=2)
            except Exception:
                self.e_ventas = tk.Entry(self.general_frame)
        self.e_ventas.grid(row=5, column=7, sticky='ew', padx=6, pady=6)

        # Use a BooleanVar to track activo state
        self.chk_activo_var = tk.BooleanVar(value=True)

        # Place a small container in the same grid cell to hold the 'Activo' label and the checkbox
        try:
            self._activo_frame = ctk.CTkFrame(self.general_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
            self._activo_frame.grid(row=4, column=4, columnspan=2, sticky='w', padx=6, pady=6)
            try:
                ctk.CTkLabel(self._activo_frame, text='Activo', text_color=self.colors['text'], font=lbl_font).pack(side='left')
            except Exception:
                try:
                    tk.Label(self._activo_frame, text='Activo').pack(side='left')
                except Exception:
                    pass
            # Checkbox keeps its descriptive label
            try:
                self.chk_activo = ctk.CTkCheckBox(self._activo_frame, text='Producto activo', variable=self.chk_activo_var, fg_color=self.colors['secondary'], text_color=self.colors['secondary'])
                self.chk_activo.pack(side='left', padx=(6, 0))
            except Exception:
                try:
                    self.chk_activo = tk.Checkbutton(self._activo_frame, text='Producto activo', variable=self.chk_activo_var)
                    self.chk_activo.pack(side='left', padx=(6, 0))
                except Exception:
                    pass
        except Exception:
            # Fallback: place checkbox in grid and a separate label if frame creation fails
            try:
                ctk.CTkLabel(self.general_frame, text='Activo', text_color=self.colors['text'], font=lbl_font).grid(row=4, column=4, sticky='w', padx=6, pady=6)
            except Exception:
                try:
                    tk.Label(self.general_frame, text='Activo').grid(row=4, column=4, sticky='w', padx=6, pady=6)
                except Exception:
                    pass
            try:
                self.chk_activo = ctk.CTkCheckBox(self.general_frame, text='Producto activo', variable=self.chk_activo_var, fg_color=self.colors['secondary'], text_color=self.colors['secondary'])
                self.chk_activo.grid(row=4, column=5, columnspan=1, sticky='w', padx=6, pady=6)
            except Exception:
                try:
                    self.chk_activo = tk.Checkbutton(self.general_frame, text='Producto activo', variable=self.chk_activo_var)
                    self.chk_activo.grid(row=4, column=5, columnspan=1, sticky='w', padx=6, pady=6)
                except Exception:
                    pass

        # Read-only 'Tesoro' label to the right
        try:
            self.lbl_tesoro_var = tk.StringVar(value='Tesoro: -')
        except Exception:
            self.lbl_tesoro_var = None
        try:
            if self.lbl_tesoro_var is not None:
                self.lbl_tesoro = ctk.CTkLabel(self.general_frame, textvariable=self.lbl_tesoro_var, text_color=self.colors['text'], font=lbl_font)
            else:
                self.lbl_tesoro = ctk.CTkLabel(self.general_frame, text='Tesoro: -', text_color=self.colors['text'], font=lbl_font)
        except Exception:
            self.lbl_tesoro = tk.Label(self.general_frame, text='Tesoro: -')
        self.lbl_tesoro.grid(row=4, column=7, sticky='e', padx=6, pady=6)

        # Fila 7: CÓDIGOS_DE_BARRAS (CSV separado por comas)
        ctk.CTkLabel(self.general_frame, text="CÓDIGOS:", text_color=self.colors['text'], font=lbl_font).grid(row=6, column=0, sticky='w', padx=6, pady=6)
        
        # Botón para generar código interno ⭐
        try:
            self.btn_gen_barcode = ButtonFactory.create_button(
                parent=self.general_frame,
                text='BARRAS',
                command=self._on_gen_barcode_interno,
                style_key="mini_action",
                module='almacen',
                palette_key='secondary'
            )
            self.btn_gen_barcode.grid(row=6, column=1, sticky='ew', padx=6, pady=6)
        except Exception:
            logger.exception('Error creando botón BARRAS')

        try:
            self.e_codigos = ctk.CTkEntry(self.general_frame, placeholder_text='ean1,ean2,ean3', **entry_kwargs)
        except Exception:
            self.e_codigos = tk.Entry(self.general_frame)
        self.e_codigos.grid(row=6, column=2, columnspan=6, sticky='nsew', padx=6, pady=6)

        # Separador de la zona Shopify: etiqueta + línea en color del módulo
        sep_frame = ctk.CTkFrame(self.general_frame, fg_color='transparent')
        sep_frame.grid(row=7, column=0, columnspan=8, sticky='ew', padx=6, pady=(12, 6))
        ctk.CTkLabel(sep_frame, text='SHOPIFY', text_color=shop_primary, font=lbl_font).pack(side='left')
        ctk.CTkFrame(sep_frame, height=2, corner_radius=0, fg_color=shop_primary).pack(side='left', fill='x', expand=True, padx=(10, 0), pady=6)

        # Load options from DB if available
        self._load_db_options()

        # SHOPIFY tab: 6 filas en rejilla de 15 columnas, etiquetas en azul Shopify
        for c in range(15):
            self.shopify_frame.grid_columnconfigure(c, weight=1, uniform='col')
        shop_lbl = shop_primary

        # Fila 1: TITULO (6) | AUTOR (5) | AÑO (4)
        ctk.CTkLabel(self.shopify_frame, text='TITULO:', text_color=shop_lbl, font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=8)
        self.e_store_title = ctk.CTkEntry(self.shopify_frame, placeholder_text='Título web', **shop_entry_kwargs)
        self.e_store_title.grid(row=0, column=1, columnspan=5, sticky='ew', padx=6, pady=8)

        ctk.CTkLabel(self.shopify_frame, text='AUTOR:', text_color=shop_lbl, font=lbl_font).grid(row=0, column=6, sticky='w', padx=6, pady=8)
        self.e_autor = ctk.CTkEntry(self.shopify_frame, placeholder_text='Autor', **shop_entry_kwargs)
        self.e_autor.grid(row=0, column=7, columnspan=4, sticky='ew', padx=6, pady=8)

        ctk.CTkLabel(self.shopify_frame, text='AÑO:', text_color=shop_lbl, font=lbl_font).grid(row=0, column=11, sticky='w', padx=6, pady=8)
        self.e_anio = ctk.CTkEntry(self.shopify_frame, placeholder_text='Año', **shop_entry_kwargs)
        self.e_anio.grid(row=0, column=12, columnspan=3, sticky='ew', padx=6, pady=8)

        # Fila 2: LINK (6) | IR (1) | TAGS (8)
        ctk.CTkLabel(self.shopify_frame, text='LINK:', text_color=shop_lbl, font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=8)
        self.e_shop_link = ctk.CTkEntry(self.shopify_frame, placeholder_text='https://…', **shop_entry_kwargs)
        self.e_shop_link.grid(row=1, column=1, columnspan=5, sticky='ew', padx=6, pady=8)
        try:
            ButtonFactory.create_button(
                parent=self.shopify_frame,
                text='IR',
                command=self._open_shop_link,
                style_key="mini_action",
                module='shopify',
                palette_key='secondary'
            ).grid(row=1, column=6, sticky='ew', padx=6, pady=8)
        except Exception:
            pass

        ctk.CTkLabel(self.shopify_frame, text='TAGS:', text_color=shop_lbl, font=lbl_font).grid(row=1, column=7, sticky='w', padx=6, pady=8)
        self.e_tags = ctk.CTkEntry(self.shopify_frame, placeholder_text='tag1, tag2', **shop_entry_kwargs)
        self.e_tags.grid(row=1, column=8, columnspan=7, sticky='ew', padx=6, pady=8)

        # Fila 3: botón pequeño METACAMPOS + las 4 cajas repartiendo el ancho
        meta_row = ctk.CTkFrame(self.shopify_frame, fg_color='transparent')
        meta_row.grid(row=2, column=0, columnspan=15, sticky='ew', padx=6, pady=8)

        self.btn_metacampos = ctk.CTkButton(
            meta_row, text='METACAMPOS', height=26, width=90,
            font=("Helvetica", 10, "bold"),
            fg_color=shop_primary, text_color=self.colors.get('background', COLOR_BG_TERMINAL),
            command=self._on_metacampos_click)
        self.btn_metacampos.pack(side='left', padx=(0, 10))

        for attr, etiqueta, ph in (
            ('e_meta_demografia', 'DEMOGRAFÍA:', 'Demografía'),
            ('e_meta_genero', 'GÉNERO:', 'Género'),
            ('e_meta_subgenero', 'TEMÁTICAS:', 'Temática'),
            ('e_meta_contenido', 'CONTENIDO:', 'Contenido'),
        ):
            ctk.CTkLabel(meta_row, text=etiqueta, text_color=shop_lbl, font=lbl_font).pack(side='left', padx=(8, 4))
            entry = self._crear_meta_entry(ph, parent=meta_row)
            entry.pack(side='left', expand=True, fill='x', padx=(0, 8))
            setattr(self, attr, entry)

        # Fila 4: SEO_TITLE (5) | TAXONOMY (10)
        ctk.CTkLabel(self.shopify_frame, text='SEO_TITLE:', text_color=shop_lbl, font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=8)
        self.e_google_title = ctk.CTkEntry(self.shopify_frame, placeholder_text='SEO short title', **shop_entry_kwargs)
        self.e_google_title.grid(row=3, column=1, columnspan=4, sticky='ew', padx=6, pady=8)

        ctk.CTkLabel(self.shopify_frame, text='TAXONOMY:', text_color=shop_lbl, font=lbl_font).grid(row=3, column=5, sticky='w', padx=6, pady=8)
        # Readonly entry to allow selection/copy but prevent manual edits
        try:
            self.ent_taxonomy = ctk.CTkEntry(self.shopify_frame, placeholder_text='', state='readonly', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=shop_txt, border_width=2, border_color=shop_primary, corner_radius=4)
        except Exception:
            # fallback if customtkinter does not support readonly state
            self.ent_taxonomy = ctk.CTkEntry(self.shopify_frame, placeholder_text='', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=shop_txt, border_width=2, border_color=shop_primary, corner_radius=4)
            try:
                self.ent_taxonomy.configure(state='readonly')
            except Exception:
                pass
        self.ent_taxonomy.grid(row=3, column=6, columnspan=9, sticky='ew', padx=6, pady=8)

        # Fila 5: SINOPSIS (textbox, ancho completo)
        ctk.CTkLabel(self.shopify_frame, text='SINOPSIS:', text_color=shop_lbl, font=lbl_font).grid(row=4, column=0, sticky='nw', padx=6, pady=8)
        try:
            self.txt_sinopsis = ctk.CTkTextbox(self.shopify_frame, width=800, height=60, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=shop_txt, border_width=2, border_color=shop_primary)
            self.txt_sinopsis.grid(row=4, column=1, columnspan=14, sticky='nsew', padx=6, pady=8)
        except Exception:
            frame_sin = ctk.CTkFrame(self.shopify_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), border_width=2, border_color=shop_primary)
            self.txt_sinopsis = tk.Text(frame_sin, bg=self.colors.get('background', COLOR_BG_TERMINAL), fg=shop_txt, height=3)
            self.txt_sinopsis.pack(fill='both', expand=True)
            frame_sin.grid(row=4, column=1, columnspan=14, sticky='nsew', padx=6, pady=8)

        # Fila 6: SEO_DESCRIPTION (7) | DESCRIPCION (8), misma altura
        ctk.CTkLabel(self.shopify_frame, text='SEO_DESCRIPTION:', text_color=shop_lbl, font=lbl_font).grid(row=5, column=0, columnspan=2, sticky='nw', padx=6, pady=8)
        try:
            self.e_seo_desc = ctk.CTkTextbox(self.shopify_frame, height=100, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=shop_txt, border_width=2, border_color=shop_primary)
            self.e_seo_desc.grid(row=5, column=2, columnspan=5, sticky='nsew', padx=6, pady=8)
            try:
                # make Tab move to next widget instead of inserting a tab character
                self.e_seo_desc.bind('<Tab>', lambda e: self._focus_next_widget(e))
            except Exception:
                pass
        except Exception:
            # fallback: wrap tk.Text in a framed CTkFrame to simulate border
            frame = ctk.CTkFrame(self.shopify_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), border_width=2, border_color=shop_primary)
            self.e_seo_desc = tk.Text(frame, bg=self.colors.get('background', COLOR_BG_TERMINAL), fg=shop_txt)
            self.e_seo_desc.pack(fill='both', expand=True)
            frame.grid(row=5, column=2, columnspan=5, sticky='nsew', padx=6, pady=8)

        ctk.CTkLabel(self.shopify_frame, text='DESCRIPCION:', text_color=shop_lbl, font=lbl_font).grid(row=5, column=7, columnspan=2, sticky='nw', padx=6, pady=8)
        try:
            self.txt_description = ctk.CTkTextbox(self.shopify_frame, height=100, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=shop_txt, border_width=2, border_color=shop_primary)
            self.txt_description.grid(row=5, column=9, columnspan=6, sticky='nsew', padx=6, pady=8)
            try:
                # Tab from description should go directly to the Guardar button
                try:
                    self.txt_description.unbind('<Tab>')
                except Exception:
                    pass
                self.txt_description.bind('<Tab>', lambda e: self._focus_to_guardar(e))
            except Exception:
                pass
        except Exception:
            frame2 = ctk.CTkFrame(self.shopify_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), border_width=2, border_color=shop_primary)
            self.txt_description = tk.Text(frame2, bg=self.colors.get('background', COLOR_BG_TERMINAL), fg=shop_txt)
            self.txt_description.pack(fill='both', expand=True)
            frame2.grid(row=5, column=9, columnspan=6, sticky='nsew', padx=6, pady=8)
        self.shopify_frame.grid_rowconfigure(5, weight=1)

        # Bottom buttons (aligned left per style guide)
        # Use terminal bg for footer to ensure buttons are visible and contrast correctly
        self.btn_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.btn_frame.pack(side='bottom', fill='x', padx=12, pady=12)
        # Guardar (desde config)
        self.btn_guardar = create_action_button(self.btn_frame, 'guardar', self._on_save, module='almacen', palette_key='primary')
        self.btn_guardar.pack(side='left', padx=8)
        # Movimientos (nuevo)
        self.btn_movimientos = create_action_button(self.btn_frame, 'buscar_articulo', self._on_ver_movimientos, module='almacen', palette_key='accent')
        self.btn_movimientos.configure(text='MOVIMIENTOS')
        self.btn_movimientos.pack(side='left', padx=8)

        # Sincronizar (desde config)
        self.btn_sync = create_action_button(self.btn_frame, 'subir_shopify', self._on_sync, module='almacen', palette_key='secondary')
        self.btn_sync.pack(side='left', padx=8)
        # Generar SEO con IA (desde config)
        self.btn_buscar = create_action_button(self.btn_frame, 'buscar_data', self._on_generar_seo, module='shopify', palette_key='primary')
        self.btn_buscar.pack(side='left', padx=8)
        self._crear_navegacion()

        # Trace category changes to update taxonomy (focusout and selection events)
        try:
            self.cb_categoria.entry.bind('<FocusOut>', lambda e: (self._validate_combo_focus(self.cb_categoria), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_categoria.entry.bind('<<SearchableComboSelected>>', lambda e: (self._on_combo_selected(self.cb_categoria), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_categoria.entry.bind('<Return>', lambda e: (self._validate_combo_focus(self.cb_categoria), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_tipo.entry.bind('<FocusOut>', lambda e: (self._validate_combo_focus(self.cb_tipo), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_tipo.entry.bind('<<SearchableComboSelected>>', lambda e: (self._on_combo_selected(self.cb_tipo), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_tipo.entry.bind('<Return>', lambda e: (self._validate_combo_focus(self.cb_tipo), self._update_taxonomy_from_category(), self._auto_generate_sku()))
            self.cb_proveedor.entry.bind('<FocusOut>', lambda e: self._validate_combo_focus(self.cb_proveedor))
            self.cb_proveedor.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_combo_selected(self.cb_proveedor))
            self.cb_proveedor.entry.bind('<Return>', lambda e: self._validate_combo_focus(self.cb_proveedor))
            self.cb_editorial.entry.bind('<FocusOut>', lambda e: self._validate_editorial())
            self.cb_editorial.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_combo_selected(self.cb_editorial))
            self.cb_editorial.entry.bind('<Return>', lambda e: self._validate_editorial())
        except Exception:
            pass

    def _on_ver_movimientos(self):
        """Abre la subvista de movimientos previo paso por password de admin."""
        if self.producto_id is None:
            ToastWidget.show(self.container, "Guarda el producto primero", tipo='warning')
            return

        from kool_tpv.utils.dialogs import show_password_dialog, show_error
        
        # 1. Autenticación de Admin
        pwd = show_password_dialog(self.container, titulo="ACCESO HISTORIAL", mensaje="Introduce CONTRASEÑA de administrador:")
        if not pwd:
            return
            
        auth = AuthService(self.db)
        valid, user = auth.validate_admin_password(pwd)
        if not valid:
            show_error(self.container, "ERROR", "Contraseña incorrecta o permisos insuficientes")
            return
            
        # 2. Abrir vista via Owner (AlmacenView)
        if self.owner and hasattr(self.owner, 'show_movimientos_producto'):
            self.owner.show_movimientos_producto(self.producto_id)
        else:
            logger.error("No hay referencia al owner o método show_movimientos_producto")

    def _auto_generate_sku(self):
        """Genera automáticamente el SKU si el producto es nuevo y los campos base están presentes."""
        # Solo auto-generar si es un producto nuevo (no tiene producto_id)
        if self.producto_id is not None:
            return

        nombre = self.e_nombre.get().strip()
        cat_nombre = self.cb_categoria._var.get().strip()
        tipo_nombre = self.cb_tipo._var.get().strip()

        # Solo si tenemos los 3 datos clave
        if nombre and cat_nombre and tipo_nombre:
            try:
                # Si el campo SKU está vacío, lo generamos
                current_sku = self.e_sku.get().strip()
                # O si el SKU actual parece ser uno generado anteriormente (podemos ser más agresivos aquí si quieres)
                # Por ahora, solo si está vacío o si quieres que se actualice siempre mientras no se guarde
                
                # Generamos el nuevo SKU
                new_sku = generate_sku(self.db, cat_nombre, tipo_nombre, nombre)
                
                # Actualizamos el campo
                self.e_sku.delete(0, 'end')
                self.e_sku.insert(0, new_sku)
                logger.debug(f"SKU auto-generado: {new_sku}")
            except Exception:
                logging.exception("Error auto-generando SKU")

    def _on_ajustar_stock(self):
        """Orquestador profesional para ajuste manual de stock con seguridad y trazabilidad."""
        if self.producto_id is None:
            ToastWidget.show(self.container, "Guarda el producto antes de ajustar stock", tipo='warning')
            return

        from kool_tpv.utils.dialogs import show_password_dialog, show_input_dialog, show_error
        
        # 1. Autenticación de Usuario
        pwd = show_password_dialog(self.container, titulo="AJUSTE DE STOCK", mensaje="Introduce TU CONTRASEÑA:")
        if not pwd:
            return
            
        auth = AuthService(self.db)
        valid, user = auth.authenticate_user_by_password(pwd)
        if not valid or not user:
            show_error(self.container, "ERROR", "Contraseña incorrecta o usuario no encontrado")
            return
            
        # 2. Cantidad de ajuste
        uds_str = show_input_dialog(self.container, "CANTIDAD", "Unidades (+ para sumar, - para restar):", valor_defecto="0")
        if uds_str is None:
            return
            
        try:
            uds = int(uds_str)
            if uds == 0:
                return
        except ValueError:
            show_error(self.container, "ERROR", "La cantidad debe ser un número entero")
            return
            
        # 3. Motivo
        motivo = show_input_dialog(self.container, "MOTIVO", "Introduce el motivo del ajuste:")
        if not motivo:
            show_error(self.container, "ERROR", "El motivo es obligatorio para la trazabilidad")
            return
            
        # 4. Ejecutar ajuste via Repository (el encargo de sync a Shopify va
        # dentro de la misma transacción: si el ajuste se deshace, desaparece)
        try:
            from kool_tpv.modulos.shopify.services.shopify_sync_service import ShopifySyncService
            sync_svc = ShopifySyncService(self.db)
            with self.db.transaction() as cur:
                if not self.repo.ajustar_stock_manual(self.producto_id, uds, f"Ajuste manual: {motivo}", user['id'], cur=cur):
                    return
            sync_svc.procesar_pendientes_async()

            ToastWidget.show(self.container, "Stock ajustado correctamente", tipo='success')

            # 5. Refrescar UI usando el loader oficial
            try:
                from kool_tpv.modulos.almacen.ui.Productos.cargar_producto import CargarProductoUI
                loader = CargarProductoUI(self.parent, self.db)
                loader.apply_to_ui(self.producto_id, self)
            except Exception:
                logger.exception("Error refrescando UI tras ajuste")
        except Exception:
            show_error(self.container, "ERROR", "No se pudo realizar el ajuste en la base de datos")

    def _add_label_entry(self, parent, label, row, col, colspan, entry_kwargs, lbl_font, placeholder=''):
        ctk.CTkLabel(parent, text=f'{label}:', text_color=self.colors.get('text', COLOR_MATRIX), font=lbl_font).grid(row=row, column=col, sticky='w', padx=6, pady=6)
        ent = ctk.CTkEntry(parent, placeholder_text=placeholder, **entry_kwargs)
        ent.grid(row=row, column=col+1, columnspan=colspan-1, sticky='ew', padx=6, pady=6)
        setattr(self, f'e_{label.lower()}', ent)
        return ent

    def _load_db_options(self):
        try:
            if not self.db:
                logging.info('CrearProductoUI: no se recibió objeto db; cargando valores por defecto')
                # defaults for IVA
                try:
                    self.cb_iva.set_options([(21, '21'), (4, '4')])
                except Exception:
                    pass
                return
            conn = getattr(self.db, 'connection', None)
            if conn is None:
                try:
                    self.db.connect()
                    conn = self.db.connection
                except Exception:
                    logging.exception('CrearProductoUI: fallo conectando con db en _load_db_options')
                    conn = None
            if conn is None:
                logging.info('CrearProductoUI: no hay conexión de DB disponible en _load_db_options')
                return
            # categorias
            try:
                from kool_tpv.modulos.almacen.categoria_repository import (
                    CategoriaRepository,
                )
                cats = CategoriaRepository(self.db).get_all()
                self.cb_categoria.set_options([(int(c['id']), c['nombre'] or '') for c in cats])
                # save mapping for taxonomy
                self._cat_taxonomy = {int(c['id']): (c.get('shopify_taxonomy') or '') for c in cats}
            except Exception:
                logging.exception('Error cargando categorias')
            # tipos
            try:
                from kool_tpv.modulos.almacen.tipo_repository import (
                    TipoRepository,
                )
                tipos = TipoRepository(self.db).get_all()
                self.cb_tipo.set_options([(int(t['id']), t['nombre'] or '') for t in tipos])
                # taxonomy que hereda cada tipo de su categoría asignada
                self._tipo_taxonomy = {
                    int(t['id']): self._cat_taxonomy.get(int(t['categoria_id']), '')
                    for t in tipos if t.get('categoria_id')
                }
            except Exception:
                logging.exception('Error cargando tipos')
            # proveedores
            try:
                from kool_tpv.base_datos.proveedor_service import (
                    ProveedorService,
                )
                provs = ProveedorService(self.db).get_all_proveedores()
                self.cb_proveedor.set_options([(int(p['id']), p['nombre'] or '') for p in provs])
            except Exception:
                logging.exception('Error cargando proveedores')
            # editoriales (tabla editoriales vía servicio)
            try:
                from kool_tpv.modulos.almacen.services.fuentes_editorial_service import (
                    FuentesEditorialService,
                )
                eds = FuentesEditorialService(self.db).listar_editoriales()
                self.cb_editorial.set_options(
                    [(int(e['id']), e['nombre']) for e in eds])
            except Exception:
                logging.exception('Error cargando editoriales')
            # IVA candidates: distinct from productos
            try:
                VALID_IVA_RATES = {0, 4, 10, 21}
                ivs = self.repo.get_tipos_iva() if self.repo else []
                iva_set = {int(v) for v in ivs} | VALID_IVA_RATES
                iva_opts = sorted([(v, str(v)) for v in iva_set])
                self.cb_iva.set_options(iva_opts)
            except Exception:
                logging.exception('Error cargando IVA options')
        except Exception:
            logging.exception('Error en _load_db_options')
        # Refresh Tesoro display after loading options (will use global if no id set)
        try:
            # If we have an ID var, trace it to auto-refresh and call once now
            if getattr(self, 'e_id_var', None) is not None:
                try:
                    # ensure trace only added once
                    try:
                        self.e_id_var.trace_vdelete('w', self._e_id_trace)
                    except Exception:
                        pass
                    self._e_id_trace = self.e_id_var.trace_add('write', lambda *a: self._refresh_tesoro())
                except Exception:
                    pass
            try:
                self._refresh_tesoro()
            except Exception:
                pass
        except Exception:
            pass

    def _update_taxonomy_from_category(self):
        try:
            tax = ''
            cid = self.cb_categoria.get_id()
            if cid and hasattr(self, '_cat_taxonomy'):
                tax = self._cat_taxonomy.get(cid, '')
            # si la categoría del producto no tiene taxonomy, se usa la del tipo
            if not tax:
                tid = self.cb_tipo.get_id()
                if tid and hasattr(self, '_tipo_taxonomy'):
                    tax = self._tipo_taxonomy.get(tid, '')
            # set readonly entry value
            if getattr(self, 'ent_taxonomy', None):
                try:
                    self.ent_taxonomy.configure(state='normal')
                except Exception:
                    pass
                try:
                    self.ent_taxonomy.delete(0, 'end')
                    self.ent_taxonomy.insert(0, tax)
                except Exception:
                    try:
                        self.ent_taxonomy.configure(text=tax)
                    except Exception:
                        pass
                try:
                    self.ent_taxonomy.configure(state='readonly')
                except Exception:
                    pass
        except Exception:
            logging.exception('Error actualizando taxonomy')

    def _validate_combo_focus(self, combo):
        try:
            # If empty, reset border to normal
            val = (combo.get() or '').strip()
            if not val:
                try:
                    combo.entry.configure(border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
                except Exception:
                    pass
                return
            # If value present but no id -> invalid, clear and mark error
            try:
                if combo.get_id() is None:
                    try:
                        combo.entry.configure(border_color=COLOR_ERROR)
                    except Exception:
                        pass
                    try:
                        if hasattr(combo, 'set'):
                            combo.set('')
                        else:
                            combo.entry.delete(0, 'end')
                    except Exception:
                        pass
                else:
                    try:
                        combo.entry.configure(border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _on_combo_selected(self, combo):
        try:
            combo.entry.configure(border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
        except Exception:
            pass

    def _validate_editorial(self):
        """Editorial estricta: si el texto no existe en la tabla editoriales,
        avisa con Toast y limpia el campo."""
        try:
            val = (self.cb_editorial.get() or '').strip()
            if not val:
                self.cb_editorial.entry.configure(
                    border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
                return
            if self.cb_editorial.get_id() is None:
                self.cb_editorial.entry.configure(border_color=COLOR_ERROR)
                self.cb_editorial.set('')
                ToastWidget.show(
                    self.container,
                    f"La editorial '{val}' no existe: dala de alta en EDITORIALES",
                    tipo='error')
            else:
                self.cb_editorial.entry.configure(
                    border_color=self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)))
        except Exception:
            logging.exception('Error validando editorial')

    def _on_gen_barcode_interno(self):
        """Generar código de barras interno e imagen JPG/PNG."""
        try:
            sku = self.e_sku.get().strip()
            nombre = self.e_nombre.get().strip()
            if not sku:
                ToastWidget.show(self.container, "Introduce el SKU primero", tipo='warning')
                return

            # Generar número interno (pasando self.db para asegurar que no se repita)
            nuevo_codigo = barcode_gen_utils.generate_internal_number(db=self.db)
            
            # Generar imagen (usará el nombre para el archivo y para el texto visual)
            path = barcode_gen_utils.generate_barcode_image(nuevo_codigo, sku, nombre=nombre)
            
            if path:
                # Añadir al campo de códigos (si ya hay otros, añadir con coma)
                actual = self.e_codigos.get().strip()
                if actual:
                    if nuevo_codigo not in actual:
                        self.e_codigos.delete(0, 'end')
                        self.e_codigos.insert(0, f"{actual},{nuevo_codigo}")
                else:
                    self.e_codigos.insert(0, nuevo_codigo)
                
                ToastWidget.show(self.container, f"Código {nuevo_codigo} generado", tipo='success')
                logger.info(f"Código interno generado para SKU {sku}: {nuevo_codigo} en {path}")
            else:
                ToastWidget.show(self.container, "Error generando imagen de código", tipo='error')
        except Exception:
            logger.exception("Error en _on_gen_barcode_interno")
            ToastWidget.show(self.container, "Error al generar código interno", tipo='error')

    @staticmethod
    def _links_desde_campo(texto):
        """'url (etiqueta); url2 (etiqueta2)' -> [(etiqueta, url), ...].
        Entrada sin etiqueta -> 'Ficha'."""
        entradas = []
        for trozo in re.split(r'\s*;\s*', texto or ''):
            m = re.match(r'(https?://\S+?)(?:\s*\(([^)]*)\))?\s*$',
                         trozo.strip())
            if m:
                entradas.append((m.group(2) or 'Ficha', m.group(1)))
        return entradas

    def _open_shop_link(self):
        link = (self.e_nombre.get() or '').strip()
        # If shop_link entry exists, prefer it
        try:
            link_ent = getattr(self, 'e_shop_link', None)
            if link_ent:
                link = link_ent.get() or link
        except Exception:
            pass
        if not link:
            return
        entradas = self._links_desde_campo(link)
        if not entradas:
            try:
                webbrowser.open(link)
            except Exception:
                logging.exception('Error abriendo shop link')
            return
        url = entradas[0][1]
        if len(entradas) > 1:
            url = self._elegir_link(entradas)
        if url:
            try:
                webbrowser.open(url)
            except Exception:
                logging.exception('Error abriendo shop link')

    def _elegir_link(self, entradas):
        """Varios links en el campo: diálogo para elegir cuál abrir."""
        try:
            from kool_tpv.utils.dialogs.metaobject_select_dialog import (
                show_reference_select_dialog)
            opciones = [{'id': u, 'text': e, 'family': ''}
                        for e, u in entradas]
            return show_reference_select_dialog(
                self.container, 'ABRIR ENLACE', opciones, None,
                multi_select=False, agrupar=False)
        except Exception:
            logging.exception('Error eligiendo enlace')
            return entradas[0][1]

    def _on_buscar_editorial(self):
        """Abre la búsqueda del tomo en la web de la editorial o Google."""
        try:
            editorial = self.cb_editorial.get().strip()
            nombre = self.e_nombre.get().strip()
            
            if not nombre:
                ToastWidget.show(self.container, "Introduce el nombre del producto", tipo='warning')
                return

            # Por ahora búsqueda en Google con el contexto de la editorial
            query = f"{nombre}"
            if editorial:
                query += f" editorial {editorial}"
            
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            
        except Exception:
            logger.exception("Error en _on_buscar_editorial")

    def _on_obtener(self):
        """Obtiene los datos del producto por EAN en la fuente de la editorial.

        Lee el EAN de CÓDIGOS y la editorial del combo, lanza la búsqueda
        en un hilo (el login del portal tarda) y rellena al volver:
        ORIGINAL, AUTOR, AÑO, TAGS, SINOPSIS y LINK. No pisa lo ya escrito.
        """
        try:
            codes = [c.strip() for c in (self.e_codigos.get() or '').split(',')
                     if c.strip()]
            ean = codes[0] if codes else ''
            editorial = (self.cb_editorial.get() or '').strip()
            nombre = (self.e_nombre.get() or '').strip()

            self.btn_obtener.configure(state='disabled', text='BUSCANDO...')
            ToastWidget.show(self.container, 'Buscando en la fuente...',
                             tipo='info')
            service = ObtenerDatosService(self.db)
            portadas = PortadasService()

            def _run():
                try:
                    datos = service.obtener(editorial, ean, nombre)
                    if isinstance(datos, dict):
                        urls = [datos.get('imagen_url'),
                                *(datos.get('imagenes') or [])]
                        guardadas = portadas.descargar(ean, urls)
                        datos['_imagenes_bajadas'] = len(guardadas)
                        # metacampos: los candidatos estructurados de la fuente
                        # se cotejan con las listas de Shopify (aquí, en el hilo)
                        try:
                            sug = ComparadorMetacamposService(self.db).comparar(
                                datos.get('candidatos_meta') or [])
                            datos['_meta_sugeridos'] = sug.get('metacampos') or {}
                            datos['_meta_pruebas'] = sug.get('pruebas') or []
                        except Exception:
                            logger.exception('Comparador de metacampos falló')
                except Exception as e:
                    datos = e
                try:
                    self.container.after(0, lambda: self._obtener_fin(datos))
                except Exception:
                    pass

            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            logger.exception('Error en _on_obtener')
            try:
                self.btn_obtener.configure(state='normal', text='OBTENER')
            except Exception:
                pass
            ToastWidget.show(self.container, "Error inesperado en OBTENER",
                             tipo='error')

    def _obtener_fin(self, datos):
        """Vuelca la ficha normalizada en los campos (sin pisar lo escrito)."""
        try:
            self.btn_obtener.configure(state='normal', text='OBTENER')
        except Exception:
            pass
        if isinstance(datos, Exception) or not datos:
            msg = str(datos) if datos else 'Sin datos'
            ToastWidget.show(self.container, msg, tipo='error')
            return

        def _fill(entry, value):
            if not value or entry is None:
                return
            try:
                if (entry.get() or '').strip():
                    return
                entry.delete(0, 'end')
                entry.insert(0, str(value))
            except Exception:
                pass

        # ORIGINAL solo si es un título distinto al español (romaji/original);
        # si la fuente repite el mismo título no se rellena
        titulo_orig = (datos.get('titulo_original') or '').strip()
        titulo_esp = (datos.get('titulo') or '').strip()
        if titulo_orig and titulo_orig.lower() != titulo_esp.lower():
            _fill(getattr(self, 'e_nombre_original', None), titulo_orig)
        _fill(getattr(self, 'e_autor', None), datos.get('autor'))
        _fill(getattr(self, 'e_anio', None), datos.get('anio'))
        # metacampos sugeridos por el comparador: solo lo que esté vacío
        for clave, valor in (datos.get('_meta_sugeridos') or {}).items():
            if valor and not (self._metacampos or {}).get(clave):
                self.set_metacampo(clave, valor)
        for prueba in datos.get('_meta_pruebas') or []:
            logger.info('Metacampo sugerido: %s', prueba)
        demog = datos.get('demografia')
        if demog and not (self._metacampos or {}).get('demografia'):
            self.set_metacampo('demografia', demog)
        generos = datos.get('generos') or []
        _fill(getattr(self, 'e_tags', None), ", ".join(generos))
        links = datos.get('links') or []
        if links:
            link_txt = "; ".join(
                f"{l['url']} ({l['etiqueta']})" if l.get('etiqueta')
                else l['url'] for l in links if l.get('url'))
        else:
            link_txt = datos.get('url_ficha')
        _fill(getattr(self, 'e_shop_link', None), link_txt)
        try:
            sinopsis = datos.get('sinopsis') or ''
            txt = getattr(self, 'txt_sinopsis', None)
            if sinopsis and txt is not None:
                actual = txt.get('1.0', 'end-1c').strip()
                if not actual:
                    txt.delete('1.0', 'end')
                    txt.insert('1.0', sinopsis)
        except Exception:
            pass
        n_img = datos.get('_imagenes_bajadas') or 0
        extra = f" · {n_img} imagen(es)" if n_img else ''
        ToastWidget.show(self.container,
                         f'Datos obtenidos de la fuente{extra}',
                         tipo='success')

    def get_widget(self):
        return self.container

    def _validate_strict(self) -> Tuple[bool, str]:
        # Validate required fields and strict comboboxes
        if not (self.e_nombre.get() or '').strip():
            return False, 'Nombre obligatorio'
        # strict comboboxes: category, tipo, proveedor, iva
        combos = [
            ('cb_categoria', 'Categoría'),
            ('cb_tipo', 'Tipo'),
            ('cb_proveedor', 'Proveedor'),
            ('cb_iva', 'IVA'),
        ]
        for attr, label in combos:
            try:
                w = getattr(self, attr, None)
                if w is None:
                    continue
                val = (w.get() or '').strip()
                if not val:
                    try:
                        w.entry.configure(border_color=COLOR_ERROR)
                    except Exception:
                        pass
                    return False, f"{label} obligatorio"
                if w.get_id() is None:
                    # force red border and return descriptive message
                    try:
                        w.entry.configure(border_color=COLOR_ERROR)
                    except Exception:
                        pass
                    return False, f"La {label} '{val}' no existe"
                else:
                    try:
                        w.entry.configure(border_color=self.colors['primary'])
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error validando combo %s', attr)
                return False, f'Error validando {label}'
        # Editorial: no obligatoria, pero si hay texto debe existir en la tabla
        try:
            cb_ed = getattr(self, 'cb_editorial', None)
            if cb_ed is not None:
                ed_val = (cb_ed.get() or '').strip()
                if ed_val and cb_ed.get_id() is None:
                    cb_ed.entry.configure(border_color=COLOR_ERROR)
                    return False, f"La editorial '{ed_val}' no existe"
        except Exception:
            logging.exception('Error validando editorial')
            return False, 'Error validando Editorial'
        return True, ''

    def _on_save(self, despues=None):
        """Guarda el producto. Devuelve True si se guardó. Por defecto vacía el
        formulario al terminar; con `despues` ejecuta eso en su lugar."""
        valid, msg = self._validate_strict()
        if not valid:
            try:
                ToastWidget.show(self.container, msg, tipo='error')
            except Exception:
                logging.error('Validación: %s', msg)
            return

        # Prepare data
        sku = (getattr(self, 'e_sku', None) and self.e_sku.get() or '').strip()
        if not sku:
            try:
                ToastWidget.show(self.container, 'EL SKU ES OBLIGATORIO', tipo='error')
            except Exception:
                logging.error('Validación: El SKU es obligatorio')
            return
        nombre = (self.e_nombre.get() or '').strip()
        nombre_boton = (self.e_nombre_btn.get() or '').strip()
        categoria_id = self.cb_categoria.get_id()
        tipo_id = self.cb_tipo.get_id()
        proveedor_id = self.cb_proveedor.get_id()
        try:
            pvp = float(self.e_pvp.get() or 0)
        except Exception:
            pvp = 0.0
        try:
            coste = float(self.e_coste.get() or 0)
        except Exception:
            coste = 0.0
        # Sanitize decimals: allow comma as decimal separator and empty -> 0.0
        try:
            raw_pvp = (self.e_pvp.get() or '').strip()
            if raw_pvp == '':
                pvp = 0.0
            else:
                pvp = float(raw_pvp.replace(',', '.'))
        except Exception:
            pvp = 0.0
        try:
            raw_coste = (self.e_coste.get() or '').strip()
            if raw_coste == '':
                coste = 0.0
            else:
                coste = float(raw_coste.replace(',', '.'))
        except Exception:
            coste = 0.0
        iva = self.cb_iva.get_id() or 21
        pvp_variable = 1 if getattr(self, 'chk_pvp_var_var', None) and self.chk_pvp_var_var.get() else 0
        try:
            stock_actual = int(self.e_stock_actual.get() or 0)
        except Exception:
            stock_actual = 0
        try:
            stock_min = int(self.e_stock_min.get() or 0)
        except Exception:
            stock_min = 0
        activo = 1 if getattr(self, 'chk_activo_var', None) and self.chk_activo_var.get() else 0
        # shopify taxonomy value from readonly entry
        try:
            shopify_taxonomy = (getattr(self, 'ent_taxonomy', None) and self.ent_taxonomy.get()) or ''
        except Exception:
            shopify_taxonomy = ''

        # capture SEO description and full description textbox contents
        try:
            seo_desc = ''
            if getattr(self, 'e_seo_desc', None):
                try:
                    seo_desc = self.e_seo_desc.get('1.0', 'end-1c').strip()
                except Exception:
                    try:
                        seo_desc = self.e_seo_desc.get().strip()
                    except Exception:
                        seo_desc = ''
        except Exception:
            seo_desc = ''
        try:
            descripcion_full = ''
            if getattr(self, 'txt_description', None):
                try:
                    descripcion_full = self.txt_description.get('1.0', 'end-1c').strip()
                except Exception:
                    try:
                        descripcion_full = self.txt_description.get().strip()
                    except Exception:
                        descripcion_full = ''
        except Exception:
            descripcion_full = ''

        # Campos Shopify adicionales
        try:
            titulo = (getattr(self, 'e_store_title', None) and self.e_store_title.get()) or ''
        except Exception:
            titulo = ''

        try:
            seo_title = (getattr(self, 'e_google_title', None) and self.e_google_title.get()) or ''
        except Exception:
            seo_title = ''

        try:
            tipo_shop = (self.cb_tipo.get() or '').strip()
        except Exception:
            tipo_shop = ''

        try:
            etiquetas = (getattr(self, 'e_tags', None) and self.e_tags.get()) or ''
        except Exception:
            etiquetas = ''

        # notas_internas field removed from UI and DB saving per spec

        try:
            shop_link = (getattr(self, 'e_shop_link', None) and self.e_shop_link.get()) or ''
        except Exception:
            shop_link = ''

        try:
            editorial = (getattr(self, 'cb_editorial', None) and self.cb_editorial.get()) or ''
        except Exception:
            editorial = ''

        try:
            nombre_original = (getattr(self, 'e_nombre_original', None) and self.e_nombre_original.get()) or ''
        except Exception:
            nombre_original = ''

        # Datos técnicos y sinopsis
        try:
            autor = (getattr(self, 'e_autor', None) and self.e_autor.get()) or ''
            anio = (getattr(self, 'e_anio', None) and self.e_anio.get()) or ''

            import json
            tech_dict = {
                'autor': autor,
                'anio': anio,
            }
            metacampos_json = json.dumps(getattr(self, '_metacampos', None) or {}, ensure_ascii=False)
            tech_dict.update(getattr(self, '_tech_extra', None) or {})
            datos_tecnicos = json.dumps(tech_dict)
        except Exception:
            datos_tecnicos = '{}'

        try:
            sinopsis = ''
            if getattr(self, 'txt_sinopsis', None):
                try:
                    sinopsis = self.txt_sinopsis.get('1.0', 'end-1c').strip()
                except Exception:
                    sinopsis = ''
        except Exception:
            sinopsis = ''

        # Guardar producto via Repository (transacción atómica)
        try:
            if self.repo is None:
                raise RuntimeError('Database no disponible')

            # Obtener códigos de barras desde entry CSV
            codes_text = ''
            try:
                if getattr(self, 'e_codigos', None):
                    codes_text = self.e_codigos.get().strip()
            except Exception:
                pass
            codes = [c.strip() for c in (codes_text or '').split(',') if c.strip()]

            fabricado_por_nosotros = 1 if getattr(self, 'chk_fabricado_var', None) and self.chk_fabricado_var.get() else 0
            
            prod_id = self.repo.guardar_producto_completo(
                nombre=nombre,
                nombre_boton=nombre_boton,
                sku=sku,
                categoria_id=categoria_id,
                tipo_id=tipo_id,
                proveedor_id=proveedor_id,
                iva=iva,
                stock_actual=stock_actual,
                stock_min=stock_min,
                activo=activo,
                pvp=pvp,
                coste=coste,
                pvp_variable=pvp_variable,
                fabricado_por_nosotros=fabricado_por_nosotros,
                codigos_barras=codes,
                producto_id=self.producto_id,
                shopify_taxonomy=shopify_taxonomy,
                descripcion_shopify=descripcion_full,
                titulo=titulo,
                seo_title=seo_title,
                seo_description=seo_desc,
                tipo_shop=tipo_shop,
                etiquetas=etiquetas,
                shop_link=shop_link,
                editorial=editorial,
                nombre_original=nombre_original,
                sinopsis=sinopsis,
                datos_tecnicos=datos_tecnicos,
                metacampos=metacampos_json,
            )

            # Actualizar campo ID en UI
            try:
                if getattr(self, 'e_id_var', None) is not None:
                    self.e_id_var.set(str(prod_id))
            except Exception:
                pass
            try:
                self._refresh_tesoro()
            except Exception:
                pass
            ToastWidget.show(self.container, 'Producto guardado correctamente', tipo='success')
            if despues is not None:
                try:
                    despues()
                except Exception:
                    logging.exception('Error en la acción posterior a guardar')
            else:
                # El producto guardado se queda cargado: seguir editándolo o
                # navegar por la lista sin rehacer la búsqueda
                self.producto_id = prod_id
                try:
                    self.marcar_limpio()
                except Exception:
                    pass
            return True

        except Exception:
            logging.exception('Error guardando producto, transacción revertida')
            try:
                ToastWidget.show(self.container, 'NO SE PUDO GUARDAR EL PRODUCTO', tipo='error')
            except Exception:
                pass

    # ---------- navegación por la lista de la búsqueda ----------

    def marcar_limpio(self):
        """Foto del formulario recién cargado, para saber si hay cambios sin guardar."""
        self._foto = self.get_data()

    def _hay_cambios(self) -> bool:
        return self._foto is not None and self.get_data() != self._foto

    def _crear_navegacion(self):
        """ANTERIOR / n de N / SIGUIENTE. Solo si el producto se abrió desde la
        lista de la búsqueda."""
        pos = None
        try:
            if self.owner is not None and self.producto_id is not None:
                pos = self.owner.posicion_en_lista(self.producto_id)
        except Exception:
            logger.exception('Error leyendo la posición en la lista de búsqueda')
        if not pos:
            return
        actual, total = pos
        hay_ant = actual > 1
        hay_sig = actual < total
        try:
            # derecha del pie: SIGUIENTE se empaqueta primero para quedar más a la derecha
            self.btn_siguiente = ButtonFactory.create_button(
                parent=self.btn_frame, text='SIGUIENTE ▶',
                command=lambda: self._ir_a_vecino(1),
                style_key="mini_action", module='almacen', palette_key='secondary')
            self.btn_siguiente.pack(side='right', padx=8)
            self.lbl_posicion = ctk.CTkLabel(
                self.btn_frame, text=f'{actual} de {total}',
                text_color=self.colors['text'], font=get_font('label', module=self.module_name))
            self.lbl_posicion.pack(side='right', padx=8)
            self.btn_anterior = ButtonFactory.create_button(
                parent=self.btn_frame, text='◀ ANTERIOR',
                command=lambda: self._ir_a_vecino(-1),
                style_key="mini_action", module='almacen', palette_key='secondary')
            self.btn_anterior.pack(side='right', padx=8)
            if not hay_ant:
                self.btn_anterior.configure(state='disabled')
            if not hay_sig:
                self.btn_siguiente.configure(state='disabled')
        except Exception:
            logger.exception('Error creando los botones de navegación')

    def _ir_a_vecino(self, paso: int):
        """Cambia al producto anterior (-1) o siguiente (1) de la lista. Si hay
        cambios sin guardar, pregunta si guardar y pasar; solo cambia si se
        guarda bien."""
        destino = self.owner.producto_vecino(self.producto_id, paso)
        if destino is None:
            return
        abrir = lambda: self.owner.show_crear(producto_id=destino, apilar=False)
        if not self._hay_cambios():
            abrir()
            return
        from kool_tpv.utils.dialogs.helpers import show_warning
        sentido = 'siguiente' if paso > 0 else 'anterior'
        if show_warning(self.container, 'Cambios sin guardar',
                        f'¿Guardar el producto y pasar al {sentido}?', confirm=True):
            self._on_save(despues=abrir)

    def _on_cancel(self):
        try:
            # limpiar campos manualmente
            for attr in list(vars(self).keys()):
                if attr.startswith('e_') or attr.startswith('cb_') or attr.startswith('txt_'):
                    # Prefer clearing an associated variable if present (e.g., e_ventas_var)
                    try:
                        var_name = f"{attr}_var"
                        if hasattr(self, var_name):
                            var = getattr(self, var_name)
                            try:
                                if hasattr(var, 'set'):
                                    var.set('')
                                    continue
                            except Exception:
                                pass
                    except Exception:
                        pass
                    w = getattr(self, attr)
                    try:
                        if hasattr(w, 'delete'):
                            if isinstance(w, SearchableCombo):
                                w.set('')
                            else:
                                try:
                                    w.delete(0, 'end')
                                except Exception:
                                    # readonly entries may not allow delete; try configure or variable
                                    try:
                                        w.configure(text='')
                                    except Exception:
                                        pass
                        elif hasattr(w, 'configure'):
                            w.configure(text='')
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error en _on_cancel CrearProductoUI')
        try:
            self._metacampos = {}
            self._refrescar_meta_entries()
        except Exception:
            pass

    # ---------- metacampos de cómic (Shopify) ----------

    # clave metacampo -> atributo del campo de solo lectura
    _META_ENTRIES = (
        ('demografia', 'e_meta_demografia'),
        ('genero_comic', 'e_meta_genero'),
        ('subgenero_comic', 'e_meta_subgenero'),
        ('contenido_adultos', 'e_meta_contenido'),
    )

    def _crear_meta_entry(self, placeholder, parent=None):
        """Campo de solo lectura que muestra los nombres elegidos (como TAXONOMY)."""
        contenedor = parent or self.shopify_frame
        try:
            return ctk.CTkEntry(
                contenedor, placeholder_text=placeholder, state='readonly',
                fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
                text_color=self._shop_primary, border_width=2,
                border_color=self._shop_primary,
                corner_radius=4)
        except Exception:
            e = ctk.CTkEntry(contenedor, placeholder_text=placeholder)
            try:
                e.configure(state='readonly')
            except Exception:
                pass
            return e

    def _set_meta_entry(self, entry, texto):
        """Escribe en un campo readonly: habilita, rellena y vuelve a bloquear."""
        try:
            entry.configure(state='normal')
            entry.delete(0, 'end')
            if texto:
                entry.insert(0, texto)
            entry.configure(state='readonly')
        except Exception:
            pass

    def _refrescar_meta_entries(self):
        """Vuelca self._metacampos en los 4 campos visibles."""
        datos = self._metacampos or {}
        for clave, attr in self._META_ENTRIES:
            entry = getattr(self, attr, None)
            if entry is None:
                continue
            v = datos.get(clave)
            texto = ', '.join(v) if isinstance(v, list) else (v or '')
            self._set_meta_entry(entry, texto)

    def set_metacampos(self, datos):
        """Carga el dict de metacampos (al abrir un producto)."""
        self._metacampos = dict(datos or {})
        self._refrescar_meta_entries()

    def set_metacampo(self, clave, valor):
        """Pone un valor por código (OBTENER, demografía antigua)."""
        if self._metacampos is None:
            self._metacampos = {}
        if valor:
            self._metacampos[clave] = valor
        else:
            self._metacampos.pop(clave, None)
        self._refrescar_meta_entries()

    def _on_metacampos_click(self):
        """UN botón: baja las 4 listas de Shopify y reparte lo elegido en sus cajas."""
        if self.db is None:
            return
        try:
            ToastWidget.show(self.container, 'Cargando metacampos de Shopify…', tipo='info')
        except Exception:
            pass

        def work():
            svc = None
            try:
                svc = MetacamposComicService(self.db)
                opciones, err = svc.obtener_opciones()
            except Exception as e:
                opciones, err = None, str(e)
            try:
                self.container.after(0, lambda: self._mostrar_selector_metacampos(svc, opciones, err))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _mostrar_selector_metacampos(self, svc, opciones, err):
        if err or not opciones:
            ToastWidget.show(self.container, err or 'No se pudieron cargar los metacampos', tipo='error')
            return
        # preselección: nombres guardados -> GIDs
        seleccion = {}
        for clave, grupo in opciones.items():
            almacenado = (self._metacampos or {}).get(clave)
            nombres = almacenado if isinstance(almacenado, list) else ([almacenado] if almacenado else [])
            seleccion[grupo['titulo']] = svc.gids_de_nombres(grupo['entradas'], nombres)
        grupos_dialogo = [
            {'titulo': g['titulo'], 'unico': g['unico'],
             'opciones': [{'id': e['gid'], 'text': e['nombre']} for e in g['entradas']]}
            for g in opciones.values()
        ]
        resultado = show_metacampos_agrupados_dialog(
            self.container, 'METACAMPOS', grupos_dialogo, seleccion)
        if resultado is None:
            return
        for clave, grupo in opciones.items():
            nombres = svc.nombres_de_gids(grupo['entradas'], resultado.get(grupo['titulo']) or [])
            if grupo['unico']:
                if nombres:
                    self._metacampos[clave] = nombres[0]
                else:
                    self._metacampos.pop(clave, None)
            elif nombres:
                self._metacampos[clave] = nombres
            else:
                self._metacampos.pop(clave, None)
        self._refrescar_meta_entries()

    def _focus_next_widget(self, event):
        try:
            nxt = event.widget.tk_focusNext()
            if nxt:
                try:
                    nxt.focus_set()
                except Exception:
                    try:
                        nxt.focus()
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error moviendo foco al siguiente widget')
        return 'break'

    def _focus_to_guardar(self, event):
        try:
            if getattr(self, 'btn_guardar', None):
                try:
                    self.btn_guardar.focus_set()
                except Exception:
                    try:
                        self.btn_guardar.focus()
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error moviendo foco a Guardar')
        return 'break'

    def _refresh_tesoro(self, *args):
        try:
            # Determine product id from entry var if present
            pid = None
            try:
                if getattr(self, 'e_id_var', None) is not None:
                    idtxt = (self.e_id_var.get() or '').strip()
                    try:
                        logging.info("TESORO DEBUG - e_id_var = %s", self.e_id_var.get())
                    except Exception:
                        logging.info("TESORO DEBUG - e_id_var = <error getting var>")
                    if idtxt:
                        try:
                            pid = int(idtxt)
                        except Exception:
                            pid = None
                    try:
                        logging.info("TESORO DEBUG - pid = %s", pid)
                    except Exception:
                        logging.info("TESORO DEBUG - pid = <error computing pid>")
            except Exception:
                pid = None

            # Default display
            display = 'Tesoro: -'

            if pid and getattr(self, 'db', None):
                try:
                    from kool_tpv.modulos.fidelizacion.fidelizacion_service import FidelizacionService
                    fs = FidelizacionService(self.db)
                    cfg = fs.obtener_fidelizacion_producto(pid)
                    if cfg:
                        tipo = cfg.get('tipo', 'porcentaje')
                        valor = cfg.get('valor')
                        if tipo == 'fijo':
                            display = f"Tesoro: {valor} €"
                        else:
                            display = f"Tesoro: {valor}%"
                except Exception:
                    try:
                        from kool_tpv.base_datos.configuracion_service import ConfiguracionService
                        cs = ConfiguracionService(self.db)
                        gp = cs.get_fide_porcentaje_global()
                        display = f"Tesoro: {gp}%"
                    except Exception:
                        display = 'Tesoro: -'
            else:
                # No id -> show global
                try:
                    from kool_tpv.base_datos.configuracion_service import ConfiguracionService
                    cs = ConfiguracionService(self.db)
                    gp = cs.get_fide_porcentaje_global()
                    display = f"Tesoro: {gp}%"
                except Exception:
                    display = 'Tesoro: -'

            try:
                if getattr(self, 'lbl_tesoro_var', None) is not None:
                    self.lbl_tesoro_var.set(display)
                elif getattr(self, 'lbl_tesoro', None) is not None:
                    try:
                        self.lbl_tesoro.configure(text=display)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error refrescando tesoro')

    def _on_sync(self):
        """SUBIR A SHOPIFY: crea o actualiza la ficha web del producto (activo)."""
        try:
            pid_txt = (self.e_id_var.get() or '').strip() if getattr(self, 'e_id_var', None) else ''
            pid = int(pid_txt) if pid_txt else 0
        except (ValueError, TypeError):
            pid = 0
        if not pid:
            ToastWidget.show(self.container, 'Guarda el producto antes de subirlo a Shopify', tipo='warning')
            return
        if self._hay_cambios():
            ToastWidget.show(self.container, 'Guarda los cambios antes de subir', tipo='warning')
            return
        form = self.get_data()

        def work():
            try:
                from kool_tpv.modulos.shopify.services.shopify_ficha_service import ShopifyFichaService
                svc = ShopifyFichaService(self.db)
                estado = svc.estado_subida(pid)
                existente = None
                if not estado['mapeado']:
                    ean = svc._primer_ean(form.get('codigos_barras'))
                    if ean:
                        existente = svc.buscar_por_ean(ean)
                self.container.after(0, lambda: self._confirmar_y_subir(
                    pid, form, existente, estado['mapeado']))
            except Exception:
                logging.exception('Error comprobando producto en Shopify')
                self.container.after(0, lambda: ToastWidget.show(
                    self.container, 'Error comprobando Shopify', tipo='error'))

        ToastWidget.show(self.container, 'Comprobando Shopify…', tipo='info')
        threading.Thread(target=work, daemon=True).start()

    def _confirmar_y_subir(self, pid, form, existente, mapeado):
        """Si el EAN ya existe en Shopify se pide permiso para enlazarlo."""
        shopify_id = None
        if existente:
            from kool_tpv.utils.dialogs import show_warning
            ok = show_warning(
                self.container, 'YA EXISTE EN SHOPIFY',
                f"El EAN ya lo usa '{existente.get('title')}' ({existente.get('status')}).\n"
                '¿Actualizar ese producto y enlazarlo con esta ficha?',
                confirm=True)
            if not ok:
                return
            shopify_id = existente.get('id')
        es_nuevo = not mapeado and not shopify_id
        self._subir_a_shopify(pid, form, shopify_id, es_nuevo)

    def _subir_a_shopify(self, pid, form, shopify_id, es_nuevo):
        def work():
            try:
                from kool_tpv.modulos.shopify.services.shopify_ficha_service import ShopifyFichaService
                res = ShopifyFichaService(self.db).subir(
                    pid, form, 'ACTIVE', shopify_id_confirmado=shopify_id)
                self.container.after(0, lambda: self._on_subida_lista(res, es_nuevo, form))
            except Exception:
                logging.exception('Error subiendo producto a Shopify')
                self.container.after(0, lambda: self._on_subida_lista(
                    {'success': False, 'message': 'Error inesperado (ver log)'}))

        ToastWidget.show(self.container, 'Subiendo a Shopify…', tipo='info')
        threading.Thread(target=work, daemon=True).start()

    def _on_subida_lista(self, res, es_nuevo=False, form=None):
        from kool_tpv.utils.dialogs import show_error
        if res.get('success'):
            if res.get('url') and getattr(self, 'e_shop_link', None):
                self.e_shop_link.delete(0, 'end')
                self.e_shop_link.insert(0, res['url'])
                if self._foto is not None:
                    self._foto['shop_link'] = res['url']
            if res.get('stock_ok', True):
                ToastWidget.show(self.container, 'Subido a Shopify', tipo='success')
            else:
                show_error(self.container, 'SUBIDO SIN STOCK',
                           f"El producto subió pero el stock falló:\n{res.get('stock_error') or ''}")
            if es_nuevo:
                self._buscar_duplicados(form or {}, res.get('product_id'))
        else:
            show_error(self.container, 'ERROR SUBIENDO', res.get('message') or 'Error desconocido')

    def _buscar_duplicados(self, form, producto_nuevo_id):
        """Tras crear un producto nuevo: busca duplicados antiguos por título."""
        titulo = (form.get('titulo') or form.get('nombre') or '').strip()
        if not titulo:
            return

        def work():
            try:
                from kool_tpv.modulos.shopify.services.shopify_ficha_service import ShopifyFichaService
                dups = ShopifyFichaService(self.db).buscar_duplicados(
                    titulo, excluir_id=producto_nuevo_id)
                self.container.after(0, lambda: self._mostrar_duplicados(dups))
            except Exception:
                logging.exception('Error buscando duplicados en Shopify')

        threading.Thread(target=work, daemon=True).start()

    def _mostrar_duplicados(self, dups):
        """Diálogo con checkboxes: el usuario marca los duplicados a borrar."""
        if not dups:
            return
        from kool_tpv.utils.dialogs.metaobject_select_dialog import show_reference_select_dialog
        opciones = [{
            'id': p['id'],
            'text': f"{p.get('title')}  ·  {p.get('status')}  ·  "
                    f"{(p.get('createdAt') or '')[:10]}  ·  "
                    f"sku: {', '.join(v.get('sku') or '-' for v in p.get('variants', {}).get('nodes', []))}",
            'family': p.get('productType') or 'Sin tipo',
        } for p in dups]
        marcados = show_reference_select_dialog(
            self.container, 'POSIBLES DUPLICADOS EN SHOPIFY',
            opciones, [], multi_select=True, columnas=1)
        if not marcados:
            return
        from kool_tpv.utils.dialogs import show_warning
        ok = show_warning(
            self.container, 'BORRAR DUPLICADOS',
            f'¿Borrar {len(marcados)} producto(s) de Shopify?\nEsta acción NO se puede deshacer.',
            confirm=True)
        if not ok:
            return

        def work():
            try:
                from kool_tpv.modulos.shopify.services.shopify_ficha_service import ShopifyFichaService
                res = ShopifyFichaService(self.db).borrar_productos(marcados)
                self.container.after(0, lambda: self._on_duplicados_borrados(res))
            except Exception:
                logging.exception('Error borrando duplicados en Shopify')
                self.container.after(0, lambda: ToastWidget.show(
                    self.container, 'Error borrando duplicados', tipo='error'))

        ToastWidget.show(self.container, 'Borrando duplicados…', tipo='info')
        threading.Thread(target=work, daemon=True).start()

    def _on_duplicados_borrados(self, res):
        n = len(res.get('borrados') or [])
        errores = res.get('errores') or []
        if n and not errores:
            ToastWidget.show(self.container, f'{n} duplicado(s) borrado(s)', tipo='success')
        elif n:
            ToastWidget.show(
                self.container, f'{n} borrados, {len(errores)} con error (ver log)', tipo='warning')
        else:
            from kool_tpv.utils.dialogs import show_error
            show_error(self.container, 'SIN BORRAR',
                       'No se pudo borrar ningún duplicado (ver log)')

    def _on_generar_seo(self):
        """GENERAR SEO: envía los datos del formulario a la IA y rellena los campos SEO."""
        try:
            nombre = (self.e_nombre.get() or '').strip()
            if not nombre:
                ToastWidget.show(self.container, "Introduce un nombre para generar SEO", tipo='warning')
                return

            mc = self._metacampos or {}
            def _meta_txt(v):
                return ", ".join(map(str, v)) if isinstance(v, list) else str(v or '')

            codigos = (self.e_codigos.get() or '').split(',')
            datos = {
                'tipo_id': self.cb_tipo.get_id(),
                'tipo_producto': (self.cb_tipo.get() or '').strip(),
                'product_name': nombre,
                'author': (getattr(self, 'e_autor', None) and self.e_autor.get() or '').strip(),
                'publisher': (getattr(self, 'cb_editorial', None) and self.cb_editorial.get() or '').strip(),
                'isbn': codigos[0].strip() if codigos and codigos[0].strip() else '',
                'demografia': _meta_txt(mc.get('demografia')),
                'generos': _meta_txt(mc.get('genero_comic')),
                'subgeneros': _meta_txt(mc.get('subgenero_comic')),
                'contenido': _meta_txt(mc.get('contenido_adultos')),
                'tags_actuales': (getattr(self, 'e_tags', None) and self.e_tags.get() or '').strip(),
                'sinopsis': (self.txt_sinopsis.get('1.0', 'end-1c') or '').strip()
                            if getattr(self, 'txt_sinopsis', None) else '',
            }

            self.btn_buscar.configure(state='disabled')
            ToastWidget.show(self.container, 'Generando SEO con IA...', tipo='info')

            def _run():
                try:
                    res, err = SeoFichaService(self.db).generar(datos)
                except Exception as e:
                    logger.exception('Error generando SEO')
                    res, err = None, str(e)
                self.container.after(0, lambda r=res, e=err: self._seo_fin(r, e))

            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            logger.exception('Error en _on_generar_seo')
            ToastWidget.show(self.container, "Error inesperado generando SEO", tipo='error')
            self.btn_buscar.configure(state='normal')

    @staticmethod
    def _seo_set(widget, valor):
        """Escribe en un campo Entry o Textbox, sea cual sea."""
        if widget is None or not valor:
            return
        try:
            widget.delete('1.0', 'end')
            widget.insert('1.0', str(valor))
        except Exception:
            try:
                widget.delete(0, 'end')
                widget.insert(0, str(valor))
            except Exception:
                pass

    def _seo_fin(self, res, err):
        self.btn_buscar.configure(state='normal')
        if err or not res:
            ToastWidget.show(self.container, err or "La IA no devolvió datos", tipo='error')
            return
        self._seo_set(getattr(self, 'e_store_title', None), res.get('titulo'))
        self._seo_set(getattr(self, 'e_google_title', None), res.get('seo_title'))
        self._seo_set(getattr(self, 'e_seo_desc', None), res.get('seo_description'))
        self._seo_set(getattr(self, 'txt_description', None), res.get('description'))
        self._seo_set(getattr(self, 'e_tags', None), res.get('tags'))
        ToastWidget.show(self.container, "SEO generado", tipo='success')

    def get_data(self) -> Dict[str, str]:
        try:
            return {
                'nombre': (self.e_nombre.get() or '').strip(),
                'nombre_boton': (self.e_nombre_btn.get() or '').strip(),
                'sku': (getattr(self, 'e_sku', None) and self.e_sku.get()) or '',
                'categoria_id': self.cb_categoria.get_id(),
                'tipo_id': self.cb_tipo.get_id(),
                'proveedor_id': self.cb_proveedor.get_id(),
                'pvp': (self.e_pvp.get() or '').strip(),
                'coste': (self.e_coste.get() or '').strip(),
                'iva': self.cb_iva.get(),
                'pvp_variable': bool(self.chk_pvp_var.get()),
                'stock_actual': (getattr(self, 'e_stock_actual', None) and self.e_stock_actual.get()) or '0',
                'stock_min': (getattr(self, 'e_stock_min', None) and self.e_stock_min.get()) or '0',
                'shopify_taxonomy': (getattr(self, 'ent_taxonomy', None) and self.ent_taxonomy.get()) or '',
                'titulo': (getattr(self, 'e_store_title', None) and self.e_store_title.get()) or '',
                'seo_title': (getattr(self, 'e_google_title', None) and self.e_google_title.get()) or '',
                'seo_description': (lambda: (
                    (lambda txt: txt.strip())(
                        (self.e_seo_desc.get('1.0', 'end-1c') if getattr(self, 'e_seo_desc', None) and hasattr(self.e_seo_desc, 'get') else (self.e_seo_desc.get() if getattr(self, 'e_seo_desc', None) and hasattr(self.e_seo_desc, 'get') else ''))
                    )
                ))(),
                'descripcion_shopify': (lambda: (
                    (lambda txt: txt.strip())(
                        (self.txt_description.get('1.0', 'end-1c') if getattr(self, 'txt_description', None) and hasattr(self.txt_description, 'get') else (self.txt_description.get() if getattr(self, 'txt_description', None) and hasattr(self.txt_description, 'get') else ''))
                    )
                ))(),
                'tipo_shop': (self.cb_tipo.get() or '').strip(),
                'etiquetas': (getattr(self, 'e_tags', None) and self.e_tags.get()) or '',
                'shop_link': (getattr(self, 'e_shop_link', None) and self.e_shop_link.get()) or '',
                'editorial': (getattr(self, 'cb_editorial', None) and self.cb_editorial.get()) or '',
                'nombre_original': (getattr(self, 'e_nombre_original', None) and self.e_nombre_original.get()) or '',
                'autor': (getattr(self, 'e_autor', None) and self.e_autor.get()) or '',
                'anio': (getattr(self, 'e_anio', None) and self.e_anio.get()) or '',
                'metacampos': (lambda: (
                    __import__('json').dumps(getattr(self, '_metacampos', None) or {}, sort_keys=True, ensure_ascii=False)
                ))(),
                'sinopsis': (lambda: (
                    (lambda txt: txt.strip())(
                        (self.txt_sinopsis.get('1.0', 'end-1c') if getattr(self, 'txt_sinopsis', None) and hasattr(self.txt_sinopsis, 'get') else '')
                    )
                ))(),
                'codigos_barras': (getattr(self, 'e_codigos', None) and (self.e_codigos.get() or '').strip()) or '',
            }
        except Exception:
            logging.exception('Error obteniendo datos CrearProductoUI')
            return {}

