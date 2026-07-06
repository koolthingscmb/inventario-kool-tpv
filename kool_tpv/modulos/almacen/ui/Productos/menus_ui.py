import logging
import tkinter as tk
import customtkinter as ctk
import unicodedata
from typing import Optional, List, Dict

from kool_tpv.modulos.almacen.services.menu_service import MenuService
from kool_tpv.base_datos.categoria_service import CategoriaService
from kool_tpv.base_datos.tipo_service import TipoService
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
from kool_tpv.utils.sku_generator import generate_sku
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db

logger = logging.getLogger(__name__)

class MenusUI:
    def __init__(self, parent, db=None, owner=None, keyboard_manager=None, module_name: str = 'almacen'):
        self.parent = parent
        self.owner = owner
        self.db = db
        self.module_name = module_name
        self.keyboard_mgr = keyboard_manager
        
        self.service = MenuService(db)
        self.categoria_service = CategoriaService(db)
        self.tipo_service = TipoService(db)
        self.producto_service = ProductoService(db)
        self.proveedor_service = ProveedorService(db)
        
        from kool_tpv.utils.config_loader import load_colors
        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {'background': '#1a1a1a', 'text': '#00FF00', 'border': '#00FF00', 'primary': '#00FF00', 'secondary': '#00FF00', 'light': '#00AA00', 'accent': '#00FF00', 'error': '#FF0000', 'warning': '#FFFF00'}

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#1a1a1a'))
        
        # Estado interno
        self.current_menu_id = None
        self.componentes_seleccionados = [] # List[dict] con {id, nombre, sku, cantidad}
        self.comp_qty_entries = {} # {idx: entry_widget}
        
        self._setup_ui()
        self._load_initial_data()

    def get_widget(self):
        return self.container

    def _setup_ui(self):
        # Layout principal: Izquierda (lista) - Derecha (editor)
        self.main_split = ctk.CTkFrame(self.container, fg_color='transparent')
        self.main_split.pack(fill='both', expand=True, padx=10, pady=10)
        
        # --- PANEL IZQUIERDO ---
        self.left_panel = ctk.CTkFrame(self.main_split, width=450, fg_color=self.colors.get('background', '#1a1a1a'), border_width=1, border_color=self.colors.get('border', '#333'))
        self.left_panel.pack(side='left', fill='y', padx=(0, 10))
        self.left_panel.pack_propagate(False)
        
        # Buscador de menús
        self.menu_search_var = tk.StringVar()
        self.menu_search_entry = ctk.CTkEntry(
            self.left_panel,
            textvariable=self.menu_search_var,
            placeholder_text='Buscar menú... (Enter)',
            height=35,
            fg_color=self.colors.get('background', '#1a1a1a'),
            text_color=self.colors.get('text', '#00FF00'),
            border_color=self.colors.get('border', '#00FF00')
        )
        self.menu_search_entry.pack(fill='x', padx=10, pady=10)
        self.menu_search_entry.bind('<Return>', lambda e: self._on_search_menus())
        
        # Lista de menús
        columns = [
            ('nombre', 200, 'NOMBRE'),
            ('pvp', 80, 'PVP'),
            ('num_componentes', 100, 'COMPON.')
        ]
        
        self.menus_list = SearchablePaginatedNavList(
            parent=self.left_panel,
            columns=columns,
            search_function=self._buscar_menuses,
            map_function=self._map_menu_row,
            module_name=self.module_name,
            on_double_click=self._on_menu_select,
            keyboard_manager=self.keyboard_mgr
        )
        self.menus_list.pack(fill='both', expand=True, padx=5, pady=5)
        
        # --- PANEL DERECHO (3 ZONAS: Form 20%, Buscador 40%, Componentes 40%) ---
        self.right_panel = ctk.CTkFrame(self.main_split, fg_color=self.colors.get('background', '#1a1a1a'), border_width=1, border_color=self.colors.get('border', '#333'))
        self.right_panel.pack(side='right', fill='both', expand=True)
        
        # 1. ZONA FORMULARIO (20%)
        self.top_area = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        self.top_area.place(relx=0, rely=0, relwidth=1, relheight=0.20)
        
        # Título sección
        ctk.CTkLabel(self.top_area, text='DATOS DEL MENÚ', font=get_font('subtitle', module=self.module_name), text_color=self.colors.get('primary')).pack(anchor='w', padx=10, pady=(5, 5))
        
        # Grid de 3 columnas para campos básicos
        self.form_frame = ctk.CTkFrame(self.top_area, fg_color='transparent')
        self.form_frame.pack(fill='both', expand=True, padx=10)
        for i in range(3): self.form_frame.columnconfigure(i*2 + 1, weight=1)
        
        # Fila 0: Nombre, PVP, SKU
        self.e_nombre = self._add_field_grid(self.form_frame, 'Nombre:', 0, 0)
        self.e_nombre.bind('<FocusOut>', lambda e: self._auto_generate_sku())
        self.e_pvp = self._add_field_grid(self.form_frame, 'PVP (€):', 0, 1)
        self.e_sku = self._add_field_grid(self.form_frame, 'SKU:', 0, 2, placeholder='Auto-generado')
        
        # Fila 1: Categoría, Tipo, Proveedor
        self.cb_categoria = self._add_combo_field_grid(self.form_frame, 'Categoría:', 1, 0, self.categoria_service.get_all())
        self.cb_categoria.entry.bind('<FocusOut>', lambda e: self._auto_generate_sku())
        self.cb_categoria.entry.bind('<<SearchableComboSelected>>', lambda e: self._auto_generate_sku())
        
        self.cb_tipo = self._add_combo_field_grid(self.form_frame, 'Tipo:', 1, 1, self.tipo_service.get_all_tipos())
        self.cb_tipo.entry.bind('<FocusOut>', lambda e: self._auto_generate_sku())
        self.cb_tipo.entry.bind('<<SearchableComboSelected>>', lambda e: self._auto_generate_sku())
        
        self.cb_proveedor = self._add_combo_field_grid(self.form_frame, 'Proveedor:', 1, 2, self.proveedor_service.get_all_proveedores())
        
        # 2. ZONA BUSCADOR (40%)
        self.mid_area = ctk.CTkFrame(self.right_panel, fg_color='transparent', border_width=1, border_color=self.colors.get('border', '#333'))
        self.mid_area.place(relx=0, rely=0.20, relwidth=1, relheight=0.4)
        
        ctk.CTkLabel(self.mid_area, text='BUSCADOR DE COMPONENTES', font=get_font('subtitle', module=self.module_name), text_color=self.colors.get('primary')).pack(anchor='w', padx=10, pady=5)
        
        self.comp_search_frame = ctk.CTkFrame(self.mid_area, fg_color='transparent')
        self.comp_search_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        self.comp_search_var = tk.StringVar()
        self.comp_search_entry = ctk.CTkEntry(
            self.comp_search_frame,
            textvariable=self.comp_search_var,
            placeholder_text='Buscar producto para añadir... (Enter)',
            height=35,
            fg_color=self.colors.get('background', '#1a1a1a'),
            text_color=self.colors.get('text', '#00FF00'),
            border_color=self.colors.get('border', '#00FF00')
        )
        self.comp_search_entry.pack(fill='x', expand=True)
        self.comp_search_entry.bind('<Return>', lambda e: self._on_search_component_enter())
        
        comp_columns = [
            ('nombre', 250, 'PRODUCTO'),
            ('sku', 150, 'SKU'),
            ('stock', 80, 'STOCK')
        ]
        self.comp_results_frame = ctk.CTkFrame(self.mid_area, fg_color='transparent')
        self.comp_results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.comp_search_results = SearchablePaginatedNavList(
            parent=self.comp_results_frame,
            columns=comp_columns,
            search_function=self._buscar_productos_comp,
            map_function=self._map_prod_comp_row,
            module_name=self.module_name,
            on_double_click=self._on_comp_add_select,
            keyboard_manager=self.keyboard_mgr,
            page_limit=10
        )
        self.comp_search_results.pack(fill='both', expand=True)
        
        # 3. ZONA COMPONENTES AÑADIDOS (40%)
        self.bottom_area = ctk.CTkFrame(self.right_panel, fg_color='transparent')
        self.bottom_area.place(relx=0, rely=0.60, relwidth=1, relheight=0.40)
        
        ctk.CTkLabel(self.bottom_area, text='COMPONENTES DEL MENÚ', font=get_font('subtitle', module=self.module_name), text_color=self.colors.get('primary')).pack(anchor='w', padx=10, pady=5)
        
        self.comp_list_scroll = ctk.CTkScrollableFrame(self.bottom_area, fg_color='transparent')
        self.comp_list_scroll.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.comp_list_frame = ctk.CTkFrame(self.comp_list_scroll, fg_color='transparent')
        self.comp_list_frame.pack(fill='x')
        
        # --- BOTONES PIE ---
        self.footer = ctk.CTkFrame(self.right_panel, fg_color='transparent', height=50)
        self.footer.pack(fill='x', side='bottom', padx=20, pady=10)
        
        self.btn_nuevo = ButtonFactory.create_button(self.footer, text='NUEVO', command=self._on_nuevo, style_key='action_secondary')
        self.btn_nuevo.pack(side='left', padx=10)
        
        self.btn_eliminar = ButtonFactory.create_button(self.footer, text='ELIMINAR', command=self._on_eliminar, style_key='action_danger')
        self.btn_eliminar.pack(side='left', padx=10)
        
        self.btn_guardar = ButtonFactory.create_button(self.footer, text='GUARDAR MENÚ', command=self._on_guardar, style_key='action_primary')
        self.btn_guardar.pack(side='right', padx=10)

    def _add_field_grid(self, parent, label, row, col, placeholder=''):
        ctk.CTkLabel(parent, text=label, text_color=self.colors.get('text')).grid(row=row, column=col*2, sticky='w', padx=5, pady=2)
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            fg_color=self.colors.get('background'),
            text_color=self.colors.get('text'),
            border_color=self.colors.get('border')
        )
        entry.grid(row=row, column=col*2 + 1, sticky='ew', padx=5, pady=2)
        return entry

    def _add_combo_field_grid(self, parent, label, row, col, options_data):
        ctk.CTkLabel(parent, text=label, text_color=self.colors.get('text')).grid(row=row, column=col*2, sticky='w', padx=5, pady=2)
        options = [(o['id'], o['nombre']) for o in options_data]
        combo = SearchableCombo(parent, options=options)
        combo.grid(row=row, column=col*2 + 1, sticky='ew', padx=5, pady=2)
        return combo

    def _load_initial_data(self):
        self._on_nuevo()
        self._on_search_menus()

    def _auto_generate_sku(self):
        """Genera automáticamente el SKU si el producto es nuevo."""
        if self.current_menu_id is not None:
            return

        nombre = self.e_nombre.get().strip()
        cat_nombre = self.cb_categoria._var.get().strip()
        tipo_nombre = self.cb_tipo._var.get().strip()

        if nombre and cat_nombre and tipo_nombre:
            try:
                new_sku = generate_sku(self.db, cat_nombre, tipo_nombre, nombre)
                self.e_sku.delete(0, 'end')
                self.e_sku.insert(0, new_sku)
            except Exception:
                logger.exception("Error auto-generando SKU")

    def _on_nuevo(self):
        self.current_menu_id = None
        self.e_nombre.delete(0, 'end')
        self.e_pvp.delete(0, 'end')
        self.e_sku.delete(0, 'end')
        self.cb_categoria.set('')
        self.cb_tipo.set('')
        self.cb_proveedor.set_by_id(9) # Default ID 9
        self.componentes_seleccionados = []
        self._refresh_component_list()
        self.btn_eliminar.configure(state='disabled')
        self.menu_search_entry.focus_set()

    def _on_search_menus(self):
        texto = self.menu_search_var.get()
        self.menus_list.search(texto)

    def _buscar_menuses(self, texto: str) -> List[dict]:
        all_menuses = self.service.listar_menuses()
        if not texto:
            return all_menuses
        
        # Filtrado simple sin tildes
        def normalize(s):
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
        
        t_norm = normalize(texto)
        return [m for m in all_menuses if t_norm in normalize(m['nombre']) or t_norm in normalize(m.get('sku', ''))]

    def _map_menu_row(self, item: dict) -> dict:
        return {
            'nombre': item['nombre'],
            'pvp': f"{item['pvp']:.2f}€",
            'num_componentes': f"{item['num_componentes']} uds",
            '_id': item['id']
        }

    def _on_menu_select(self, data: dict):
        mid = data.get('_id')
        if mid:
            detalle = self.service.get_detalle_menu(mid)
            if detalle:
                self.current_menu_id = mid
                self.e_nombre.delete(0, 'end')
                self.e_nombre.insert(0, detalle['nombre'])
                self.e_pvp.delete(0, 'end')
                self.e_pvp.insert(0, f"{detalle['pvp']:.2f}")
                self.e_sku.delete(0, 'end')
                self.e_sku.insert(0, detalle['sku'] or '')
                
                # Buscar nombres de cat/tipo para el combo
                cat_name = self._get_name_by_id(self.categoria_service.get_all(), detalle['categoria_id'])
                self.cb_categoria.set(cat_name)
                
                tipo_name = self._get_name_by_id(self.tipo_service.get_all_tipos(), detalle['tipo_id'])
                self.cb_tipo.set(tipo_name)
                
                # Cargar proveedor
                self.cb_proveedor.set_by_id(detalle['proveedor_id'])
                
                self.componentes_seleccionados = detalle['componentes']
                self._refresh_component_list()
                self.btn_eliminar.configure(state='normal')

    def _get_name_by_id(self, items, item_id):
        for it in items:
            if it['id'] == item_id:
                return it['nombre']
        return ''

    def _on_search_component_enter(self):
        texto = self.comp_search_var.get().strip()
        if not texto:
            return
        
        self.comp_search_results.search(texto)
        
        # Mover foco a la lista si hay resultados
        nav = getattr(self.comp_search_results, 'nav_list', None)
        if nav:
            nav._canvas.focus_set()

    def _buscar_productos_comp(self, texto: str) -> List[dict]:
        if not texto: return []
        return self.producto_service.buscar_productos_paginados(termino_busqueda=texto, limit=20)

    def _map_prod_comp_row(self, item: dict) -> dict:
        return {
            'nombre': item['nombre'],
            'sku': item['sku'],
            'stock': f"{item['stock_actual']} uds",
            '_obj': item
        }

    def _on_comp_add_select(self, data: dict):
        prod = data.get('_obj')
        if not prod: return
        
        # Evitar duplicados
        if any(c['componente_id'] == prod['id'] for c in self.componentes_seleccionados):
            ToastWidget.show(self.container, "Producto ya está en la receta", tipo='warning')
            return
            
        self.componentes_seleccionados.append({
            'componente_id': prod['id'],
            'nombre': prod['nombre'],
            'sku': prod['sku'],
            'cantidad': 1,
            'stock_actual': prod['stock_actual']
        })
        
        self.comp_search_var.set('')
        # Ya no ocultamos la lista tras seleccionar
        self._refresh_component_list()
        self.comp_search_entry.focus_set()

    def _refresh_component_list(self):
        for widget in self.comp_list_frame.winfo_children():
            widget.destroy()
        
        self.comp_qty_entries = {}
            
        if not self.componentes_seleccionados:
            ctk.CTkLabel(self.comp_list_frame, text='No hay componentes añadidos.', text_color='gray').pack(pady=10)
            return
            
        for i, comp in enumerate(self.componentes_seleccionados):
            row = ctk.CTkFrame(self.comp_list_frame, fg_color='transparent')
            row.pack(fill='x', pady=2)
            
            # Info básica
            info = f"{comp['nombre']} ({comp['sku']}) - Stock: {comp['stock_actual']}"
            ctk.CTkLabel(row, text=info, text_color=self.colors.get('text')).pack(side='left', padx=5)
            
            # Botón quitar
            btn_del = ctk.CTkButton(row, text='✕', width=30, height=25, fg_color='transparent', text_color='red', hover_color='#331111', command=lambda idx=i: self._remove_component(idx))
            btn_del.pack(side='right', padx=5)
            
            # Cantidad
            ctk.CTkLabel(row, text='Cant:', text_color=self.colors.get('text')).pack(side='right', padx=2)
            e_cant = ctk.CTkEntry(row, width=50, height=25)
            e_cant.insert(0, str(comp['cantidad']))
            e_cant.pack(side='right', padx=5)
            self.comp_qty_entries[i] = e_cant
            e_cant.bind('<FocusOut>', lambda e, idx=i, ent=e_cant: self._update_qty(idx, ent))
            e_cant.bind('<Return>', lambda e, idx=i, ent=e_cant: self._update_qty(idx, ent))

    def _remove_component(self, idx):
        self.componentes_seleccionados.pop(idx)
        self._refresh_component_list()

    def _update_qty(self, idx, entry):
        try:
            val = int(entry.get())
            if val < 1: val = 1
            self.componentes_seleccionados[idx]['cantidad'] = val
        except:
            pass

    def _on_guardar(self):
        # Asegurar que las cantidades de la UI se guardan en el estado
        for idx, entry in self.comp_qty_entries.items():
            try:
                val = int(entry.get())
                if val < 1: val = 1
                self.componentes_seleccionados[idx]['cantidad'] = val
            except:
                pass

        nombre = self.e_nombre.get().strip()
        pvp_str = self.e_pvp.get().strip().replace(',', '.')
        cat_id = self.cb_categoria.get_id()
        tipo_id = self.cb_tipo.get_id()
        prov_id = self.cb_proveedor.get_id()
        sku = self.e_sku.get().strip()
        
        if not nombre or not pvp_str or not cat_id or not tipo_id:
            ToastWidget.show(self.container, "Faltan datos obligatorios", tipo='error')
            return
            
        if not self.componentes_seleccionados:
            ToastWidget.show(self.container, "El menú debe tener componentes", tipo='error')
            return
            
        try:
            pvp = float(pvp_str)
        except:
            ToastWidget.show(self.container, "Precio no válido", tipo='error')
            return
            
        try:
            res = self.service.guardar_menu(
                nombre=nombre,
                pvp_euros=pvp,
                categoria_id=cat_id,
                tipo_id=tipo_id,
                componentes=self.componentes_seleccionados,
                producto_id=self.current_menu_id,
                sku=sku,
                proveedor_id=prov_id
            )
            if res:
                ToastWidget.show(self.container, "Menú guardado correctamente", tipo='success')
                self._load_initial_data()
        except Exception:
            logging.exception("Error guardando menú")
            ToastWidget.show(self.container, "Error al guardar menú", tipo='error')

    def _on_eliminar(self):
        if not self.current_menu_id: return
        
        # TODO: Mensaje de confirmación?
        try:
            if self.service.eliminar_menu(self.current_menu_id):
                ToastWidget.show(self.container, "Menú eliminado", tipo='success')
                self._load_initial_data()
        except Exception:
            logging.exception("Error eliminando menú")
            ToastWidget.show(self.container, "Error al eliminar menú", tipo='error')
