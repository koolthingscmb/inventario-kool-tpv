"""Panel overlay para Devoluciones - Reescrito sin SelectionOverlayTemplate.

Este modulo define DevolucionesPanel (interfaz) y DevolucionAction.
Usa SearchablePaginatedNavList para garantizar el mismo comportamiento que StockSubView.
"""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable
import logging

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList


class DevolucionesPanel(ctk.CTkFrame):
    """Overlay especifico para devoluciones usando componentes estandar."""

    def __init__(self, view_or_action_panel: Any, db: Database, on_selection_callback: Optional[Callable] = None):
        # Determinar el parent para el overlay (el toplevel de la app)
        self.view = view_or_action_panel
        self.root = self.view.winfo_toplevel()
        
        # Inicializar como CTkFrame sobre el root
        super().__init__(self.root, fg_color="#1a1a1a", corner_radius=0)
        
        self.db = db
        self.on_selection_callback = on_selection_callback
        self._visible = False
        self._items = []
        self.devoluciones_service = None

        # Servicio de productos
        try:
            self.producto_service = ProductoService(db)
        except Exception:
            logging.exception('Error instanciando ProductoService en DevolucionesPanel')
            self.producto_service = None

        self._setup_ui()

    def _setup_ui(self):
        """Construye la interfaz manualmente."""
        # Contenedor principal con margen
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=40, pady=40)

        # Header: Titulo
        self.title_label = ctk.CTkLabel(
            self.main_container, 
            text="DEVOLUCIONES", 
            font=("Roboto", 34, "bold"),
            text_color="white"
        )
        self.title_label.pack(side="top", anchor="w", pady=(0, 5))

        # Subtitulo
        self.subtitle_label = ctk.CTkLabel(
            self.main_container, 
            text="Introduce EAN o nombre del articulo", 
            font=("Roboto", 16),
            text_color="#aaaaaa"
        )
        self.subtitle_label.pack(side="top", anchor="w", pady=(0, 20))

        # Fila de Controles (Buscador + Botones)
        self.controls_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.controls_frame.pack(side="top", fill="x", pady=(0, 20))

        # Buscador
        self.search_entry = ctk.CTkEntry(
            self.controls_frame, 
            width=400,
            height=45,
            placeholder_text="EAN o nombre...",
            font=("Roboto", 16)
        )
        self.search_entry.pack(side="left", padx=(0, 20))
        # BIND DE ENTER EXACTO COMO EN STOCKSUBVIEW
        self.search_entry.bind("<Return>", lambda e: self.search_list.search(self.search_entry.get()))

        # Boton Anadir (Aceptar)
        self.aceptar_btn = ctk.CTkButton(
            self.controls_frame,
            text="Anadir",
            width=140,
            height=45,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            font=("Roboto", 16, "bold"),
            command=self._on_aceptar_click
        )
        self.aceptar_btn.pack(side="left", padx=5)

        # Boton Cliente
        self.cliente_btn = ctk.CTkButton(
            self.controls_frame,
            text="Cliente",
            width=140,
            height=45,
            fg_color="#FFD400",
            hover_color="#e6be00",
            text_color="black",
            font=("Roboto", 16, "bold"),
            command=self._open_clientes
        )
        self.cliente_btn.pack(side="left", padx=5)

        # Boton Cerrar (X) arriba a la derecha
        from kool_tpv.utils.global_buttons import create_global_close_button
        self.close_btn = create_global_close_button(self, command=self.hide)
        self.close_btn.place(relx=0.97, rely=0.03, anchor="ne")

        # Lista de resultados
        columns = [
            ("id", 80, "ID"),
            ("nombre", 400, "Nombre"),
            ("categoria", 180, "Categoria"),
            ("tipo", 140, "Tipo"),
            ("stock_actual", 100, "Stock"),
        ]

        from kool_tpv.utils.config_loader import load_layout_config
        layout_cfg = load_layout_config()

        self.search_list = SearchablePaginatedNavList(
            parent=self.main_container,
            columns=columns,
            search_function=self._buscar_productos_api,
            map_function=self._map_producto_fila,
            module_name="tpv",
            page_limit=25,
            on_double_click=self._on_row_double_click,
            layout_config=layout_cfg
        )
        self.search_list.pack(fill="both", expand=True)

    def _ejecutar_busqueda(self):
        texto = self.search_var.get()
        logging.info(f"DevolucionesPanel: buscando '{texto}'")
        self.search_list.search(texto)

    def _buscar_productos_api(self, texto: str):
        if not self.producto_service:
            return []
        return self.producto_service.listar_productos(texto or "")

    def _map_producto_fila(self, item: dict):
        return {
            "id": item.get('id'),
            "nombre": item.get('nombre', ''),
            "categoria": item.get('categoria') or item.get('categoria_nombre') or '',
            "tipo": item.get('tipo') or item.get('tipo_nombre') or '',
            "stock_actual": item.get('stock_actual') if item.get('stock_actual') is not None else item.get('stock', '')
        }

    def show(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._visible = True
        
        # Cargar datos iniciales (vacio)
        try:
            self.search_list.search("")
        except: pass
        
        # Focus garantizado
        self.after(200, lambda: self.search_entry.focus_set())
        
        if hasattr(self.root, 'register_power_handler'):
            self.root.register_power_handler(self.hide, owner=self)

    def hide(self):
        self.place_forget()
        self._visible = False
        if hasattr(self.root, 'unregister_power_handler'):
            self.root.unregister_power_handler(owner=self)

    def _on_row_double_click(self, data):
        if data:
            self._add_to_devolucion(data)

    def _on_aceptar_click(self):
        selected = self.search_list.nav_list.get_selected_data()
        if selected:
            self._add_to_devolucion(selected)

    def _add_to_devolucion(self, product_data):
        try:
            pid = product_data.get('id')
            q = """
            SELECT p.id, p.nombre, COALESCE(pr.pvp,0.0) AS pvp, COALESCE(p.tipo_iva,21) AS tipo_iva
            FROM productos p
            LEFT JOIN precios pr ON pr.producto_id = p.id AND pr.activo = 1
            WHERE p.id = ?
            """
            row = self.db.fetch_one(q, (pid,))
            if row:
                full_prod = {
                    'id': row[0],
                    'nombre': row[1],
                    'pvp': str(row[2]),
                    'tipo_iva': int(row[3] or 21)
                }
            else:
                full_prod = product_data

            if self.devoluciones_service:
                self.devoluciones_service.add_devolucion_item(full_prod, cantidad=1)
                top = self.root
                if hasattr(top, 'carrito_ui') and top.carrito_ui:
                    top.carrito_ui.update_display()
                elif hasattr(self.view, 'carrito_ui') and self.view.carrito_ui:
                    self.view.carrito_ui.update_display()
            else:
                logging.error("No hay DevolucionesService vinculado al panel")
        except Exception:
            logging.exception("Error anadiendo item a devolucion")

    def _open_clientes(self):
        try:
            if hasattr(self.view, '_cliente_action') and self.view._cliente_action:
                self.view._cliente_action.ejecutar()
            else:
                from kool_tpv.modulos.tpv.actions.cliente import ClienteAction
                carrito = getattr(self.view, 'carrito_service', None)
                action = ClienteAction(self.view, self.db, carrito)
                action.ejecutar()
        except Exception:
            logging.exception("Error abriendo clientes desde devoluciones")


class DevolucionAction:
    def __init__(self, view: Any, db: Database, carrito_service: Any):
        self.view = view
        self.db = db
        self.carrito_service = carrito_service
        self._panel: Optional[DevolucionesPanel] = None

    def ejecutar(self) -> None:
        try:
            from kool_tpv.modulos.tpv.actions.permisos import check_permiso
            parent = self.view.winfo_toplevel()
            if not check_permiso(self.carrito_service, 'permiso_devolucion', parent):
                return

            if self._panel is None:
                self._panel = DevolucionesPanel(self.view, self.db)
                self._panel.devoluciones_service = DevolucionesService(self.db, self.carrito_service)
                self._panel.devoluciones_service.start_devolucion()
                
                original_hide = self._panel.hide
                def _hide_wrapper():
                    try:
                        self._panel.devoluciones_service.end_devolucion()
                    except: pass
                    original_hide()
                self._panel.hide = _hide_wrapper

            self._panel.show()
        except Exception:
            logging.exception('DevolucionAction: error al ejecutar')
