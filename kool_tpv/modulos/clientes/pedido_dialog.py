"""Diálogo para crear o editar un pedido de cliente."""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import Optional, Dict, Any
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.modulos.clientes.services.pedidos_service import PedidosService
from kool_tpv.modulos.clientes.ui_clientes import UIClientes
from kool_tpv.modulos.almacen.ui.ui_productos_dialog import UIProductosDialog
from kool_tpv.base_datos.money_adapter import read_from_db

logger = logging.getLogger(__name__)

class PedidoDialog:
    def __init__(self, parent, db, cliente_id: Optional[int] = None, keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.cliente_id = cliente_id
        self.keyboard_manager = keyboard_manager
        self.service = PedidosService(db)
        self.result = False
        
        # Estado del diálogo
        self.selected_cliente = None
        self.selected_producto = None
        
        # Crear ventana modal
        self.window = ctk.CTkToplevel(parent)
        self.window.title("NUEVO PEDIDO ESPECIAL")
        self.window.geometry("700x650")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Colors
        self.bg_color = COLOR_BG_TERMINAL
        self.text_color = COLOR_MATRIX
        
        self.main_frame = ctk.CTkFrame(self.window, fg_color=self.bg_color)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # TITULO
        ctk.CTkLabel(
            self.main_frame, 
            text="REGISTRAR PEDIDO / RESERVA", 
            font=get_font('title', module='clientes'),
            text_color=self.text_color
        ).pack(pady=(0, 20))
        
        # --- SECCIÓN CLIENTE ---
        cliente_group = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        cliente_group.pack(fill='x', pady=10)
        
        ctk.CTkLabel(cliente_group, text="CLIENTE:", font=get_font('label_bold'), text_color=self.text_color).pack(anchor='w')
        
        self.btn_seleccionar_cliente = ctk.CTkButton(
            cliente_group,
            text="BUSCAR CLIENTE FIDELIZADO",
            command=self._seleccionar_cliente,
            height=40,
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_seleccionar_cliente.pack(fill='x', pady=5)
        
        self.lbl_cliente_info = ctk.CTkLabel(cliente_group, text="O rellene datos de contacto manual:", font=get_font('small'), text_color="#AAAAAA")
        self.lbl_cliente_info.pack(anchor='w', pady=(5, 0))
        
        contacto_frame = ctk.CTkFrame(cliente_group, fg_color='transparent')
        contacto_frame.pack(fill='x', pady=5)
        
        self.e_nombre = ctk.CTkEntry(contacto_frame, placeholder_text="Nombre cliente manual", height=36, width=300)
        self.e_nombre.pack(side='left', padx=(0, 10))
        
        self.e_telefono = ctk.CTkEntry(contacto_frame, placeholder_text="Teléfono contacto", height=36)
        self.e_telefono.pack(side='left', fill='x', expand=True)

        # Si se pasó cliente_id, cargarlo
        if self.cliente_id:
            try:
                from kool_tpv.modulos.clientes.cliente_service import ClienteService
                c_data = ClienteService(self.db).get_cliente(self.cliente_id)
                if c_data:
                    self._on_cliente_selected(c_data)
            except Exception:
                logger.exception("Error cargando cliente inicial en PedidoDialog")
        
        # --- SECCIÓN PRODUCTO ---
        producto_group = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        producto_group.pack(fill='x', pady=10)
        
        ctk.CTkLabel(producto_group, text="PRODUCTO:", font=get_font('label_bold'), text_color=self.text_color).pack(anchor='w')
        
        self.btn_seleccionar_producto = ctk.CTkButton(
            producto_group,
            text="BUSCAR PRODUCTO EN CATÁLOGO",
            command=self._seleccionar_producto,
            height=40,
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_seleccionar_producto.pack(fill='x', pady=5)
        
        self.lbl_prod_info = ctk.CTkLabel(producto_group, text="O describa el producto si no existe en BD:", font=get_font('small'), text_color="#AAAAAA")
        self.lbl_prod_info.pack(anchor='w', pady=(5, 0))
        
        self.e_info = ctk.CTkEntry(producto_group, placeholder_text="Ej: Manga One Piece Tomo 105, Edición especial...", height=36)
        self.e_info.pack(fill='x', pady=5)
        
        # --- CANTIDAD Y NOTAS ---
        extra_frame = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        extra_frame.pack(fill='x', pady=10)
        
        cant_frame = ctk.CTkFrame(extra_frame, fg_color='transparent')
        cant_frame.pack(side='left', padx=(0, 20))
        ctk.CTkLabel(cant_frame, text="CANTIDAD:", font=get_font('label_bold'), text_color=self.text_color).pack(anchor='w')
        self.e_cantidad = ctk.CTkEntry(cant_frame, width=80, height=36)
        self.e_cantidad.insert(0, "1")
        self.e_cantidad.pack(pady=5)
        
        notas_frame = ctk.CTkFrame(extra_frame, fg_color='transparent')
        notas_frame.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(notas_frame, text="NOTAS INTERNAS:", font=get_font('label_bold'), text_color=self.text_color).pack(anchor='w')
        self.e_notas = ctk.CTkEntry(notas_frame, placeholder_text="Ej: Urgente, avisar por la mañana...", height=36)
        self.e_notas.pack(fill='x', pady=5)
        
        # --- BOTONES ---
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color='transparent')
        btn_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="CANCELAR", command=self.window.destroy,
            fg_color="#555555", hover_color="#666666", height=45
        )
        self.btn_cancelar.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        self.btn_guardar = ctk.CTkButton(
            btn_frame, text="GUARDAR PEDIDO", command=self._on_guardar,
            fg_color="#00A4DF", hover_color="#008BBF", height=45
        )
        self.btn_guardar.pack(side='right', fill='x', expand=True)
        
        self.window.wait_window()

    def _seleccionar_cliente(self):
        ui = UIClientes(self.window, self.db, on_cliente_selected=self._on_cliente_selected)
        ui.show()

    def _on_cliente_selected(self, cliente):
        self.selected_cliente = cliente
        self.btn_seleccionar_cliente.configure(
            text=f"CLIENTE: {cliente['nombre']} (ID: {cliente['id']})",
            fg_color="#00CC66"
        )
        # Desactivar campos manuales
        self.e_nombre.delete(0, 'end')
        self.e_nombre.insert(0, cliente['nombre'])
        self.e_nombre.configure(state='disabled')
        self.e_telefono.delete(0, 'end')
        self.e_telefono.insert(0, cliente.get('telefono', ''))
        self.e_telefono.configure(state='disabled')

    def _seleccionar_producto(self):
        UIProductosDialog(self.window, self.db, on_producto_selected=self._on_producto_selected)

    def _on_producto_selected(self, producto):
        self.selected_producto = producto
        self.btn_seleccionar_producto.configure(
            text=f"PRODUCTO: {producto['nombre']} (SKU: {producto['sku']})",
            fg_color="#00CC66"
        )
        # Limpiar campo info y desactivar para evitar confusiones
        self.e_info.delete(0, 'end')
        self.e_info.configure(state='disabled', placeholder_text="Producto seleccionado del catálogo")

    def _on_guardar(self):
        # Validaciones
        nombre = self.e_nombre.get().strip()
        info = self.e_info.get().strip()
        
        if not self.selected_cliente and not nombre:
            ToastWidget.show(self.window, "Debe indicar un cliente o nombre de contacto", tipo='error')
            return
            
        if not self.selected_producto and not info:
            ToastWidget.show(self.window, "Debe seleccionar un producto o describir uno en 'Info'", tipo='error')
            return
            
        try:
            cant = int(self.e_cantidad.get().strip() or "1")
        except ValueError:
            ToastWidget.show(self.window, "Cantidad no válida", tipo='error')
            return

        data = {
            'cliente_id': self.selected_cliente['id'] if self.selected_cliente else None,
            'contacto_nombre': nombre if not self.selected_cliente else None,
            'contacto_telefono': self.e_telefono.get().strip(),
            'producto_id': self.selected_producto['id'] if self.selected_producto else None,
            'info': info if not self.selected_producto else None,
            'cantidad_solicitada': cant,
            'notas': self.e_notas.get().strip(),
            'usuario_id': None # TODO: Coger usuario activo
        }
        
        res = self.service.crear_pedido(data)
        if res['success']:
            self.result = True
            self.window.destroy()
        else:
            ToastWidget.show(self.window, res['error'], tipo='error')

    def show(self):
        return self.result
