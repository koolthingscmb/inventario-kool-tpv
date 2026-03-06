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

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import get_font


class SearchableCombo(ctk.CTkFrame):
    """Combobox con búsqueda en tiempo real y modo estricto.

    Implementado con un popup (Toplevel) para el Listbox para evitar que
    empuje o redimensione el grid padre al mostrar coincidencias.
    """

    def __init__(self, parent, options: List[Tuple[int, str]] = None, placeholder: str = '', module_name: str = 'almacen', **kwargs):
        super().__init__(parent, fg_color='transparent')
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'background': '#1a1a1a', 'text': '#00FF00', 'border': '#00FF00', 'error': '#e74c3c'}
        self._var = tk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self._var, placeholder_text=placeholder, fg_color=self.colors.get('background', '#1a1a1a'), text_color=self.colors.get('text', '#00FF00'), border_color=self.colors.get('border', '#00FF00'), **kwargs)
        self.entry.pack(fill='x')
        self.popup = None
        self.listbox = None
        self.options = options or []
        self._names = [n for (_id, n) in self.options]
        self._mapping = {n: _id for (_id, n) in self.options}
        self._last_matches: List[str] = []
        self.entry.bind('<KeyRelease>', self._on_key)
        # keyboard navigation: handle arrows on the entry (remote control selection)
        self.entry.bind('<Down>', self._entry_down)
        self.entry.bind('<Up>', self._entry_up)
        # Enter on entry: if exactly one match or something selected, select it
        self.entry.bind('<Return>', self._entry_return)
        # hide popup shortly after focus out to allow selection clicks
        self.entry.bind('<FocusOut>', lambda e: self.entry.after(120, self._on_focus_out))

    def _on_focus_out(self, event=None):
        try:
            # first, check validity and then hide popup
            try:
                self._check_validity()
            except Exception:
                pass
            try:
                self._hide_list()
            except Exception:
                pass
        except Exception:
            pass

    def _check_validity(self):
        """Verifica que el texto actual coincida al 100% con una opción.

        Ajusta el color del borde: verde si válido, rojo si inválido.
        """
        try:
            name = (self._var.get() or '').strip()
            if name and name in self._names:
                # válido
                try:
                    self.entry.configure(border_color=self.colors.get('text', '#00FF00'))
                except Exception:
                    pass
                return True
            else:
                try:
                    # empty field considered invalid for strict combos
                    self.entry.configure(border_color=self.colors.get('error', '#e74c3c'))
                except Exception:
                    pass
                return False
        except Exception:
            logging.exception('Error comprobando validez en SearchableCombo')
            return False

    def set_border_color(self, color: str):
        try:
            self.entry.configure(border_color=color)
        except Exception:
            pass

    def _on_key(self, event=None):
        # FILTRO CRÍTICO: Si la tecla es de navegación, NO regenerar la lista
        try:
            if event and getattr(event, 'keysym', None) in ('Up', 'Down', 'Return', 'Escape', 'Tab'):
                return
        except Exception:
            pass

        text = (self._var.get() or '').lower()
        matches = [n for n in self._names if text in n.lower()]
        self._last_matches = matches
        if matches:
            self._show_list(matches)
        else:
            self._hide_list()

    def _entry_return(self, event=None):
        # Priority: if there's an active selection in the listbox, take it
        try:
            if self.listbox is not None:
                try:
                    sel = self.listbox.curselection()
                except Exception:
                    sel = ()
                if sel:
                    text = self.listbox.get(sel[0])
                    self._var.set(text)
                    self._hide_list()
                    return 'break'
        except Exception:
            pass

        # Fallback: if exactly one match, auto-select it
        try:
            if self._last_matches and len(self._last_matches) == 1:
                sel = self._last_matches[0]
                self._var.set(sel)
                self._hide_list()
                return 'break'
        except Exception:
            pass
        return None

    def _entry_down(self, event=None):
        try:
            if self.popup is None or self.listbox is None:
                return None
            size = self.listbox.size()
            if size == 0:
                return 'break'
            # find current selection
            sel = None
            try:
                sel = self.listbox.curselection()
            except Exception:
                sel = ()
            if not sel:
                idx = 0
            else:
                idx = min(size - 1, sel[0] + 1)
            try:
                self.listbox.selection_clear(0, 'end')
            except Exception:
                pass
            self.listbox.selection_set(idx)
            self.listbox.activate(idx)
            try:
                self.listbox.see(idx)
            except Exception:
                pass
            return 'break'
        except Exception:
            logging.exception('Error manejando Down en entry')
            return 'break'

    def _entry_up(self, event=None):
        try:
            if self.popup is None or self.listbox is None:
                return None
            size = self.listbox.size()
            if size == 0:
                return 'break'
            sel = None
            try:
                sel = self.listbox.curselection()
            except Exception:
                sel = ()
            if not sel:
                idx = size - 1
            else:
                idx = max(0, sel[0] - 1)
            try:
                self.listbox.selection_clear(0, 'end')
            except Exception:
                pass
            self.listbox.selection_set(idx)
            self.listbox.activate(idx)
            try:
                self.listbox.see(idx)
            except Exception:
                pass
            return 'break'
        except Exception:
            logging.exception('Error manejando Up en entry')
            return 'break'

    def _show_list(self, items: List[str]):
        try:
            if self.popup is None or not getattr(self.popup, 'winfo_exists', lambda: False)():
                self.popup = tk.Toplevel(self)
                self.popup.wm_overrideredirect(True)
                self.popup.configure(bg=self.colors.get('background', '#1a1a1a'))
                self.listbox = tk.Listbox(self.popup, bg=self.colors.get('background', '#1a1a1a'), fg=self.colors.get('text', '#00FF00'), highlightthickness=0, bd=0)
                self.listbox.pack(fill='both', expand=True)
                # selection via mouse or programmatic selection
                self.listbox.bind('<<ListboxSelect>>', self._on_select)
                # confirm via double-click or mouse release
                self.listbox.bind('<Double-Button-1>', self._on_select)
                self.listbox.bind('<ButtonRelease-1>', self._on_select)
                # we do NOT transfer focus to the listbox; entry keeps focus
                # keep a return handler available if listbox gets Return events
                self.listbox.bind('<Return>', self._listbox_return)

            self.listbox.delete(0, 'end')
            for it in items:
                self.listbox.insert('end', it)

            try:
                x = self.entry.winfo_rootx()
                y = self.entry.winfo_rooty() + self.entry.winfo_height()
                width = max(self.entry.winfo_width(), 200)
                self.popup.geometry(f"{width}x150+{x}+{y}")
                self.popup.lift()
            except Exception:
                pass
        except Exception:
            logging.exception('Error mostrando lista SearchableCombo')

    def _hide_list(self):
        try:
            if self.popup is not None:
                try:
                    self.popup.destroy()
                except Exception:
                    pass
                self.popup = None
                self.listbox = None
        except Exception:
            pass

    def _on_select(self, ev=None):
        try:
            if not self.listbox:
                return
            sel = self.listbox.curselection()
            if not sel:
                return
            text = self.listbox.get(sel[0])
            self._var.set(text)
            self._hide_list()
            try:
                # ensure the focus remains (or returns) to the entry so the
                # cursor never abandons the input box
                self.entry.focus_set()
            except Exception:
                pass
        except Exception:
            logging.exception('Error seleccionando item SearchableCombo')

    def _listbox_return(self, event=None):
        try:
            # emulate click selection
            if not self.listbox:
                return 'break'
            sel = self.listbox.curselection()
            if not sel:
                return 'break'
            text = self.listbox.get(sel[0])
            self._var.set(text)
            self._hide_list()
            try:
                self.entry.focus_set()
            except Exception:
                pass
            return 'break'
        except Exception:
            logging.exception('Error en _listbox_return')
            return 'break'

    def set_options(self, options: List[Tuple[int, str]]):
        self.options = options or []
        self._names = [n for (_id, n) in self.options]
        self._mapping = {n: _id for (_id, n) in self.options}

    def get(self) -> str:
        return self._var.get()

    def get_id(self) -> Optional[int]:
        name = (self._var.get() or '').strip()
        # strict: only return id if exact name match
        return self._mapping.get(name) if name in self._mapping else None

    def set(self, name: str):
        self._var.set(name)


