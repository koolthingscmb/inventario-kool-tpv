"""Subvista para la creación de un nuevo pedido especial."""
import logging
import tkinter as tk
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.modulos.clientes.cliente_service import ClienteService
from kool_tpv.modulos.clientes.services.pedidos_service import PedidosService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.config_loader import load_colors, load_layout_config, create_action_button
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.base_datos.usuario_service import UsuarioService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.modulos.almacen.tipo_repository import TipoRepository

logger = logging.getLogger(__name__)

class CrearPedidoUI:
    def __init__(self, parent, db=None, owner=None, keyboard_manager=None, cliente_inicial_id=None, pedido_id=None):
        self.parent = parent
        self.owner = owner  # ClientesView
        self.db = db
        self.keyboard_mgr = keyboard_manager
        self.pedido_id = pedido_id
        
        self.prod_service = ProductoService(db)
        self.cli_service = ClienteService(db)
        self.ped_service = PedidosService(db)
        self.user_service = UsuarioService(db)
        self.prov_service = ProveedorService(db)
        self.tipo_repo = TipoRepository(db)
        
        self.colors_almacen = load_colors('almacen')
        self.colors_clientes = load_colors('clientes')
        
        self.container = ctk.CTkFrame(self.parent, fg_color=COLOR_BG_TERMINAL)
        
        # Estado de la UI
        self.selected_cliente = None
        self.selected_producto = None
        self.lineas_widgets = [] # List of dicts with entries
        self.current_estado = 'pendiente'
        
        self._build_ui()
        
        # Cargar cliente inicial si existe
        if cliente_inicial_id:
            cliente = self.cli_service.get_cliente(cliente_inicial_id)
            if cliente:
                self._on_cliente_selected(cliente)

        # Cargar pedido si estamos en modo edición
        if self.pedido_id:
            self._cargar_pedido(self.pedido_id)

    def get_widget(self):
        return self.container

    def _build_ui(self):
        # ZONA 1: Buscador Productos + Usuario
        zone1 = ctk.CTkFrame(self.container, fg_color='transparent')
        zone1.pack(fill='both', expand=True, padx=10, pady=5)
        zone1.pack_propagate(False)
        zone1.configure(height=200) # Aproximadamente 25%
        
        # Fila superior de búsqueda y usuario
        top_search_row = ctk.CTkFrame(zone1, fg_color='transparent')
        top_search_row.pack(fill='x', pady=5)
        
        ctk.CTkLabel(top_search_row, text="BUSCAR PRODUCTO:").pack(side='left', padx=5)
        self.search_prod_var = tk.StringVar()
        self.entry_prod = ctk.CTkEntry(
            top_search_row, textvariable=self.search_prod_var,
            placeholder_text="Nombre o SKU (Enter)...",
            fg_color=self.colors_almacen.get('background'),
            text_color=self.colors_almacen.get('text'),
            border_color=self.colors_almacen.get('primary'),
            width=300,
            height=35
        )
        self.entry_prod.pack(side='left', padx=5)
        self.entry_prod.bind('<Return>', lambda e: self.nav_prod.search(self.search_prod_var.get()))

        ctk.CTkLabel(top_search_row, text="USUARIO:").pack(side='left', padx=15)
        usuarios = self.user_service.get_all_usuarios()
        user_opts = [(u['id'], u['nombre']) for u in usuarios]
        self.cb_usuario = SearchableCombo(top_search_row, options=user_opts, width=200, placeholder="Seleccionar usuario")
        self.cb_usuario.pack(side='left', padx=5)
        
        cols_prod = [('sku', 120, 'SKU'), ('nombre', 400, 'PRODUCTO'), ('pvp', 80, 'PVP'), ('stock_actual', 70, 'STOCK')]
        self.nav_prod = SearchablePaginatedNavList(
            zone1, columns=cols_prod, 
            search_function=lambda t: self.prod_service.buscar_productos_paginados(termino_busqueda=t, limit=50),
            map_function=self._map_prod, module_name='almacen',
            on_double_click=self._on_prod_selected, layout_config=load_layout_config()
        )
        self.nav_prod.pack(fill='both', expand=True)
        
        # ZONA 2: Buscador Clientes (25%)
        zone2 = ctk.CTkFrame(self.container, fg_color='transparent')
        zone2.pack(fill='both', expand=True, padx=10, pady=5)
        zone2.pack_propagate(False)
        zone2.configure(height=200)
        
        row_busqueda_cli = ctk.CTkFrame(zone2, fg_color='transparent')
        row_busqueda_cli.pack(fill='x', pady=(0, 5))
        
        ctk.CTkLabel(row_busqueda_cli, text="BUSCAR CLIENTE:").pack(side='left', padx=5)
        
        self.search_cli_var = tk.StringVar()
        self.entry_cli = ctk.CTkEntry(
            row_busqueda_cli, textvariable=self.search_cli_var,
            placeholder_text="Nombre, Teléfono, Email (Enter)...",
            fg_color=self.colors_clientes.get('background'),
            text_color=self.colors_clientes.get('text'),
            border_color=self.colors_clientes.get('primary'),
            height=35
        )
        self.entry_cli.pack(side='left', fill='x', expand=True, padx=5)
        self.entry_cli.bind('<Return>', lambda e: self.nav_cli.search(self.search_cli_var.get()))
        
        cols_cli = [('id', 50, 'ID'), ('nombre', 300, 'CLIENTE'), ('telefono', 140, 'TELÉFONO'), ('email', 250, 'EMAIL')]
        self.nav_cli = SearchablePaginatedNavList(
            zone2, columns=cols_cli,
            search_function=lambda t: self.cli_service.buscar_clientes(t),
            map_function=self._map_cli, module_name='clientes',
            on_double_click=self._on_cliente_selected, layout_config=load_layout_config()
        )
        self.nav_cli.pack(fill='both', expand=True)

        # ZONA 3: GRID Datos del Pedido
        zone3 = ctk.CTkScrollableFrame(self.container, fg_color='transparent')
        zone3.pack(fill='both', expand=True, padx=10, pady=5)
        self.grid_container = zone3
        
        # Header del grid con label y botón +
        header_grid = ctk.CTkFrame(zone3, fg_color='transparent')
        header_grid.pack(fill='x', pady=5)
        ctk.CTkLabel(header_grid, text="DATOS DEL PEDIDO", font=('Arial', 14, 'bold')).pack(side='left', padx=5)
        
        # Label de Pedido Finalizado (oculto por defecto)
        self.lbl_finalizado = ctk.CTkLabel(
            header_grid, text="PEDIDO FINALIZADO", 
            font=('Arial', 14, 'bold'),
            text_color="#FF4444" # Rojo
        )
        # Se posiciona pero no se muestra inicialmente
        
        ButtonFactory.create_button(
            parent=header_grid,
            text="+ AÑADIR PRODUCTO",
            command=self._add_producto_row,
            style_key='action_primary',
            width=150
        ).pack(side='right')

        # Fila 1: Datos Cliente (Fija)
        self.cli_row = ctk.CTkFrame(zone3, fg_color='#333333', height=60)
        self.cli_row.pack(fill='x', pady=2)
        
        ctk.CTkLabel(self.cli_row, text="CLIENTE:", width=80).pack(side='left', padx=5)
        self.e_cli_nombre = ctk.CTkEntry(self.cli_row, placeholder_text="Nombre...", width=160) # Reducido más para hueco vale
        self.e_cli_nombre.pack(side='left', padx=5)
        
        ctk.CTkLabel(self.cli_row, text="TEL:", width=40).pack(side='left', padx=5)
        self.e_cli_tel = ctk.CTkEntry(self.cli_row, placeholder_text="Tel...", width=100)
        self.e_cli_tel.pack(side='left', padx=5)
        
        ctk.CTkLabel(self.cli_row, text="NOTA:", width=40).pack(side='left', padx=5)
        self.e_cli_nota = ctk.CTkEntry(self.cli_row, placeholder_text="Nota...", width=180)
        self.e_cli_nota.pack(side='left', padx=5)

        # SECCIÓN VALE (Solo lectura)
        ctk.CTkLabel(self.cli_row, text="VALE:", width=50, text_color="#FFFFFF").pack(side='left', padx=(15, 5))
        self.lbl_vale_nombre = ctk.CTkLabel(self.cli_row, text="-", width=180, anchor="w", text_color="#55FF55", font=("Arial", 12, "bold"))
        self.lbl_vale_nombre.pack(side='left', padx=5)
        
        ctk.CTkLabel(self.cli_row, text="VALOR:", width=50, text_color="#FFFFFF").pack(side='left', padx=5)
        self.lbl_vale_valor = ctk.CTkLabel(self.cli_row, text="- €", width=80, anchor="w", text_color="#55FF55", font=("Arial", 12, "bold"))
        self.lbl_vale_valor.pack(side='left', padx=5)
        
        # Guardamos el ID del vale internamente
        self.current_vale_id = None
        
        # Añadir primera fila de producto por defecto
        self._add_producto_row()

        # ZONA 4: Footer
        footer = ctk.CTkFrame(self.container, fg_color='transparent', height=60)
        footer.pack(fill='x', side='bottom', padx=10, pady=10)
        
        self.btn_guardar = create_action_button(footer, 'guardar', self._on_guardar)
        self.btn_guardar.pack(side='right', padx=10)

        self.btn_whatsapp = create_action_button(footer, 'whatsapp', self._on_whatsapp)
        self.btn_whatsapp.pack(side='right', padx=10)
        
        self.btn_cancelar = create_action_button(footer, 'cancelar', self._on_cancelar)
        self.btn_cancelar.pack(side='left', padx=10)
        
        # Foco inicial
        self.entry_prod.after(100, lambda: self.entry_prod.focus_set())
        
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
            logging.exception("Error vinculando Tab en CrearPedidoUI")

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
            # Si es CTkEntry o similar, coger el _entry interno
            if hasattr(w, '_entry'): widgets.append(w._entry)
            elif hasattr(w, '_canvas'): widgets.append(w._canvas)
            else: widgets.append(w)

        # 1. Buscadores superiores
        if hasattr(self, 'entry_prod'): add_widget(self.entry_prod)
        if hasattr(self, 'cb_usuario'): add_widget(self.cb_usuario.entry)
        if hasattr(self, 'entry_cli'): add_widget(self.entry_cli)
        
        # 2. Datos del cliente
        if hasattr(self, 'e_cli_nombre'): add_widget(self.e_cli_nombre)
        if hasattr(self, 'e_cli_tel'): add_widget(self.e_cli_tel)
        if hasattr(self, 'e_cli_nota'): add_widget(self.e_cli_nota)
        
        # 3. Líneas de productos
        for w in self.lineas_widgets:
            add_widget(w['e_sku'])
            add_widget(w['e_prod'])
            add_widget(w['cb_tipo'].entry)
            add_widget(w['cb_prov'].entry)
            add_widget(w['e_cant'])
            
        # 4. Botones inferiores
        if hasattr(self, 'btn_cancelar'): add_widget(self.btn_cancelar)
        if hasattr(self, 'btn_whatsapp'): add_widget(self.btn_whatsapp)
        if hasattr(self, 'btn_guardar'): add_widget(self.btn_guardar)
        
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

    def _add_producto_row(self, data=None):
        row = ctk.CTkFrame(self.grid_container, fg_color='#2A2A2A', height=50)
        row.pack(fill='x', pady=2)
        
        ctk.CTkLabel(row, text="SKU:", width=40).pack(side='left', padx=2)
        e_sku = ctk.CTkEntry(row, placeholder_text="SKU...", width=100)
        e_sku.pack(side='left', padx=2)
        e_sku.bind('<Return>', lambda e, r=row: self._on_sku_enter(e, r))

        ctk.CTkLabel(row, text="PRODUCTO:", width=80).pack(side='left', padx=2)
        e_prod = ctk.CTkEntry(row, placeholder_text="Producto...", width=240) # Reducido 20% (300 -> 240)
        e_prod.pack(side='left', padx=2)
        
        ctk.CTkLabel(row, text="TIPO:", width=40).pack(side='left', padx=2)
        # SearchableCombo para Tipo
        tipos = self.tipo_repo.get_all()
        tipo_opts = [(t['id'], t['nombre']) for t in tipos]
        cb_tipo = SearchableCombo(row, options=tipo_opts, width=100, placeholder="Tipo...") # Reducido 30% (150 -> 100)
        cb_tipo.pack(side='left', padx=2)
        
        ctk.CTkLabel(row, text="PROV:", width=40).pack(side='left', padx=2)
        # SearchableCombo para Proveedor
        provs = self.prov_service.get_all_proveedores()
        prov_opts = [(p['id'], p['nombre']) for p in provs]
        cb_prov = SearchableCombo(row, options=prov_opts, width=120, placeholder="Prov...") # Reducido 30% (180 -> 120)
        cb_prov.pack(side='left', padx=2)
        
        ctk.CTkLabel(row, text="CANT:", width=40).pack(side='left', padx=2)
        e_cant = ctk.CTkEntry(row, width=50)
        e_cant.insert(0, "1")
        e_cant.pack(side='left', padx=2)
        
        btn_del = ctk.CTkButton(row, text="X", width=30, fg_color="#FF4444", 
                               command=lambda r=row: self._remove_row(r))
        btn_del.pack(side='right', padx=5)
        
        row_data = {
            'frame': row,
            'producto_id': None,
            'e_sku': e_sku,
            'e_prod': e_prod,
            'cb_tipo': cb_tipo,
            'cb_prov': cb_prov,
            'e_cant': e_cant
        }
        
        if data:
            row_data['producto_id'] = data.get('id')
            sku_val = str(data.get('sku') or '')
            nombre_val = str(data.get('nombre') or '')
            e_sku.insert(0, sku_val)
            e_prod.insert(0, nombre_val)
            
            # Intentar rellenar tipo y proveedor por ID o nombre
            t_id = data.get('tipo_id') or data.get('tipo')
            if t_id:
                if isinstance(t_id, int): cb_tipo.set_by_id(t_id)
                else: cb_tipo.set(str(t_id))
                
            p_id = data.get('proveedor_id') or data.get('proveedor_nombre')
            if p_id:
                if isinstance(p_id, int): cb_prov.set_by_id(p_id)
                else: cb_prov.set(str(p_id))
            
        self.lineas_widgets.append(row_data)

    def _remove_row(self, row_frame):
        if len(self.lineas_widgets) <= 1:
            ToastWidget.show(self.container, "Debe haber al menos un producto", tipo='warning')
            return
        for i, item in enumerate(self.lineas_widgets):
            if item['frame'] == row_frame:
                item['frame'].destroy()
                self.lineas_widgets.pop(i)
                break

    def _map_prod(self, p):
        return {'id': p['id'], 'sku': p['sku'], 'nombre': p['nombre'], 
                'pvp': f"{p['pvp']:.2f}€", 'stock_actual': p['stock_actual'],
                'tipo_id': p.get('tipo_id'), 'proveedor_id': p.get('proveedor_id'),
                'tipo': p.get('tipo', ''), 'proveedor_nombre': p.get('proveedor_nombre', ''),
                '_data': p}

    def _map_cli(self, c):
        return {'id': c['id'], 'nombre': c['nombre'], 'telefono': c.get('telefono', ''), 
                'email': c.get('email', ''), '_data': c}

    def _on_prod_selected(self, item_data):
        prod = item_data.get('_data')
        # Asignar a la última fila vacía o crear una nueva
        target_row = None
        for r in self.lineas_widgets:
            if not r['e_prod'].get() and not r['e_sku'].get():
                target_row = r
                break
        
        if not target_row:
            self._add_producto_row(prod)
        else:
            self._fill_row_with_prod(target_row, prod)
        
        ToastWidget.show(self.container, f"Producto añadido: {prod['nombre']}", tipo='success')

    def _fill_row_with_prod(self, row_data, prod):
        """Rellenar una fila con los datos de un producto."""
        row_data['producto_id'] = prod['id']
        row_data['e_sku'].delete(0, 'end')
        row_data['e_sku'].insert(0, prod.get('sku', ''))
        row_data['e_prod'].delete(0, 'end')
        row_data['e_prod'].insert(0, prod['nombre'])
        
        # Rellenar tipo y proveedor por ID (ahora disponible en buscar)
        if prod.get('tipo_id'):
            row_data['cb_tipo'].set_by_id(prod['tipo_id'])
        elif prod.get('tipo'):
            row_data['cb_tipo'].set(prod['tipo'])
            
        if prod.get('proveedor_id'):
            row_data['cb_prov'].set_by_id(prod['proveedor_id'])
        elif prod.get('proveedor_nombre'):
            row_data['cb_prov'].set(prod['proveedor_nombre'])

    def _on_sku_enter(self, event, row_frame):
        """Al pulsar Enter en el campo SKU de una fila."""
        target_row = None
        for r in self.lineas_widgets:
            if r['frame'] == row_frame:
                target_row = r
                break
        
        if not target_row: return
        
        sku = target_row['e_sku'].get().strip()
        if not sku: return
        
        # Buscar producto por SKU
        from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
        repo = ProductoRepository(self.db)
        prod = repo.get_by_sku(sku) # Este devuelve el dict base
        
        if prod:
            # Obtener datos extendidos (tipo_nombre, etc)
            prod_full = self.prod_service.get_producto_completo(prod['id'])
            if prod_full:
                self._fill_row_with_prod(target_row, prod_full)
                ToastWidget.show(self.container, f"Producto encontrado: {prod_full['nombre']}", tipo='success')
            else:
                ToastWidget.show(self.container, f"Error cargando detalles de SKU {sku}", tipo='error')
        else:
            ToastWidget.show(self.container, f"SKU {sku} no encontrado", tipo='warning')

    def _on_cliente_selected(self, item_data):
        cli = item_data.get('_data') if isinstance(item_data, dict) and '_data' in item_data else item_data
        self.selected_cliente = cli
        self.e_cli_nombre.delete(0, 'end')
        self.e_cli_nombre.insert(0, cli['nombre'])
        self.e_cli_tel.delete(0, 'end')
        self.e_cli_tel.insert(0, cli.get('telefono', ''))
        ToastWidget.show(self.container, f"Cliente seleccionado: {cli['nombre']}", tipo='success')

    def _on_guardar(self):
        # 1. Cabecera
        cab = {
            'id': self.pedido_id,
            'cliente_id': self.selected_cliente['id'] if self.selected_cliente else None,
            'contacto_nombre': self.e_cli_nombre.get().strip(),
            'contacto_telefono': self.e_cli_tel.get().strip(),
            'notas_generales': self.e_cli_nota.get().strip(),
            'usuario_id': self.cb_usuario.get_id(),
            'estado': self.current_estado,
            'vale_id': self.current_vale_id
        }
        
        if not cab['contacto_nombre']:
            ToastWidget.show(self.container, "Falta nombre del cliente", tipo='error')
            return
            
        if not cab['usuario_id']:
            ToastWidget.show(self.container, "Debe introducir un Usuario", tipo='error')
            return
            
        # 2. Líneas
        lineas = []
        for w in self.lineas_widgets:
            nombre = w['e_prod'].get().strip()
            if not nombre: continue
            
            lineas.append({
                'producto_id': w['producto_id'],
                'nombre_manual': nombre,
                'tipo_id': w['cb_tipo'].get_id(),
                'proveedor_id': w['cb_prov'].get_id(),
                'tipo_manual': w['cb_tipo'].get(),
                'proveedor_manual': w['cb_prov'].get(),
                'cantidad': int(w['e_cant'].get() or 1),
                'estado_linea': 'pendiente'
            })
            
        if not lineas:
            ToastWidget.show(self.container, "El pedido no tiene productos", tipo='error')
            return
            
        res = self.ped_service.guardar_pedido(cab, lineas)
        if res['success']:
            ToastWidget.show(self.container, "PEDIDO GUARDADO CORRECTAMENTE", tipo='success')
            self._on_cancelar()
        else:
            ToastWidget.show(self.container, res['error'], tipo='error')

    def _on_cancelar(self):
        if self.owner and hasattr(self.owner, 'show_pedidos'):
            self.owner.show_pedidos()

    def _cargar_pedido(self, pedido_id):
        """Cargar datos de un pedido existente para modificar."""
        pedido = self.ped_service.get_pedido_por_id(pedido_id)
        if not pedido:
            ToastWidget.show(self.container, f"Error cargando pedido {pedido_id}", tipo='error')
            return
        
        # 1. Rellenar cabecera
        self.current_estado = pedido.get('estado', 'pendiente')
        
        # Mostrar label si está finalizado
        if self.current_estado == 'entregado':
            self.lbl_finalizado.pack(side='left', padx=20)
        else:
            self.lbl_finalizado.pack_forget()

        self.e_cli_nombre.delete(0, 'end')
        self.e_cli_nombre.insert(0, pedido.get('contacto_nombre', ''))
        self.e_cli_tel.delete(0, 'end')
        self.e_cli_tel.insert(0, pedido.get('contacto_telefono', ''))
        self.e_cli_nota.delete(0, 'end')
        self.e_cli_nota.insert(0, pedido.get('notas_generales', ''))

        # Cargar Vale si existe
        self.current_vale_id = pedido.get('vale_id')
        if self.current_vale_id:
            try:
                from kool_tpv.modulos.tpv.vale_devolucion_service import ValeDevolucionService
                from kool_tpv.base_datos.money_adapter import read_from_db
                from pathlib import Path as _Path
                
                vale_service = ValeDevolucionService()
                vale_data = vale_service.obtener_por_id(self.current_vale_id)
                
                if vale_data:
                    path_str = vale_data.get('path', '')
                    nombre_vale = _Path(path_str).stem if path_str else '?'
                    if nombre_vale.startswith('USADO_'): nombre_vale = nombre_vale[6:]
                    
                    importe = read_from_db(vale_data.get('importe_cents', 0))
                    
                    self.lbl_vale_nombre.configure(text=nombre_vale)
                    self.lbl_vale_valor.configure(text=f"{importe:.2f} €")
                else:
                    self.lbl_vale_nombre.configure(text="ID NO ENCONTRADO", text_color="#FF4444")
            except Exception:
                logger.exception("Error cargando vale en CrearPedidoUI")
        
        if pedido.get('usuario_id'):
            self.cb_usuario.set_by_id(pedido['usuario_id'])
            
        if pedido.get('cliente_id'):
            self.selected_cliente = self.cli_service.get_cliente(pedido['cliente_id'])
            
        # 2. Rellenar líneas
        lineas = self.ped_service.get_lineas_pedido(pedido_id)
        # Limpiar fila por defecto
        for w in self.lineas_widgets:
            w['frame'].destroy()
        self.lineas_widgets = []
        
        for lin in lineas:
            self._add_producto_row({
                'id': lin.get('producto_id'),
                'sku': lin.get('producto_sku_db'),
                'nombre': lin.get('nombre_manual'),
                'tipo_id': lin.get('tipo_id'),
                'tipo': lin.get('tipo_manual'),
                'proveedor_id': lin.get('proveedor_id'),
                'proveedor_nombre': lin.get('proveedor_manual')
            })
            # La cantidad se pone manual
            self.lineas_widgets[-1]['e_cant'].delete(0, 'end')
            self.lineas_widgets[-1]['e_cant'].insert(0, str(lin.get('cantidad', 1)))

    def _on_whatsapp(self):
        """Abrir diálogo de WhatsApp y enviar mensaje."""
        try:
            telefono = (self.e_cli_tel.get() or '').strip()
            cliente_data = {
                'nombre': (self.e_cli_nombre.get() or '').strip(),
                'telefono': telefono,
                'email': self.selected_cliente.get('email', '') if self.selected_cliente else ''
            }
            
            from kool_tpv.services.whatsapp_service import WhatsAppService
            WhatsAppService.enviar_mensaje(
                self.container, 
                self.db, 
                telefono, 
                cliente_data,
                pedido_id=self.pedido_id if hasattr(self, 'pedido_id') else None
            )

        except Exception:
            logger.exception('Error en _on_whatsapp')
            ToastWidget.show(self.container, 'ERROR AL ABRIR WHATSAPP', tipo='error')
