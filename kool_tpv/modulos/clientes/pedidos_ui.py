"""UI para la gestión de pedidos de clientes."""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import Optional, List, Dict, Any
from datetime import datetime

from kool_tpv.modulos.clientes.services.pedidos_service import PedidosService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import load_colors, load_layout_config
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.custom_dialog import show_warning

logger = logging.getLogger(__name__)

class PedidosUI:
    def __init__(self, parent, db=None, owner=None, module_name: str = 'clientes', keyboard_manager=None):
        self.parent = parent
        self.owner = owner  # ClientesView
        self.db = db
        self.module_name = module_name
        self.keyboard_manager = keyboard_manager
        self.service = PedidosService(db)
        
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {'text': COLOR_MATRIX, 'primary': COLOR_MATRIX, 'background': COLOR_BG_TERMINAL}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', COLOR_BG_TERMINAL))
        
        # TOP: Search and Actions
        top_frame = ctk.CTkFrame(self.container, fg_color='transparent')
        top_frame.pack(fill='x', padx=12, pady=(12, 6))
        
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            top_frame,
            textvariable=self.search_var,
            placeholder_text='Buscar pedido (cliente, producto, info, notas)...',
            height=36,
            fg_color=self.colors.get('background', COLOR_BG_TERMINAL),
            text_color=self.colors.get('text', COLOR_MATRIX),
            border_width=2,
            border_color=self.colors.get('primary', COLOR_MATRIX),
            font=get_font('entry', module=self.module_name)
        )
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self._on_search())
        
        self.btn_nuevo = ButtonFactory.create_button(
            parent=top_frame,
            text='+ PEDIDO',
            command=self._on_nuevo_pedido,
            style_key='action_primary'
        )
        self.btn_nuevo.pack(side='right', padx=5)

        self.btn_modificar = ButtonFactory.create_button(
            parent=top_frame,
            text='MODIFICAR',
            command=self._on_modificar_pedido,
            style_key='action_secondary'
        )
        self.btn_modificar.pack(side='right', padx=5)

        # FILTERS
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        
        ctk.CTkLabel(
            filter_frame,
            text='Estado:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(0, 8))
        
        self.estado_var = tk.StringVar(value='TODOS')
        estados_list = ['TODOS'] + [e['id'].upper() for e in self.service.get_estados()]
        
        self.combo_estado = ctk.CTkComboBox(
            filter_frame,
            values=estados_list,
            variable=self.estado_var,
            width=150,
            font=get_font('label', module=self.module_name)
        )
        self.combo_estado.pack(side='left', padx=(0, 10))

        self.btn_cambiar_estado = ButtonFactory.create_button(
            parent=filter_frame,
            text='CAMBIAR ESTADO',
            command=self._on_cambiar_estado,
            style_key='action_secondary'
        )
        self.btn_cambiar_estado.pack(side='left', padx=(0, 20))

        # LIST
        columns = [
            ('id', 50, 'ID'),
            ('fecha_pedido', 120, 'FECHA'),
            ('cliente_nombre', 200, 'CLIENTE'),
            ('producto_nombre', 400, 'PRODUCTO'),
            ('usuario_nombre', 120, 'USUARIO'),
            ('num_lineas', 80, 'LÍNEAS'),
            ('estado', 120, 'ESTADO'),
            ('notas', 250, 'NOTAS')
        ]
        
        self.nav_list = SearchablePaginatedNavList(
            parent=self.container,
            columns=columns,
            search_function=self._buscar_pedidos,
            map_function=self._map_pedido,
            module_name=self.module_name,
            page_limit=50,
            on_double_click=self._on_item_double_click,
            keyboard_manager=self.keyboard_manager,
            layout_config=load_layout_config()
        )
        self.nav_list.pack(fill='both', expand=True, padx=12, pady=6)
        
        # Auto-focus
        self.container.after(100, lambda: self.search_entry.focus_set())
        
        # Setup Tab Navigation
        self._setup_tab_nav()

    def _setup_tab_nav(self):
        """Configurar la navegación por Tab."""
        try:
            root = self.container.winfo_toplevel()
            root.bind("<Tab>", self._on_tab_next)
            root.bind("<Shift-Tab>", self._on_tab_prev)
            
            # Limpiar al destruir
            self.container.bind("<Destroy>", self._on_view_destroy)
        except Exception:
            logging.exception("Error vinculando Tab en PedidosUI")

    def _on_view_destroy(self, event):
        """Limpiar bindings globales al cerrar la vista."""
        if event.widget == self.container:
            try:
                root = self.container.winfo_toplevel()
                root.unbind("<Tab>")
                root.unbind("<Shift-Tab>")
            except Exception:
                pass

    def _get_navigable_widgets(self):
        """Obtiene la lista de widgets navegables (internos de tkinter) en orden."""
        widgets = []
        def add_widget(w):
            if not w: return
            if hasattr(w, '_entry'): widgets.append(w._entry)
            elif hasattr(w, '_canvas'): widgets.append(w._canvas)
            else: widgets.append(w)

        if hasattr(self, 'search_entry'): add_widget(self.search_entry)
        if hasattr(self, 'combo_estado'): add_widget(self.combo_estado)
        if hasattr(self, 'btn_cambiar_estado'): add_widget(self.btn_cambiar_estado)
        if hasattr(self, 'btn_modificar'): add_widget(self.btn_modificar)
        if hasattr(self, 'btn_nuevo'): add_widget(self.btn_nuevo)
        
        return [w for w in widgets if w.winfo_exists() and w.winfo_viewable()]

    def _on_tab_next(self, event):
        """Foco al siguiente widget."""
        widgets = self._get_navigable_widgets()
        if not widgets: return
        
        try:
            current = self.container.focus_get()
            if current in widgets:
                idx = widgets.index(current)
                next_idx = (idx + 1) % len(widgets)
                widgets[next_idx].focus_set()
            else:
                widgets[0].focus_set()
        except Exception:
            widgets[0].focus_set()
            
        return "break"

    def _on_tab_prev(self, event):
        """Foco al widget anterior."""
        widgets = self._get_navigable_widgets()
        if not widgets: return
        
        try:
            current = self.container.focus_get()
            if current in widgets:
                idx = widgets.index(current)
                prev_idx = (idx - 1) % len(widgets)
                widgets[prev_idx].focus_set()
            else:
                widgets[-1].focus_set()
        except Exception:
            widgets[-1].focus_set()
            
        return "break"

    def get_widget(self):
        return self.container

    def _on_search(self):
        termino = (self.search_var.get() or '').strip()
        self.nav_list.search(termino)

    def _buscar_pedidos(self, texto: str):
        pedidos = self.service.get_pedidos(estado=None, termino=texto)
        return pedidos

    def _map_pedido(self, pedido: dict) -> dict:
        # Formatear fecha
        fecha = pedido.get('fecha_pedido', '')
        if fecha:
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                fecha = dt.strftime('%d/%m/%y %H:%M')
            except Exception:
                pass
        
        # Badge de estado con color
        estado_id = pedido.get('estado', 'pendiente')
        estado_txt = estado_id.upper()
        
        # Si es distribuidor, resaltar
        if estado_id == 'distribuidor':
            estado_txt = "★ DISTRIBUIDOR ★"

        mapped = {
            'id': str(pedido.get('id')),
            'fecha_pedido': fecha,
            'cliente_nombre': pedido.get('cliente_nombre') or pedido.get('contacto_nombre') or 'Anon',
            'producto_nombre': pedido.get('linea_producto_nombre') or '',
            'usuario_nombre': pedido.get('usuario_nombre') or '',
            'num_lineas': str(pedido.get('num_lineas', 0)),
            'estado': estado_txt,
            'notas': pedido.get('notas_generales') or '',
            '_data': pedido
        }

        # Color de texto si está entregado (usando color de la config global si es posible)
        if estado_id == 'entregado':
            global_colors = load_colors('global')
            # text_disabled suele ser un gris oscuro/medio apropiado
            mapped['_row_fg'] = global_colors.get('text_disabled', '#666666')
        
        return mapped

    def _on_cambiar_estado(self):
        """Cambiar el estado del pedido seleccionado al estado elegido en el combo."""
        sel = self.nav_list.get_selected_item()
        if not sel:
            ToastWidget.show(self.container, "Seleccione un pedido de la lista", tipo='warning')
            return
            
        nuevo_estado_txt = self.estado_var.get()
        if nuevo_estado_txt == 'TODOS':
            ToastWidget.show(self.container, "Seleccione un estado específico en el combo", tipo='warning')
            return
            
        pedido = sel.get('_data')
        nuevo_estado = nuevo_estado_txt.lower()
        
        if self.service.actualizar_estado(pedido['id'], nuevo_estado):
            ToastWidget.show(self.container, f"Pedido #{pedido['id']} actualizado a {nuevo_estado.upper()}", tipo='success')
            self._on_search()
        else:
            ToastWidget.show(self.container, "No se pudo actualizar el estado", tipo='error')

    def _on_nuevo_pedido(self):
        """Navegar a la subvista de creación de pedido."""
        if self.owner and hasattr(self.owner, 'show_crear_pedido'):
            self.owner.show_crear_pedido()

    def _on_item_double_click(self, item_data: dict):
        """Doble click: Modificar pedido."""
        self._on_modificar_pedido()

    def _on_modificar_pedido(self):
        """Navegar a la subvista de creación de pedido en modo edición."""
        sel = self.nav_list.get_selected_item()
        if not sel:
            ToastWidget.show(self.container, "Seleccione un pedido para modificar", tipo='warning')
            return
            
        pedido = sel.get('_data')
        if self.owner and hasattr(self.owner, 'show_crear_pedido'):
            self.owner.show_crear_pedido(pedido_id=pedido['id'])
