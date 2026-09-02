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
from kool_tpv.utils.dialogs import show_warning

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
        # Vincular esta instancia al widget para permitir refrescos desde fuera
        self.container._ui_object = self
        
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
            style_key='mini_outline_clientes',
            module='clientes',
            palette_key='primary'
        )
        self.btn_nuevo.pack(side='right', padx=5)

        self.btn_modificar = ButtonFactory.create_button(
            parent=top_frame,
            text='MODIFICAR',
            command=self._on_modificar_pedido,
            style_key='mini_outline_clientes',
            module='clientes',
            palette_key='secondary'
        )
        self.btn_modificar.pack(side='right', padx=5)

        self.btn_asociar_vale = ButtonFactory.create_button(
            parent=top_frame,
            text='Asignar Vale',
            command=self._on_asociar_vale,
            style_key='mini_outline_clientes',
            module='clientes',
            palette_key='secondary'
        )
        self.btn_asociar_vale.pack(side='right', padx=5)

        self.btn_usar_vale = ButtonFactory.create_button(
            parent=top_frame,
            text='USAR VALE',
            command=self._on_usar_vale,
            style_key='mini_outline_clientes',
            module='clientes',
            palette_key='secondary'
        )
        self.btn_usar_vale.pack(side='right', padx=5)

        # FILTERS
        filter_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=40)
        filter_frame.pack(fill='x', padx=12, pady=(6, 6))
        
        ctk.CTkLabel(
            filter_frame,
            text='Estado:',
            text_color=self.colors.get('text', COLOR_MATRIX),
            font=get_font('label', module=self.module_name)
        ).pack(side='left', padx=(0, 8))
        
        self.estado_var = tk.StringVar(value='PENDIENTE')
        
        # Diccionario de estados con iconos
        self.ESTADOS_UI = {
            'pendiente': '⏳',
            'distribuidor': '🚚',
            'avisado': '📞',
            'entregado': '✅',
            'cancelado': '❌'
        }
        
        estados_list = [f"{icon} ({name.upper()})" for name, icon in self.ESTADOS_UI.items()]
        
        self.combo_estado = ctk.CTkComboBox(
            filter_frame,
            values=estados_list,
            variable=self.estado_var,
            width=200,
            font=get_font('label', module=self.module_name)
        )
        self.combo_estado.pack(side='left', padx=(0, 10))

        self.btn_cambiar_estado = ButtonFactory.create_button(
            parent=filter_frame,
            text='CAMBIAR ESTADO',
            command=self._on_cambiar_estado,
            style_key='mini_outline_clientes',
            module='clientes',
            palette_key='accent'
        )
        self.btn_cambiar_estado.pack(side='left', padx=(0, 20))

        # LIST
        columns = [
            ('id', 42, 'ID'),
            ('fecha_pedido', 88, 'FECHA'),
            ('vale', 50, '🎫'),
            ('cliente_nombre', 160, 'CLIENTE', True),
            ('producto_nombre', 200, 'PRODUCTO', True),
            ('usuario_nombre', 86, 'USER'),
            ('estado', 50, '📌'),
            ('notas', 50, '📝')
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
        if hasattr(self, 'btn_asociar_vale'): add_widget(self.btn_asociar_vale)
        if hasattr(self, 'btn_usar_vale'): add_widget(self.btn_usar_vale)
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

    def refresh(self):
        """Refrescar la lista de pedidos."""
        self._on_search()

    def _on_search(self):
        termino = (self.search_var.get() or '').strip()
        self.nav_list.search(termino)

    def _buscar_pedidos(self, texto: str):
        pedidos = self.service.get_pedidos(estado=None, termino=texto)
        return pedidos

    def _map_pedido(self, pedido: dict) -> dict:
        # Formatear fecha (DD-MM-YY)
        fecha = pedido.get('fecha_pedido', '')
        if fecha:
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                fecha = dt.strftime('%d-%m-%y')
            except Exception:
                pass
        
        # Icono de estado
        estado_id = pedido.get('estado', 'pendiente').lower()
        estado_icon = self.ESTADOS_UI.get(estado_id, '⏳')
        
        mapped = {
            'id': str(pedido.get('id')),
            'fecha_pedido': fecha,
            'cliente_nombre': pedido.get('cliente_nombre') or pedido.get('contacto_nombre') or 'Anon',
            'producto_nombre': pedido.get('linea_producto_nombre') or '',
            'usuario_nombre': pedido.get('usuario_nombre') or '',
            'estado': estado_icon,
            'vale': '🎟️' if pedido.get('vale_id') and estado_id != 'entregado' else '',
            'notas': '✅' if pedido.get('notas_generales') else '',
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
            
        nuevo_estado_full = self.estado_var.get()
        # Extraer el id del estado del formato "Icono (NOMBRE)"
        import re
        match = re.search(r'\((.*?)\)', nuevo_estado_full)
        if not match:
            ToastWidget.show(self.container, "Estado no válido", tipo='error')
            return
            
        nuevo_estado = match.group(1).lower()
        pedido = sel.get('_data')
        
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

    def _on_asociar_vale(self):
        """Abrir subvista de vales para asociar uno al pedido seleccionado."""
        sel = self.nav_list.get_selected_item()
        if not sel:
            ToastWidget.show(self.container, "Seleccione un pedido de la lista", tipo='warning')
            return

        pedido = sel.get('_data')
        pedido_id = pedido['id']

        try:
            from kool_tpv.modulos.tpv.subviews.vales_list_subview import ValesListSubView
            
            def _vincular_vale(vale_data):
                vale_id = vale_data.get('id')
                if not vale_id: return
                
                if self.service.asociar_vale(pedido_id, vale_id):
                    ToastWidget.show(self.container, f"Vale asociado al pedido #{pedido_id}", tipo='success')
                    # Cerrar subview de vales (pop)
                    if self.owner and hasattr(self.owner, 'pop_subview'):
                        self.owner.pop_subview()
                    self._on_search() # Recargar lista
                else:
                    ToastWidget.show(self.container, "Error al asociar el vale", tipo='error')

            if self.owner and hasattr(self.owner, 'push_subview'):
                subview = ValesListSubView(
                    parent=self.parent,
                    view=self.owner,
                    module_name='tpv',
                    on_select=_vincular_vale
                )
                self.owner.push_subview(subview, "ASOCIAR VALE A PEDIDO")
        except Exception:
            logging.exception('Error abriendo ValesListSubView desde PedidosUI')

    def _on_usar_vale(self):
        """Carga el vale asociado al pedido en el TPV para finalizar la venta."""
        sel = self.nav_list.get_selected_item()
        if not sel:
            ToastWidget.show(self.container, "Seleccione un pedido de la lista", tipo='warning')
            return

        pedido = sel.get('_data')
        vale_id = pedido.get('vale_id')

        if not vale_id:
            ToastWidget.show(self.container, "Este pedido no tiene un vale asociado", tipo='warning')
            return

        # 1. Obtener datos del vale
        try:
            from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
            vale_service = ValeDevolucionService()
            vale_data = vale_service.obtener_por_id(vale_id)
            if not vale_data:
                ToastWidget.show(self.container, "No se encontró el archivo del vale", tipo='error')
                return
        except Exception:
            logging.exception("Error cargando vale")
            return

        # 2. Acceder al carrito y aplicar vale
        try:
            # El carrito reside en TpvView (self.owner)
            if hasattr(self.owner, 'carrito_service'):
                self.owner.carrito_service.aplicar_vale(vale_data)
                
                # Refrescar el visor del carrito (TicketCarrito)
                ticket = getattr(self.owner, 'ticket_widget', None)
                if ticket and hasattr(ticket, 'update_carrito'):
                    ticket.update_carrito()
                
                # 3. Volver al TPV (cerrando esta sub-vista de pedidos)
                if hasattr(self.owner, 'pop_subview'):
                    self.owner.pop_subview()
                    # Mostrar mensaje de éxito en la vista que queda visible
                    ToastWidget.show(self.owner, "Vale aplicado al carrito", tipo='success')
            else:
                ToastWidget.show(self.container, "No se pudo acceder al carrito del TPV", tipo='error')
            
        except Exception:
            logging.exception("Error al aplicar vale en el TPV")
            ToastWidget.show(self.container, "Error al procesar el vale", tipo='error')

    def _on_modificar_pedido(self):
        """Navegar a la subvista de creación de pedido en modo edición."""
        sel = self.nav_list.get_selected_item()
        if not sel:
            ToastWidget.show(self.container, "Seleccione un pedido para modificar", tipo='warning')
            return
            
        pedido = sel.get('_data')
        if self.owner and hasattr(self.owner, 'show_crear_pedido'):
            self.owner.show_crear_pedido(pedido_id=pedido['id'])
