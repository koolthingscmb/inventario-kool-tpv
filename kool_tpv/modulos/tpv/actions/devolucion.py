"""Panel overlay para Devoluciones — implementado con SearchablePaginatedNavList.

Este módulo define `DevolucionesPanel` (interfaz) y `DevolucionAction`
que se usa desde `TpvView` para abrir el overlay.

Reglas específicas:
- Título: "DEVOLUCIONES" y subtítulo "Introduce EAN o nombre del artículo".
- Columnas: id, nombre, stock_actual, ventas, pvp.
- Al mostrar, carga todos los productos usando ProductoService.
- Búsqueda al pulsar ENTER, consistente con StockSubView.
"""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import logging

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.config_loader import load_layout_config


class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específico para devoluciones, similar a StockSubView pero en formato Overlay."""

    def __init__(self, view_or_action_panel: Any, db: Database, on_selection_callback: Optional[callable] = None, ui_config: Optional[dict] = None):
        # Detectar root y view
        if hasattr(view_or_action_panel, "action_panel"):
            self.view = view_or_action_panel
            self.action_panel = getattr(self.view, "action_panel", None)
        else:
            self.view = None
            self.action_panel = view_or_action_panel

        try:
            if self.action_panel is not None:
                self.root = self.action_panel.winfo_toplevel()
            elif self.view is not None and getattr(self.view, "parent", None) is not None:
                self.root = self.view.parent.winfo_toplevel()
            else:
                self.root = view_or_action_panel.winfo_toplevel()
        except Exception:
            self.root = None

        parent_for_overlay = self.root if self.root is not None else self.action_panel
        
        # Inicializar como frame de overlay
        super().__init__(parent_for_overlay, fg_color="#1a1a1a", corner_radius=15)
        
        self.db = db
        self.on_selection_callback = on_selection_callback
        self.devoluciones_service: Optional[DevolucionesService] = None
        self._visible = False

        # ProductoService
        try:
            self.producto_service = ProductoService(db)
        except Exception:
            logging.exception('Error instanciando ProductoService en DevolucionesPanel')
            self.producto_service = None

        # --- UI LAYOUT ---
        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(20, 10))

        # Título
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="DEVOLUCIONES", 
            font=("Roboto", 34, "bold"),
            text_color="#ffffff"
        )
        self.title_label.pack(side="top", anchor="w")

        # Subtítulo
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="Introduce EAN o nombre del artículo", 
            font=("Roboto", 14),
            text_color="#aaaaaa"
        )
        self.subtitle_label.pack(side="top", anchor="w", pady=(2, 10))

        # Controles de búsqueda y botones
        self.controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.controls_frame.pack(side="top", fill="x")

        # Buscador (Entry)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.controls_frame, 
            textvariable=self.search_var, 
            placeholder_text="Buscar por nombre, SKU o EAN...",
            width=400,
            height=45,
            font=("Roboto", 16)
        )
        self.search_entry.pack(side="left", padx=(0, 15))
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        # Botones
        # Botón "Añadir" (el verde de aceptar en el template)
        self.aceptar_btn = ButtonFactory.create_button(
            parent=self.controls_frame,
            text="Añadir",
            style_key="primary", # o el que corresponda a añadir
            command=self._on_accept,
            width=140,
            height=45
        )
        self.aceptar_btn.pack(side="left", padx=5)

        # Botón "Cliente" (amarillo)
        self.cliente_btn = ButtonFactory.create_button(
            parent=self.controls_frame,
            text="Cliente",
            style_key="warning", # amarillo
            command=self._open_clientes,
            width=140,
            height=45
        )
        self.cliente_btn.configure(fg_color="#FFD400", text_color="#000000") # Forzar colores según petición previa
        self.cliente_btn.pack(side="left", padx=5)

        # Botón cerrar (X) arriba a la derecha
        from kool_tpv.utils.global_buttons import create_global_close_button
        self.close_btn = create_global_close_button(self, command=self.hide)
        self.close_btn.place(relx=1.0, x=-15, y=15, anchor="ne")

        # 2. Lista Frame
        self.list_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=10)
        self.list_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 20))

        columns = [
            ("id", 80, "ID"),
            ("nombre", 350, "Nombre Producto"),
            ("stock_actual", 100, "Stock"),
            ("ventas", 100, "Ventas"),
            ("pvp", 120, "PVP"),
        ]

        from kool_tpv.utils.keyboard_manager import KeyboardManager
        _km = getattr(self.root, 'keyboard_manager', None)

        self.search_list = SearchablePaginatedNavList(
            parent=self.list_frame,
            columns=columns,
            search_function=self._buscar_productos,
            map_function=self._map_producto,
            module_name="tpv",
            page_limit=50,
            on_double_click=self._on_row_double_click,
            keyboard_manager=_km,
            layout_config=load_layout_config(),
        )
        self.search_list.pack(fill="both", expand=True, padx=10, pady=10)

        # Registrar handler de power si existe la API en root
        try:
            if self.root is not None and hasattr(self.root, 'register_power_handler'):
                self.root.register_power_handler(self.hide, owner=self)
                # Si existe dispatcher central, re-vincular botón cerrar
                if hasattr(self.root, '_dispatch_power'):
                    self.close_btn.configure(command=self.root._dispatch_power)
        except Exception:
            pass

    def _do_search(self):
        """Ejecuta la búsqueda en el navlist."""
        termino = self.search_var.get()
        self.search_list.search(termino)

    def _buscar_productos(self, texto: str):
        """Callback para SearchablePaginatedNavList."""
        try:
            if not self.producto_service:
                return []
            # Usar listar_productos que ya corregimos para soportar EAN/SKU
            return self.producto_service.listar_productos(texto or '')
        except Exception:
            logging.exception('Error buscando productos en DevolucionesPanel')
            return []

    def _map_producto(self, item: dict):
        """Mapeo de datos para VirtualNavList."""
        return {
            "id": item.get('id'),
            "nombre": item.get('nombre') or '',
            "stock_actual": item.get('stock_actual') if item.get('stock_actual') is not None else item.get('stock', ''),
            "ventas": item.get('ventas', 0),
            "pvp": item.get('pvp', '0.00')
        }

    def _on_accept(self):
        """Handler para botón Añadir."""
        self._add_selected_to_devolucion()

    def _on_row_double_click(self, item: dict):
        """Handler para doble click en la lista."""
        self._add_selected_to_devolucion(item)

    def _add_selected_to_devolucion(self, item_pref: Optional[dict] = None):
        """Añade el producto seleccionado a la devolución."""
        try:
            # Si no nos pasan el item, lo buscamos en el navlist
            prod = item_pref
            if not prod:
                nav = getattr(self.search_list, 'nav_list', None)
                if nav:
                    prod = nav.get_selected_data()
            
            if not prod:
                return False

            if not self.devoluciones_service:
                logging.error('No hay DevolucionesService asociado al panel')
                return False

            # Recargar producto completo para asegurar pvp y tipo_iva
            try:
                pid = prod.get('id')
                full_prod = self.producto_service.get_producto_para_carrito(prod) if self.producto_service else prod
                # Si get_producto_para_carrito no devolvió lo esperado, usar el de la lista
                if not full_prod:
                    full_prod = prod
            except Exception:
                full_prod = prod

            added = self.devoluciones_service.add_devolucion_item(full_prod, cantidad=1)
            
            # Refrescar UI si es necesario (opcional)
            self._do_search()
            
            # Notificar al carrito UI
            try:
                if self.view and hasattr(self.view, 'carrito_ui'):
                    self.view.carrito_ui.update_display()
                elif self.root and hasattr(self.root, 'carrito_ui'):
                    self.root.carrito_ui.update_display()
            except Exception:
                pass
                
            # Mantener focus en el buscador para seguir metiendo EANs
            self.search_entry.focus_set()
            return bool(added)
            
        except Exception:
            logging.exception('Error añadiendo producto como devolución')
            return False

    def _open_clientes(self):
        """Abre el panel de selección de clientes."""
        try:
            from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
            carrito = None
            if self.devoluciones_service:
                carrito = self.devoluciones_service.carrito_service
            
            action = ClienteAction(self.view or self.root, self.db, carrito)
            action.ejecutar()
        except Exception:
            logging.exception('Error abriendo CLIENTES desde DevolucionesPanel')

    def show(self) -> None:
        """Muestra el overlay centrado."""
        try:
            # Calcular dimensiones (80% de la pantalla o similar)
            w = int(self.root.winfo_width() * 0.85)
            h = int(self.root.winfo_height() * 0.85)
            x = (self.root.winfo_width() - w) // 2
            y = (self.root.winfo_height() - h) // 2
            
            self.place(x=x, y=y, width=w, height=h)
            self._visible = True
            self.lift()
            
            # Carga inicial y focus
            self._do_search()
            self.after(200, lambda: self.search_entry.focus_set())
            
            logging.info("DevolucionesPanel: mostrado")
        except Exception:
            logging.exception("Error mostrando DevolucionesPanel")

    def hide(self) -> None:
        """Oculta el overlay."""
        try:
            self.place_forget()
            self._visible = False
        except Exception:
            logging.exception("Error ocultando DevolucionesPanel")


class DevolucionAction:
    """Acción que abre el panel de devoluciones."""

    def __init__(self, view: Any, db: Database, carrito_service: Any):
        self.view = view
        self.db = db
        self.carrito_service = carrito_service
        self._panel: Optional[DevolucionesPanel] = None

    def ejecutar(self) -> None:
        try:
            # Comprobar permiso del cajero logueado
            from kool_tpv.modulos.tpv.actions.permisos import check_permiso
            parent = self.view.winfo_toplevel() if hasattr(self.view, 'winfo_toplevel') else self.view
            
            if not check_permiso(self.carrito_service, 'permiso_devolucion', parent):
                return

            if self._panel is None:
                self._panel = DevolucionesPanel(self.view, self.db)
                try:
                    self._panel.devoluciones_service = DevolucionesService(self.db, self.carrito_service)
                    # Iniciar modo devolución
                    self._panel.devoluciones_service.start_devolucion()
                    
                    # Monkey patch hide para finalizar servicio al cerrar
                    original_hide = self._panel.hide
                    def _hide_and_end():
                        try:
                            if self._panel.devoluciones_service:
                                self._panel.devoluciones_service.end_devolucion()
                        except Exception:
                            logging.exception('Error finalizando devolucion al cerrar panel')
                        original_hide()
                    self._panel.hide = _hide_and_end
                except Exception:
                    logging.exception('Error inicializando DevolucionesService para panel')
            
            self._panel.show()
        except Exception:
            logging.exception('DevolucionAction: error al ejecutar acción')