class CrearProductoUI:
    def __init__(self, parent, db: Optional[object] = None):
        self.parent = parent
        self.db = db
        self.module_name = 'almacen'
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {}
        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#1a1a1a'))

        # Header
        self.lbl_titulo = ctk.CTkLabel(self.container, text="> NUEVO_PRODUCTO_SISTEMA", font=get_font('label', module=self.module_name), text_color=self.colors.get('text', '#00FF00'))
        self.lbl_titulo.pack(anchor="w", padx=12, pady=(12, 8))

        # Tabview
        self.tabview = ctk.CTkTabview(
            self.container,
            width=1100,
            height=540,
            fg_color=self.colors.get('background', '#1a1a1a'),
            segmented_button_fg_color=self.colors.get('text', '#00FF00'),
            segmented_button_selected_color="#03519F",
            segmented_button_selected_hover_color="#5A625A",
            text_color=self.colors.get('text', '#00FF00'),
        )
        self.tabview.pack(fill='both', expand=True, padx=12, pady=8)
        self.tab_general = self.tabview.add("[01] GENERAL")
        self.tab_shop = self.tabview.add("[02] SHOPIFY")

        # Ensure each tab frame uses dark bg to avoid flicker on switching
        try:
            self.tab_general.configure(fg_color=self.colors.get('background', '#1a1a1a'))
        except Exception:
            pass
        try:
            self.tab_shop.configure(fg_color=self.colors.get('background', '#1a1a1a'))
        except Exception:
            pass

        # try to increase segmented button font/size and ensure selected text visibility
        try:
            seg = getattr(self.tabview, '_segmented_button', None)
            if seg is not None:
                try:
                    for btn in getattr(seg, '_buttons', {}).values():
                        try:
                            btn.configure(font=get_font('button', module=self.module_name))
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        # Common styles
        lbl_font = get_font('label', module=self.module_name)
        entry_kwargs = {"fg_color": self.colors.get('background', '#1a1a1a'), "text_color": self.colors.get('text', '#00FF00'), "border_width": 2, "border_color": self.colors.get('text', '#00FF00'), "corner_radius": 4}

        # Build GENERAL tab with 8-column grid (7 filas requeridas)
        for c in range(8):
            self.tab_general.grid_columnconfigure(c, weight=1, uniform='col')

        # Fila 1: ID (2 col block) | NOMBRE (6 col block)
        ctk.CTkLabel(self.tab_general, text="ID:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_id = ctk.CTkEntry(self.tab_general, placeholder_text="ID (auto)", state='disabled', fg_color=self.colors.get('background', '#1a1a1a'), text_color="#666666", border_color=self.colors.get('text', '#00FF00'))
        self.e_id.grid(row=0, column=1, columnspan=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="NOMBRE:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.e_nombre = ctk.CTkEntry(self.tab_general, placeholder_text="Nombre del producto", **entry_kwargs)
        self.e_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 2: SKU (4 col) | NOMBRE_BOTON (4 col)
        ctk.CTkLabel(self.tab_general, text="SKU:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=1, column=0, sticky='w', padx=6, pady=6)
        self.e_sku = ctk.CTkEntry(self.tab_general, placeholder_text='SKU', **entry_kwargs)
        self.e_sku.grid(row=1, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="NOMBRE_BOTON:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=1, column=4, sticky='w', padx=6, pady=6)
        self.e_nombre_btn = ctk.CTkEntry(self.tab_general, placeholder_text='Texto botón', **entry_kwargs)
        self.e_nombre_btn.grid(row=1, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 3: CATEGORIA | TIPO | PROVEEDOR (distribuidos)
        ctk.CTkLabel(self.tab_general, text="CATEGORÍA:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.cb_categoria = SearchableCombo(self.tab_general, placeholder='Buscar categoría', module_name=self.module_name)
        self.cb_categoria.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="TIPO:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=2, column=3, sticky='w', padx=6, pady=6)
        self.cb_tipo = SearchableCombo(self.tab_general, placeholder='Buscar tipo', module_name=self.module_name)
        self.cb_tipo.grid(row=2, column=4, columnspan=2, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="PROVEEDOR:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=2, column=6, sticky='w', padx=6, pady=6)
        self.cb_proveedor = SearchableCombo(self.tab_general, placeholder='Buscar proveedor', module_name=self.module_name)
        self.cb_proveedor.grid(row=2, column=7, sticky='ew', padx=6, pady=6)

        # Fila 4: PVP (4 col) | COSTE (4 col)
        ctk.CTkLabel(self.tab_general, text="PVP:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_pvp = ctk.CTkEntry(self.tab_general, placeholder_text='0.00', **entry_kwargs)
        self.e_pvp.grid(row=3, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="COSTE:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=3, column=4, sticky='w', padx=6, pady=6)
        self.e_coste = ctk.CTkEntry(self.tab_general, placeholder_text='0.00', **entry_kwargs)
        self.e_coste.grid(row=3, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 5: TIPO_IVA (4 col) | PVP_VARIABLE (4 col)
        ctk.CTkLabel(self.tab_general, text="TIPO_IVA:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=4, column=0, sticky='w', padx=6, pady=6)
        self.cb_iva = SearchableCombo(self.tab_general, placeholder='IVA (ej: 21)', module_name=self.module_name)
        self.cb_iva.grid(row=4, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="PVP_VARIABLE:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=4, column=4, sticky='w', padx=6, pady=6)
        self.chk_pvp_var = ctk.CTkCheckBox(self.tab_general, text='', fg_color=self.colors.get('text', '#00FF00'))
        self.chk_pvp_var.grid(row=4, column=5, columnspan=3, sticky='w', padx=6, pady=6)

        # Fila 6: STOCK_ACTUAL (4 col) | STOCK_MINIMO (4 col)
        ctk.CTkLabel(self.tab_general, text="STOCK_ACTUAL:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=5, column=0, sticky='w', padx=6, pady=6)
        self.e_stock_actual = ctk.CTkEntry(self.tab_general, placeholder_text='0', **entry_kwargs)
        self.e_stock_actual.grid(row=5, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="STOCK_MINIMO:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=5, column=4, sticky='w', padx=6, pady=6)
        self.e_stock_min = ctk.CTkEntry(self.tab_general, placeholder_text='0', **entry_kwargs)
        self.e_stock_min.grid(row=5, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 7: VENTAS (read-only 4 col) | ESTADO (4 col)
        ctk.CTkLabel(self.tab_general, text="VENTAS:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=6, column=0, sticky='w', padx=6, pady=6)
        self.e_ventas = ctk.CTkEntry(self.tab_general, placeholder_text='0', state='disabled', fg_color=self.colors.get('background', '#1a1a1a'), text_color="#666666")
        self.e_ventas.grid(row=6, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(self.tab_general, text="ESTADO:", text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=6, column=4, sticky='w', padx=6, pady=6)
        self.cb_estado = ctk.CTkOptionMenu(self.tab_general, values=['Activo', 'Sin Stock', 'Archivado'], fg_color=self.colors.get('background', '#1a1a1a'), button_color="#2b2b2b", text_color=self.colors.get('text', '#00FF00'))
        self.cb_estado.grid(row=6, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Load options from DB if available
        self._load_db_options()

        # SHOPIFY tab: 6 filas, un campo por fila máximo orden
        for c in range(8):
            self.tab_shop.grid_columnconfigure(c, weight=1, uniform='col')

        # Fila 1: TITULO (Label + Entry, 8 col)
        ctk.CTkLabel(self.tab_shop, text='TITULO:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=0, column=0, sticky='w', padx=6, pady=6)
        self.e_seo_title = ctk.CTkEntry(self.tab_shop, placeholder_text='Título web', **entry_kwargs)
        self.e_seo_title.grid(row=0, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 2: LINK (Label azul clicable, 8 col)
        self.lbl_shop_link = ctk.CTkLabel(self.tab_shop, text='VER SHOP', text_color='#00A0FF', font=lbl_font)
        self.lbl_shop_link.grid(row=1, column=0, columnspan=8, sticky='w', padx=6, pady=6)
        self.lbl_shop_link.bind('<Button-1>', lambda e: self._open_shop_link())

        # Fila 3: TAXONOMY (static vinculado, 4 col) | TIPO_SHOP (label+entry, 4 col)
        ctk.CTkLabel(self.tab_shop, text='TAXONOMY:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=2, column=0, sticky='w', padx=6, pady=6)
        self.lbl_taxonomy = ctk.CTkLabel(self.tab_shop, text='', text_color=self.colors.get('text', '#00FF00'), font=lbl_font)
        self.lbl_taxonomy.grid(row=2, column=1, columnspan=3, sticky='w', padx=6, pady=6)

        ctk.CTkLabel(self.tab_shop, text='TIPO_SHOP:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=2, column=4, sticky='w', padx=6, pady=6)
        self.e_tipo_shop = ctk.CTkEntry(self.tab_shop, placeholder_text='Tipo shop', **entry_kwargs)
        self.e_tipo_shop.grid(row=2, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 4: TAGS (ocupa toda la fila, 8 columnas)
        ctk.CTkLabel(self.tab_shop, text='TAGS:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=3, column=0, sticky='w', padx=6, pady=6)
        self.e_tags = ctk.CTkEntry(self.tab_shop, placeholder_text='tag1, tag2', **entry_kwargs)
        self.e_tags.grid(row=3, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 5: SEO_TITLE (Label + Entry, 8 col)
        ctk.CTkLabel(self.tab_shop, text='SEO_TITLE:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=4, column=0, sticky='w', padx=6, pady=6)
        self.e_seo_short = ctk.CTkEntry(self.tab_shop, placeholder_text='SEO short title', **entry_kwargs)
        self.e_seo_short.grid(row=4, column=1, columnspan=7, sticky='ew', padx=6, pady=6)

        # Fila 6: SEO_DESCRIPTION (CTkTextbox, altura menor 80px, 8 col)
        ctk.CTkLabel(self.tab_shop, text='SEO_DESCRIPTION:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=5, column=0, sticky='nw', padx=6, pady=6)
        try:
            self.e_seo_desc = ctk.CTkTextbox(self.tab_shop, width=800, height=80, fg_color=self.colors.get('background', '#1a1a1a'), text_color=self.colors.get('text', '#00FF00'))
        except Exception:
            self.e_seo_desc = tk.Text(self.tab_shop, bg=self.colors.get('background', '#1a1a1a'), fg=self.colors.get('text', '#00FF00'))
        self.e_seo_desc.grid(row=5, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)

        # Fila 7: DESCRIPCION (CTkTextbox grande, 8 col)
        ctk.CTkLabel(self.tab_shop, text='DESCRIPCION:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=6, column=0, sticky='nw', padx=6, pady=6)
        try:
            self.txt_description = ctk.CTkTextbox(self.tab_shop, width=800, height=240, fg_color=self.colors.get('background', '#1a1a1a'), text_color=self.colors.get('text', '#00FF00'))
        except Exception:
            self.txt_description = tk.Text(self.tab_shop, bg=self.colors.get('background', '#1a1a1a'), fg=self.colors.get('text', '#00FF00'))
        self.txt_description.grid(row=6, column=1, columnspan=7, sticky='nsew', padx=6, pady=6)
        self.tab_shop.grid_rowconfigure(6, weight=1)

        # Bottom buttons
        self.btn_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        self.btn_frame.pack(side='bottom', fill='x', padx=12, pady=12)
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text='CANCELAR', fg_color='#e74c3c', text_color='white', command=self._on_cancel)
        self.btn_cancel.pack(side='right', padx=8)
        self.btn_save = ctk.CTkButton(self.btn_frame, text='EJECUTAR_GUARDADO', fg_color='#2ecc71', text_color='black', command=self._on_save)
        self.btn_save.pack(side='right', padx=8)

        # Trace category changes to update taxonomy
        try:
            self.cb_categoria.entry.bind('<FocusOut>', lambda e: self._update_taxonomy_from_category())
        except Exception:
            pass

    def _add_label_entry(self, parent, label, row, col, colspan, entry_kwargs, lbl_font, placeholder=''):
        ctk.CTkLabel(parent, text=f'{label}:', text_color=self.colors.get('text', '#00FF00'), font=lbl_font).grid(row=row, column=col, sticky='w', padx=6, pady=6)
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
                cur.execute('SELECT DISTINCT tipo_iva FROM productos')
                ivs = cur.fetchall()
                iva_opts = []
                for r in ivs:
                    try:
                        if r[0] is not None:
                            iva_opts.append((int(r[0]), str(int(r[0]))))
                    except Exception:
                        continue
                if not iva_opts:
                    iva_opts = [(21, '21'), (4, '4')]
                self.cb_iva.set_options(iva_opts)
            except Exception:
                logging.exception('Error cargando IVA options')
        except Exception:
            logging.exception('Error en _load_db_options')

    def _update_taxonomy_from_category(self):
        try:
            cid = self.cb_categoria.get_id()
            if cid and hasattr(self, '_cat_taxonomy'):
                tax = self._cat_taxonomy.get(cid, '')
                try:
                    self.lbl_taxonomy.configure(text=tax)
                except Exception:
                    pass
        except Exception:
            logging.exception('Error actualizando taxonomy')

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
                        w.set_border_color(self.colors.get('error', '#e74c3c'))
                    except Exception:
                        pass
                    return False, f"{label} obligatorio"
                if w.get_id() is None:
                    # force red border and return descriptive message
                    try:
                        w.set_border_color(self.colors.get('error', '#e74c3c'))
                    except Exception:
                        pass
                    return False, f"La {label} '{val}' no existe"
                else:
                    try:
                        w.set_border_color(self.colors.get('text', '#00FF00'))
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
        sku = (getattr(self, 'e_sku', None) and self.e_sku.get()) or None
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
        iva = self.cb_iva.get_id() or 21
        try:
            stock_actual = int(self.e_stock_actual.get() or 0)
        except Exception:
            stock_actual = 0
        try:
            stock_min = int(self.e_stock_min.get() or 0)
        except Exception:
            stock_min = 0
        activo = 1 if (self.cb_estado.get() or 'Activo') == 'Activo' else 0

        # Transaction: insert/update productos and precios
        try:
            db = self.db
            if db is None or getattr(db, 'connection', None) is None:
                # try to use sqlite3 directly on default path
                raise RuntimeError('Database no disponible')
            conn = db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')
            # check if product exists by sku
            prod_id = None
            if sku:
                cur.execute('SELECT id FROM productos WHERE sku = ?', (sku,))
                r = cur.fetchone()
                if r and r[0]:
                    prod_id = int(r[0])

            if prod_id is None:
                # insert
                cur.execute('''INSERT INTO productos (nombre, nombre_boton, sku, categoria, tipo, proveedor_id, tipo_iva, stock_actual, stock_minimo, activo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (nombre, nombre_boton, sku, categoria_id, tipo_id, proveedor_id, iva, stock_actual, stock_min, activo))
                prod_id = cur.lastrowid
            else:
                cur.execute('''UPDATE productos SET nombre=?, nombre_boton=?, categoria=?, tipo=?, proveedor_id=?, tipo_iva=?, stock_actual=?, stock_minimo=?, activo=? WHERE id=?''', (nombre, nombre_boton, categoria_id, tipo_id, proveedor_id, iva, stock_actual, stock_min, activo, prod_id))

            # Upsert precio: deactivate previous active precios for this product and insert new active
            try:
                cur.execute('UPDATE precios SET activo = 0 WHERE producto_id = ?', (prod_id,))
            except Exception:
                pass
            cur.execute('INSERT INTO precios (producto_id, pvp, coste, activo) VALUES (?, ?, ?, 1)', (prod_id, float(pvp), float(coste)))

            conn.commit()
            try:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'Guardado', 'Producto guardado correctamente')
            except Exception:
                logging.info('Producto guardado id=%s', prod_id)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
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
                    w = getattr(self, attr)
                    try:
                        if hasattr(w, 'delete'):
                            if isinstance(w, SearchableCombo):
                                w.set('')
                            else:
                                w.delete(0, 'end')
                        elif hasattr(w, 'configure'):
                            w.configure(text='')
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error en _on_cancel CrearProductoUI')

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
            }
        except Exception:
            logging.exception('Error obteniendo datos CrearProductoUI')
            return {}


