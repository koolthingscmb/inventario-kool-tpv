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
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.utils import barcode_gen_utils

logger = logging.getLogger(__name__)




class CrearProductoUI:
    def __init__(self, parent, db: Optional[object] = None, producto_id: Optional[int] = None, module_name: str = 'almacen'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.producto_id = producto_id
        self.repo = ProductoRepository(db) if db is not None else None
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'accent': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL, 'light': '#666666'}
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))

        # Header removed: breadcrumb is provided by BaseModuleView

        # Build stacked frames: GENERAL above SHOPIFY (no TabView)
        self.general_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.general_frame.pack(fill='both', expand=False, padx=12, pady=8)

        self.shopify_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.shopify_frame.pack(fill='both', expand=True, padx=12, pady=(0, 8))
        # Common styles
        lbl_font = get_font('label', module=self.module_name)
        entry_kwargs = {"fg_color": self.colors.get('background', COLOR_BG_TERMINAL), "text_color": self.colors['text'], "border_width": 2, "border_color": self.colors.get('border', self.colors.get('primary', COLOR_MATRIX)), "corner_radius": 4}

        # Build GENERAL frame with 8-column grid (7 filas requeridas)
        for c in range(8):
            self.general_frame.grid_columnconfigure(c, weight=1, uniform='col')

        # Fila 1: ID (2 col block) | NOMBRE (6 col block)
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
        self.e_id.grid(row=0, column=1, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="NOMBRE:", text_color=self.colors['text'], font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.general_frame, placeholder_text="Nombre del producto", **entry_kwargs)
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 2: SKU (4 col) | NOMBRE_BOTON (4 col)
        ctk.CTkLabel(self.general_frame, text="SKU:", text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_sku = ctk.CTkEntry(self.general_frame, placeholder_text='SKU', **entry_kwargs)
        self.e_sku.grid(row=1, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="NOMBRE_BOTON:", text_color=self.colors['text'], font=lbl_font).grid(row=1, column=4, sticky='w', padx=6, pady=6)
        self.e_nombre_btn = ctk.CTkEntry(self.general_frame, placeholder_text='Texto botón', **entry_kwargs)
        self.e_nombre_btn.grid(row=1, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 3: CATEGORIA | TIPO | PROVEEDOR (distribuidos)
        ctk.CTkLabel(self.general_frame, text="CATEGORÍA:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.cb_categoria = SearchableCombo(self.general_frame, placeholder='Buscar categoría')
        self.cb_categoria.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="TIPO:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=3, sticky='w', padx=6, pady=6)
        self.cb_tipo = SearchableCombo(self.general_frame, placeholder='Buscar tipo')
        self.cb_tipo.grid(row=2, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="PROVEEDOR:", text_color=self.colors['text'], font=lbl_font).grid(row=2, column=6, sticky='w', padx=6, pady=6)
        self.cb_proveedor = SearchableCombo(self.general_frame, placeholder='Buscar proveedor')
        self.cb_proveedor.grid(row=2, column=7, sticky='ew', padx=6, pady=6)

        # Fila 4: PVP (4 col) | COSTE (4 col)
        ctk.CTkLabel(self.general_frame, text="PVP:", text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_pvp = ctk.CTkEntry(self.general_frame, placeholder_text='0.00', **entry_kwargs)
        self.e_pvp.grid(row=3, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="COSTE:", text_color=self.colors['text'], font=lbl_font).grid(row=3, column=4, sticky='w', padx=6, pady=6)
        self.e_coste = ctk.CTkEntry(self.general_frame, placeholder_text='0.00', **entry_kwargs)
        self.e_coste.grid(row=3, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 5: TIPO_IVA (4 col) | PVP_VARIABLE (4 col)
        ctk.CTkLabel(self.general_frame, text="TIPO_IVA:", text_color=self.colors['text'], font=lbl_font).grid(row=4, column=0, sticky='w', padx=6, pady=6)
        self.cb_iva = SearchableCombo(self.general_frame, placeholder='IVA (ej: 21)')
        self.cb_iva.grid(row=4, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        # Variable para PVP_VARIABLE
        self.chk_pvp_var_var = tk.BooleanVar(value=False)

        ctk.CTkLabel(self.general_frame, text="PVP_VARIABLE:", text_color=self.colors['text'], font=lbl_font).grid(row=4, column=4, sticky='w', padx=6, pady=6)
        self.chk_pvp_var = ctk.CTkCheckBox(self.general_frame, text='', variable=self.chk_pvp_var_var, fg_color=self.colors['secondary'])
        self.chk_pvp_var.grid(row=4, column=5, columnspan=3, sticky='w', padx=6, pady=6)

        # Fila 6: STOCK_ACTUAL (4 col) | STOCK_MINIMO (4 col)
        ctk.CTkLabel(self.general_frame, text="STOCK_ACTUAL:", text_color=self.colors['text'], font=lbl_font).grid(row=5, column=0, sticky='w', padx=6, pady=6)
        self.e_stock_actual = ctk.CTkEntry(self.general_frame, placeholder_text='0', **entry_kwargs)
        self.e_stock_actual.grid(row=5, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.general_frame, text="STOCK_MINIMO:", text_color=self.colors['text'], font=lbl_font).grid(row=5, column=4, sticky='w', padx=6, pady=6)
        self.e_stock_min = ctk.CTkEntry(self.general_frame, placeholder_text='0', **entry_kwargs)
        self.e_stock_min.grid(row=5, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 7: VENTAS (read-only 4 col) | ESTADO (4 col)
        ctk.CTkLabel(self.general_frame, text="VENTAS:", text_color=self.colors['text'], font=lbl_font).grid(row=6, column=0, sticky='w', padx=6, pady=6)
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
        self.e_ventas.grid(row=6, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        # Use a BooleanVar to track activo state
        self.chk_activo_var = tk.BooleanVar(value=True)

        # Place a small container in the same grid cell to hold the 'Activo' label and the checkbox
        try:
            self._activo_frame = ctk.CTkFrame(self.general_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
            self._activo_frame.grid(row=6, column=5, columnspan=2, sticky='w', padx=6, pady=6)
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
                ctk.CTkLabel(self.general_frame, text='Activo', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=5, sticky='w', padx=6, pady=6)
            except Exception:
                try:
                    tk.Label(self.general_frame, text='Activo').grid(row=6, column=5, sticky='w', padx=6, pady=6)
                except Exception:
                    pass
            try:
                self.chk_activo = ctk.CTkCheckBox(self.general_frame, text='Producto activo', variable=self.chk_activo_var, fg_color=self.colors['secondary'], text_color=self.colors['secondary'])
                self.chk_activo.grid(row=6, column=6, columnspan=1, sticky='w', padx=6, pady=6)
            except Exception:
                try:
                    self.chk_activo = tk.Checkbutton(self.general_frame, text='Producto activo', variable=self.chk_activo_var)
                    self.chk_activo.grid(row=6, column=6, columnspan=1, sticky='w', padx=6, pady=6)
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
        self.lbl_tesoro.grid(row=6, column=7, sticky='w', padx=6, pady=6)

        # Fila 8: CÓDIGOS_DE_BARRAS (CSV separado por comas)
        lbl_barras = ctk.CTkLabel(self.general_frame, text="CÓDIGOS_DE_BARRAS (CSV):", text_color=self.colors['text'], font=lbl_font)
        lbl_barras.grid(row=7, column=0, sticky='w', padx=6, pady=6, columnspan=4)
        
        # Botón para generar código interno ⭐
        try:
            self.btn_gen_barcode = ButtonFactory.create_button(
                parent=self.general_frame,
                text='BARRAS',
                command=self._on_gen_barcode_interno,
                style_key="mini_action"
            )
            self.btn_gen_barcode.grid(row=7, column=4, columnspan=4, sticky='e', padx=6, pady=6)
        except Exception:
            logger.exception('Error creando botón BARRAS')

        try:
            self.e_codigos = ctk.CTkEntry(self.general_frame, placeholder_text='ean1,ean2,ean3', **entry_kwargs)
        except Exception:
            self.e_codigos = tk.Entry(self.general_frame)
        self.e_codigos.grid(row=8, column=0, columnspan=8, sticky='nsew', padx=6, pady=6)

        # Label separator for Shopify section (highlighted in yellow)
        ctk.CTkLabel(self.general_frame, text='SHOPIFY', text_color=self.colors['secondary'], font=lbl_font).grid(row=9, column=0, columnspan=8, sticky='w', padx=6, pady=(12, 6))

        # Load options from DB if available
        self._load_db_options()

        # SHOPIFY tab: 6 filas, un campo por fila máximo orden
        for c in range(8):
            self.shopify_frame.grid_columnconfigure(c, weight=1, uniform='col')

        # Fila 1: TITULO (Label + Entry, 8 col)
        ctk.CTkLabel(self.shopify_frame, text='TITULO:', text_color=self.colors['text'], font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_seo_title = ctk.CTkEntry(self.shopify_frame, placeholder_text='Título web', **entry_kwargs)
        self.e_seo_title.grid(row=0, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 2: LINK (Label + Entry + Botón IR)
        ctk.CTkLabel(self.shopify_frame, text='LINK:', text_color=self.colors['text'], font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_shop_link = ctk.CTkEntry(self.shopify_frame, placeholder_text='https://…', **entry_kwargs)
        self.e_shop_link.grid(row=1, column=1, columnspan=6, sticky='ew', padx=6, pady=6)
        # IR button: prefer palette settings from colors_config.json
        btn_cfg = self.colors.get('buttons', {}).get('primary', {})
        btn_bg = btn_cfg.get('bg', self.colors.get('primary', '#3498db'))
        btn_hover = btn_cfg.get('hover', btn_bg)
        btn_text = btn_cfg.get('text', self.colors.get('text'))
        try:
            ButtonFactory.create_button(
                parent=self.shopify_frame,
                text='IR',
                command=self._open_shop_link,
                style_key="mini_action"
            ).grid(row=1, column=7, sticky='ew', padx=6, pady=6)
        except Exception:
            try:
                ButtonFactory.create_button(
                    parent=self.shopify_frame,
                    text='IR',
                    command=self._open_shop_link,
                    style_key="mini_action"
                ).grid(row=1, column=7, sticky='ew', padx=6, pady=6)
            except Exception:
                pass

        # Fila 3: TAXONOMY (static vinculado, 4 col) | TIPO_SHOP (label+entry, 4 col)
        ctk.CTkLabel(self.shopify_frame, text='TAXONOMY:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        # Readonly entry to allow selection/copy but prevent manual edits
        try:
            self.ent_taxonomy = ctk.CTkEntry(self.shopify_frame, placeholder_text='', state='readonly', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors['light'], border_width=2, border_color=self.colors.get('border', self.colors.get('secondary', COLOR_MATRIX)), corner_radius=4)
        except Exception:
            # fallback if customtkinter does not support readonly state
            self.ent_taxonomy = ctk.CTkEntry(self.shopify_frame, placeholder_text='', fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors['light'], border_width=2, border_color=self.colors['secondary'], corner_radius=4)
            try:
                self.ent_taxonomy.configure(state='readonly')
            except Exception:
                pass
        # Make taxonomy wider (occupy 2 columns) and expand horizontally
        self.ent_taxonomy.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.shopify_frame, text='TIPO_SHOP:', text_color=self.colors['text'], font=lbl_font).grid(row=2, column=4, sticky='w', padx=6, pady=6)
        self.e_tipo_shop = ctk.CTkEntry(self.shopify_frame, placeholder_text='Tipo shop', **entry_kwargs)
        self.e_tipo_shop.grid(row=2, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 4: TAGS (ocupa toda la fila, 8 columnas)
        ctk.CTkLabel(self.shopify_frame, text='TAGS:', text_color=self.colors['text'], font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_tags = ctk.CTkEntry(self.shopify_frame, placeholder_text='tag1, tag2', **entry_kwargs)
        self.e_tags.grid(row=3, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 5: SEO_TITLE (Label + Entry, 8 col)
        ctk.CTkLabel(self.shopify_frame, text='SEO_TITLE:', text_color=self.colors['text'], font=lbl_font).grid(row=4, column=0, sticky='w', padx=6, pady=6)
        self.e_seo_short = ctk.CTkEntry(self.shopify_frame, placeholder_text='SEO short title', **entry_kwargs)
        self.e_seo_short.grid(row=4, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 6: SEO_DESCRIPTION (CTkTextbox, altura menor 80px, 8 col)
        ctk.CTkLabel(self.shopify_frame, text='SEO_DESCRIPTION:', text_color=self.colors['text'], font=lbl_font).grid(row=5, column=0, sticky='nw', padx=6, pady=6)
        try:
            self.e_seo_desc = ctk.CTkTextbox(self.shopify_frame, width=800, height=80, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors['light'], border_width=2, border_color=self.colors.get('border', self.colors.get('secondary', COLOR_MATRIX)))
            self.e_seo_desc.grid(row=5, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)
            try:
                # make Tab move to next widget instead of inserting a tab character
                self.e_seo_desc.bind('<Tab>', lambda e: self._focus_next_widget(e))
            except Exception:
                pass
        except Exception:
            # fallback: wrap tk.Text in a framed CTkFrame to simulate border
            frame = ctk.CTkFrame(self.shopify_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), border_width=2, border_color=self.colors.get('border', self.colors.get('secondary', COLOR_MATRIX)))
            self.e_seo_desc = tk.Text(frame, bg=self.colors.get('background', COLOR_BG_TERMINAL), fg=self.colors['light'])
            self.e_seo_desc.pack(fill='both', expand=True)
            frame.grid(row=5, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)

        # Fila 7: DESCRIPCION (CTkTextbox grande, 8 col)
        ctk.CTkLabel(self.shopify_frame, text='DESCRIPCION:', text_color=self.colors['text'], font=lbl_font).grid(row=6, column=0, sticky='nw', padx=6, pady=6)
        try:
            self.txt_description = ctk.CTkTextbox(self.shopify_frame, width=800, height=100, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), text_color=self.colors['light'], border_width=2, border_color=self.colors.get('border', self.colors.get('secondary', COLOR_MATRIX)))
            self.txt_description.grid(row=6, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)
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
            frame2 = ctk.CTkFrame(self.shopify_frame, fg_color=self.colors.get('background', COLOR_BG_TERMINAL), border_width=2, border_color=self.colors.get('border', self.colors.get('secondary', COLOR_MATRIX)))
            self.txt_description = tk.Text(frame2, bg=self.colors.get('background', COLOR_BG_TERMINAL), fg=self.colors['light'])
            self.txt_description.pack(fill='both', expand=True)
            frame2.grid(row=6, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)
        self.shopify_frame.grid_rowconfigure(6, weight=1)

        # Bottom buttons (aligned left per style guide)
        # Use terminal bg for footer to ensure buttons are visible and contrast correctly
        self.btn_frame = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        self.btn_frame.pack(side='bottom', fill='x', padx=12, pady=12)
        # Guardar (desde config)
        self.btn_guardar = create_action_button(self.btn_frame, 'guardar', self._on_save)
        self.btn_guardar.pack(side='left', padx=8)
        # Sincronizar (desde config)
        self.btn_sync = create_action_button(self.btn_frame, 'sincronizar', self._on_sync)
        self.btn_sync.pack(side='left', padx=8)
        # Buscar data (desde config)
        self.btn_buscar = create_action_button(self.btn_frame, 'buscar_data', self._on_buscar_data)
        self.btn_buscar.pack(side='left', padx=8)

        # Trace category changes to update taxonomy (focusout and selection events)
        try:
            self.cb_categoria.entry.bind('<FocusOut>', lambda e: (self._validate_combo_focus(self.cb_categoria), self._update_taxonomy_from_category()))
            self.cb_categoria.entry.bind('<<SearchableComboSelected>>', lambda e: (self._on_combo_selected(self.cb_categoria), self._update_taxonomy_from_category()))
            self.cb_categoria.entry.bind('<Return>', lambda e: (self._validate_combo_focus(self.cb_categoria), self._update_taxonomy_from_category()))
            self.cb_tipo.entry.bind('<FocusOut>', lambda e: self._validate_combo_focus(self.cb_tipo))
            self.cb_tipo.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_combo_selected(self.cb_tipo))
            self.cb_tipo.entry.bind('<Return>', lambda e: self._validate_combo_focus(self.cb_tipo))
            self.cb_proveedor.entry.bind('<FocusOut>', lambda e: self._validate_combo_focus(self.cb_proveedor))
            self.cb_proveedor.entry.bind('<<SearchableComboSelected>>', lambda e: self._on_combo_selected(self.cb_proveedor))
            self.cb_proveedor.entry.bind('<Return>', lambda e: self._validate_combo_focus(self.cb_proveedor))
        except Exception:
            pass

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
            cur = conn.cursor()
            # categorias
            try:
                cur.execute('SELECT id, nombre, shopify_taxonomy FROM categorias')
                cats = cur.fetchall()
                cat_opts = [(int(r[0]), r[1] or '') for r in cats]
                self.cb_categoria.set_options([(r[0], r[1]) for r in cat_opts])
                # save mapping for taxonomy
                self._cat_taxonomy = {int(r[0]): (r[2] or '') for r in cats}
            except Exception:
                logging.exception('Error cargando categorias')
            # tipos
            try:
                cur.execute('SELECT id, nombre FROM tipos')
                tipos = cur.fetchall()
                self.cb_tipo.set_options([(int(r[0]), r[1] or '') for r in tipos])
            except Exception:
                logging.exception('Error cargando tipos')
            # proveedores
            try:
                cur.execute('SELECT id, nombre FROM proveedores')
                provs = cur.fetchall()
                self.cb_proveedor.set_options([(int(r[0]), r[1] or '') for r in provs])
            except Exception:
                logging.exception('Error cargando proveedores')
            # IVA candidates: distinct from productos
            try:
                VALID_IVA_RATES = {0, 4, 10, 21}
                cur.execute('SELECT DISTINCT tipo_iva FROM productos')
                ivs = cur.fetchall()
                iva_set = {int(r[0]) for r in ivs if r[0] is not None} | VALID_IVA_RATES
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
            cid = self.cb_categoria.get_id()
            if cid and hasattr(self, '_cat_taxonomy'):
                tax = self._cat_taxonomy.get(cid, '')
                try:
                    # set readonly entry value
                    if getattr(self, 'ent_taxonomy', None):
                        try:
                            # clear then insert value
                            try:
                                self.ent_taxonomy.configure(state='normal')
                            except Exception:
                                pass
                            try:
                                # some CTkEntry expose delete/insert
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
                            pass
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

    def _on_gen_barcode_interno(self):
        """Generar código de barras interno e imagen JPG/PNG."""
        try:
            sku = self.e_sku.get().strip()
            if not sku:
                ToastWidget.show(self.container, "Introduce el SKU primero", tipo='warning')
                return

            # Generar número interno
            nuevo_codigo = barcode_gen_utils.generate_internal_number()
            
            # Generar imagen
            path = barcode_gen_utils.generate_barcode_image(nuevo_codigo, sku)
            
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

    def _open_shop_link(self):
        link = (self.e_nombre.get() or '').strip()
        # If shop_link entry exists, prefer it
        try:
            link_ent = getattr(self, 'e_shop_link', None)
            if link_ent:
                link = link_ent.get() or link
        except Exception:
            pass
        if link:
            try:
                webbrowser.open(link)
            except Exception:
                logging.exception('Error abriendo shop link')

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
        return True, ''

    def _on_save(self):
        valid, msg = self._validate_strict()
        if not valid:
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Validación', msg)
            except Exception:
                logging.error('Validación: %s', msg)
            return

        # Prepare data
        sku = (getattr(self, 'e_sku', None) and self.e_sku.get() or '').strip()
        if not sku:
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Validación', 'El SKU es obligatorio')
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
            titulo = (getattr(self, 'e_seo_title', None) and self.e_seo_title.get()) or ''
        except Exception:
            titulo = ''

        try:
            seo_title = (getattr(self, 'e_seo_short', None) and self.e_seo_short.get()) or ''
        except Exception:
            seo_title = ''

        try:
            tipo_shop = (getattr(self, 'e_tipo_shop', None) and self.e_tipo_shop.get()) or ''
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
            try:
                self._on_cancel()
            except Exception:
                pass

        except Exception:
            logging.exception('Error guardando producto, transacción revertida')
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se pudo guardar el producto')
            except Exception:
                pass

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
        try:
            logging.info('Sincronizar accion triggered')
            ToastWidget.show(self.container, 'Sincronización iniciada', tipo='info')
        except Exception:
            logging.exception('Error en _on_sync')

    def _on_buscar_data(self):
        try:
            logging.info('Buscar data accion triggered')
            ToastWidget.show(self.container, 'Búsqueda iniciada', tipo='info')
        except Exception:
            logging.exception('Error en _on_buscar_data')

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
                    'descripcion_shopify': (lambda: (
                        (lambda txt: txt.strip())(
                            (self.txt_description.get('1.0', 'end-1c') if getattr(self, 'txt_description', None) and hasattr(self.txt_description, 'get') else (self.txt_description.get() if getattr(self, 'txt_description', None) and hasattr(self.txt_description, 'get') else ''))
                        )
                    ))(),
                    'seo_description': (lambda: (
                        (lambda txt: txt.strip())(
                            (self.e_seo_desc.get('1.0', 'end-1c') if getattr(self, 'e_seo_desc', None) and hasattr(self.e_seo_desc, 'get') else (self.e_seo_desc.get() if getattr(self, 'e_seo_desc', None) and hasattr(self.e_seo_desc, 'get') else ''))
                        )
                    ))(),
                    'codigos_barras': (getattr(self, 'e_codigos', None) and (self.e_codigos.get() or '').strip()) or '',
            }
        except Exception:
            logging.exception('Error obteniendo datos CrearProductoUI')
            return {}

