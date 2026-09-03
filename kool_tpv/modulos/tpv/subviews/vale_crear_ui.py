from customtkinter import CTkFrame, CTkLabel, CTkEntry
import logging
import tkinter as tk
from decimal import Decimal
from typing import List, Dict, Any

from kool_tpv.utils.widgets.notificaciones import ToastWidget, show_warning, show_success
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config
from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)

class ValeCrearUI(CTkFrame):
    """Formulario para creación manual de vales con selección de cliente."""

    def __init__(self, parent, view=None, db=None, callback_success=None):
        super().__init__(parent)
        self.view = view
        self.db = db
        self.callback_success = callback_success
        
        self.cliente_service = ClienteService(db) if db else None
        self.vale_service = ValeDevolucionService()
        
        self.cliente_seleccionado = None

        # --- ZONA 1: Importe ---
        self.amount_frame = CTkFrame(self, fg_color="transparent")
        self.amount_frame.pack(side="top", fill="x", padx=20, pady=(20, 10))
        
        CTkLabel(self.amount_frame, text="IMPORTE (€):", font=("Roboto", 16, "bold")).pack(side="left", padx=(0, 10))
        self.entry_importe = CTkEntry(self.amount_frame, width=150, height=40, font=("Roboto", 18))
        self.entry_importe.pack(side="left")
        self.entry_importe.focus_set()

        # --- ZONA 2: Selección de Cliente ---
        self.client_frame = CTkFrame(self)
        self.client_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        
        CTkLabel(self.client_frame, text="ASIGNAR A CLIENTE (OPCIONAL):", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.search_cli_var = tk.StringVar()
        self.entry_buscar_cli = CTkEntry(
            self.client_frame, 
            textvariable=self.search_cli_var,
            placeholder_text="Buscar cliente por nombre, DNI o teléfono...",
            height=35
        )
        self.entry_buscar_cli.pack(fill="x", padx=10, pady=5)
        self.entry_buscar_cli.bind('<Return>', lambda e: self.nav_cli.search(self.search_cli_var.get()))

        columns = [
            ('id', 50, 'ID'),
            ('nombre', 250, 'Nombre'),
            ('telefono', 120, 'Teléfono'),
            ('dni', 120, 'DNI')
        ]
        
        self.nav_cli = SearchablePaginatedNavList(
            parent=self.client_frame,
            columns=columns,
            search_function=self._buscar_clientes,
            map_function=self._map_cliente,
            module_name='clientes',
            on_double_click=self._on_cliente_double_click,
            layout_config=load_layout_config()
        )
        self.nav_cli.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- ZONA 3: Cliente Escogido ---
        self.selected_frame = CTkFrame(self, fg_color="transparent")
        self.selected_frame.pack(side="top", fill="x", padx=20, pady=5)
        
        self.lbl_cliente_info = CTkLabel(self.selected_frame, text="Cliente: ANÓNIMO", font=("Roboto", 14))
        self.lbl_cliente_info.pack(side="left")

        # --- ZONA 4: Botones ---
        self.actions_frame = CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.btn_guardar = ButtonFactory.create_button(
            parent=self.actions_frame,
            text="GUARDAR VALE",
            style_key="action_success",
            command=self._on_guardar,
            module='clientes',
            palette_key='primary'
        )
        self.btn_guardar.pack(side="right", padx=10)
        
        self.btn_cancelar = ButtonFactory.create_button(
            parent=self.actions_frame,
            text="CANCELAR",
            style_key="action_danger",
            command=self._on_cancelar,
            module='clientes',
            palette_key='accent'
        )
        self.btn_cancelar.pack(side="right", padx=10)

    def _buscar_clientes(self, texto: str):
        if not self.cliente_service:
            return []
        try:
            return self.cliente_service.buscar_clientes(texto)
        except Exception:
            return []

    def _map_cliente(self, c: dict) -> dict:
        return {
            'id': str(c.get('id', '')),
            'nombre': c.get('nombre', ''),
            'telefono': c.get('telefono', ''),
            'dni': c.get('dni', ''),
            '_obj': c
        }

    def _on_cliente_double_click(self, data: dict):
        cliente = data.get('_obj')
        if cliente:
            self.cliente_seleccionado = cliente
            self.lbl_cliente_info.configure(text=f"Cliente: {cliente.get('nombre')} (ID: {cliente.get('id')})", text_color="#4CAF50")
            ToastWidget.show(self, f"Cliente {cliente.get('nombre')} seleccionado", tipo='info')

    def _on_guardar(self):
        importe_str = self.entry_importe.get().strip().replace(',', '.')
        if not importe_str:
            show_warning(self.winfo_toplevel(), "DEBES INTRODUCIR UN IMPORTE")
            return
            
        try:
            importe_euros = Decimal(importe_str)
            if importe_euros <= 0:
                raise ValueError()
            importe_cents = prepare_for_db(importe_euros)
        except Exception:
            show_warning(self.winfo_toplevel(), "IMPORTE INVÁLIDO")
            return

        cliente_id = self.cliente_seleccionado.get('id') if self.cliente_seleccionado else None
        cliente_nombre = self.cliente_seleccionado.get('nombre') if self.cliente_seleccionado else None

        try:
            self.vale_service.guardar(
                importe_cents=importe_cents,
                num_ticket_devolucion="MANUAL",
                cliente_id=cliente_id,
                cliente_nombre=cliente_nombre,
                productos_nombres="VALE MANUAL"
            )
            show_success(self.winfo_toplevel(), "VALE CREADO CORRECTAMENTE")
            
            if self.callback_success:
                self.callback_success()
                
            self._on_cancelar() # Cerrar
        except Exception:
            logger.exception("Error guardando vale manual")
            ToastWidget.show(self, "Error al guardar el vale", tipo='error')

    def _on_cancelar(self):
        if self.view and hasattr(self.view, 'pop_subview'):
            self.view.pop_subview()
        else:
            self.destroy()
