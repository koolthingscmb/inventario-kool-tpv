"""Diálogo para buscar y seleccionar un producto del catálogo."""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config

logger = logging.getLogger(__name__)

class UIProductosDialog:
    def __init__(self, parent, db, on_producto_selected: Callable[[Dict[str, Any]], None]):
        self.parent = parent
        self.db = db
        self.on_producto_selected = on_producto_selected
        self.service = ProductoService(db)
        
        self.window = ctk.CTkToplevel(parent)
        self.window.title("BUSCAR PRODUCTO")
        self.window.geometry("900x700")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.bg_color = COLOR_BG_TERMINAL
        self.text_color = COLOR_MATRIX
        
        self.main_frame = ctk.CTkFrame(self.window, fg_color=self.bg_color)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # TOP: Search
        search_frame = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        search_frame.pack(fill='x', pady=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Nombre, SKU o EAN del producto... (Pulsa Enter)",
            height=40,
            font=get_font('entry')
        )
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._on_search())
        
        # LIST
        columns = [
            ('id', 50, 'ID'),
            ('sku', 120, 'SKU'),
            ('nombre', 400, 'NOMBRE'),
            ('pvp', 80, 'PVP'),
            ('stock_actual', 70, 'STOCK'),
            ('categoria_nombre', 120, 'CATEGORÍA')
        ]
        
        self.search_list = SearchablePaginatedNavList(
            parent=self.main_frame,
            columns=columns,
            search_function=self._buscar_productos,
            map_function=self._map_producto,
            module_name='almacen',
            page_limit=50,
            on_double_click=self._on_item_selected,
            layout_config=load_layout_config()
        )
        self.search_list.pack(fill='both', expand=True)
        
        # FOOTER
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        btn_frame.pack(fill='x', pady=(10, 0))
        
        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="CANCELAR", command=self.window.destroy,
            fg_color="#555555", hover_color="#666666", height=40
        )
        self.btn_cancelar.pack(side='left')
        
        self.btn_seleccionar = ctk.CTkButton(
            btn_frame, text="SELECCIONAR", command=self._on_btn_seleccionar,
            fg_color="#00A4DF", hover_color="#008BBF", height=40
        )
        self.btn_seleccionar.pack(side='right')
        
        self.window.after(100, lambda: self.search_entry.focus_set())

    def _on_search(self):
        termino = self.search_var.get().strip()
        self.search_list.search(termino)

    def _buscar_productos(self, texto: str):
        try:
            return self.service.buscar_productos_paginados(
                termino_busqueda=texto,
                limit=100
            )
        except Exception:
            logger.exception("Error buscando productos en UIProductosDialog")
            return []

    def _map_producto(self, p: dict) -> dict:
        return {
            'id': str(p.get('id')),
            'sku': p.get('sku') or '',
            'nombre': p.get('nombre') or '',
            'pvp': f"{p.get('pvp', 0):.2f}€",
            'stock_actual': str(p.get('stock_actual', 0)),
            'categoria_nombre': p.get('categoria') or '',
            '_data': p
        }

    def _on_item_selected(self, item_data: dict):
        producto = item_data.get('_data')
        if producto:
            self.on_producto_selected(producto)
            self.window.destroy()

    def _on_btn_seleccionar(self):
        # Obtener selección actual del NavList
        data = self.search_list.nav_list.get_selected_data()
        if data:
            self._on_item_selected(data)
        else:
            # Si no hay selección pero hay resultados, cogemos el primero? 
            # O mejor avisar.
            from kool_tpv.utils.widgets.notificaciones import ToastWidget
            ToastWidget.show(self.window, "SELECCIONE UN PRODUCTO DE LA LISTA", tipo='info')
