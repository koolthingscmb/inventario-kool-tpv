import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.modulos.configuracion.reset_service import ResetService
from kool_tpv.utils.widgets.tag_selector import TagSelector
from kool_tpv.utils.custom_dialog import show_warning, show_error
from kool_tpv.utils.widgets.notificaciones import ToastWidget


class ResetUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.service = ResetService(db)

        try:
            self.colors = load_colors(module_name)
        except Exception:
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        # CTkScrollableFrame.winfo_exists() devuelve 0 antes del primer ciclo del event loop.
        # Solución: CTkFrame externo como contenedor (winfo_exists siempre 1),
        # CTkScrollableFrame dentro para el scroll.
        self._outer = ctk.CTkFrame(parent, fg_color=bg)
        self.container = ctk.CTkScrollableFrame(self._outer, fg_color=bg)
        self.container.pack(fill='both', expand=True)

        # ADVERTENCIA HEADER
        warning_frame = ctk.CTkFrame(self.container, fg_color='#D32F2F', corner_radius=8)
        warning_frame.pack(fill='x', padx=20, pady=20)

        ctk.CTkLabel(
            warning_frame,
            text='⚠️ HERRAMIENTA DE DESARROLLO ⚠️',
            font=get_font('title', module=module_name),
            text_color='#FFFFFF'
        ).pack(pady=10)

        ctk.CTkLabel(
            warning_frame,
            text='Solo usar en pruebas. NUNCA en producción.',
            font=get_font('label', module=module_name),
            text_color='#FFCCCC'
        ).pack(pady=(0, 10))

        # Tabview principal
        self.tabview = ctk.CTkTabview(
            self.container, 
            fg_color=bg,
            segmented_button_fg_color=self.colors.get('surface', '#1A1A1A'),
            segmented_button_selected_color='#808080',
            segmented_button_selected_hover_color='#808080',
            segmented_button_unselected_color=self.colors.get('surface', '#1A1A1A'),
            segmented_button_unselected_hover_color=self.colors.get('surface', '#1A1A1A'),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        self.tabview.pack(fill='both', expand=True, padx=20, pady=10)

        # Crear pestañas
        self.tab_ventas = self.tabview.add('🛒 VENTAS')
        self.tab_catalogo = self.tabview.add('📦 CATÁLOGO')
        self.tab_clientes = self.tabview.add('👥 CLIENTES')
        self.tab_fiscal = self.tabview.add('📝 FISCAL')
        self.tab_produccion = self.tabview.add('⚙️ PRODUCCIÓN')
        self.tab_peligro = self.tabview.add('⚠️ PELIGRO')

        self._build_ventas_tab()
        self._build_catalogo_tab()
        self._build_clientes_tab()
        self._build_fiscal_tab()
        self._build_produccion_tab()
        self._build_peligro_tab()

    def _create_card(self, parent, title: str):
        """Helper para crear una tarjeta visual (Card)."""
        card = ctk.CTkFrame(
            parent, 
            fg_color=self.colors.get('surface', '#1A1A1A'),
            corner_radius=10,
            border_width=1,
            border_color=self.colors.get('border', '#333333')
        )
        card.pack(fill='x', padx=20, pady=10)
        
        ctk.CTkLabel(
            card,
            text=title,
            font=get_font('subtitle', module=self.module_name),
            text_color=self.colors.get('secondary', '#FFB74D')
        ).pack(anchor='w', padx=20, pady=(15, 10))
        
        return card

    def _build_ventas_tab(self):
        # Card Tickets
        card = self._create_card(self.tab_ventas, 'TICKETS Y VENTAS')
        
        frame = ctk.CTkFrame(card, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=(0, 15))
        
        btn = ButtonFactory.create_button(
            parent=frame, 
            text='BORRAR TODOS LOS TICKETS', 
            command=self._borrar_tickets_ui, 
            style_key='action_danger_small'
        )
        btn.pack(side='left', padx=(0, 15))
        
        self.check_tickets_reset = ctk.CTkCheckBox(
            frame, 
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text_dim', '#999999'),
            fg_color=self.colors.get('primary', '#2196F3'),
            hover_color=self.colors.get('primary_hover', '#1976D2')
        )
        self.check_tickets_reset.pack(side='left')

        # Card Cierres
        card_cierres = self._create_card(self.tab_ventas, 'CIERRES DE CAJA')
        frame_c = ctk.CTkFrame(card_cierres, fg_color='transparent')
        frame_c.pack(fill='x', padx=20, pady=(0, 15))
        
        btn_c = ButtonFactory.create_button(
            parent=frame_c, 
            text='BORRAR TODOS LOS CIERRES', 
            command=self._borrar_cierres_ui, 
            style_key='action_danger_small'
        )
        btn_c.pack(side='left', padx=(0, 15))
        
        self.check_cierres_reset = ctk.CTkCheckBox(
            frame_c, 
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text_dim', '#999999'),
            fg_color=self.colors.get('primary', '#2196F3')
        )
        self.check_cierres_reset.pack(side='left')

    def _build_catalogo_tab(self):
        # Card Productos
        card = self._create_card(self.tab_catalogo, 'CATÁLOGO DE PRODUCTOS')
        
        # Búsqueda manual (no real-time)
        search_frame = ctk.CTkFrame(card, fg_color='transparent')
        search_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.entry_search_prod = ctk.CTkEntry(
            search_frame,
            placeholder_text='Buscar producto (ENTER para buscar)...',
            font=get_font('label', module=self.module_name),
            fg_color=self.colors.get('background', '#000000'),
            border_color=self.colors.get('border', '#333333'),
            height=35
        )
        self.entry_search_prod.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.entry_search_prod.bind('<Return>', lambda e: self._do_search_productos())

        # Selector de resultados
        self.tag_selector_productos = TagSelector(
            card,
            module_name=self.module_name,
            placeholder='Productos encontrados...',
            fg_color='transparent'
        )
        self.tag_selector_productos.pack(fill='x', padx=20, pady=(0, 15))

        # Botones acción selectiva
        action_frame = ctk.CTkFrame(card, fg_color='transparent')
        action_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        btn_sel = ButtonFactory.create_button(
            parent=action_frame,
            text='BORRAR SELECCIONADOS',
            command=self._borrar_productos_selectivos,
            style_key='action_warning_small'
        )
        btn_sel.pack(side='left', padx=(0, 15))

        # Botones acción global
        global_frame = ctk.CTkFrame(card, fg_color='transparent')
        global_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        btn_all = ButtonFactory.create_button(
            parent=global_frame,
            text='BORRAR TODOS LOS PRODUCTOS',
            command=self._borrar_productos_todos,
            style_key='action_danger_small'
        )
        btn_all.pack(side='left', padx=(0, 15))
        
        self.check_prod_reset = ctk.CTkCheckBox(
            global_frame,
            text='Limpiar códigos de barras y secuencias',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text_dim', '#999999'),
            fg_color=self.colors.get('primary', '#2196F3')
        )
        self.check_prod_reset.pack(side='left')

    def _build_clientes_tab(self):
        # Card Clientes Selectivo
        card = self._create_card(self.tab_clientes, 'GESTIÓN DE CLIENTES')
        
        # Búsqueda manual
        search_frame = ctk.CTkFrame(card, fg_color='transparent')
        search_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.entry_search_cli = ctk.CTkEntry(
            search_frame,
            placeholder_text='Buscar cliente (ENTER para buscar)...',
            font=get_font('label', module=self.module_name),
            fg_color=self.colors.get('background', '#000000'),
            border_color=self.colors.get('border', '#333333'),
            height=35
        )
        self.entry_search_cli.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.entry_search_cli.bind('<Return>', lambda e: self._do_search_clientes())

        # Selector de resultados
        self.tag_selector_clientes = TagSelector(
            card,
            module_name=self.module_name,
            placeholder='Clientes encontrados...',
            fg_color='transparent'
        )
        self.tag_selector_clientes.pack(fill='x', padx=20, pady=(0, 15))

        # Botón reset selectivo
        btn_sel = ButtonFactory.create_button(
            parent=card,
            text='RESET ESTADÍSTICAS SELECCIONADOS',
            command=self._reset_clientes_selectivos,
            style_key='action_warning_small'
        )
        btn_sel.pack(padx=20, pady=(0, 15), anchor='w')

        # Card Global
        card_all = self._create_card(self.tab_clientes, 'ACCIONES GLOBALES')
        
        btn_all = ButtonFactory.create_button(
            parent=card_all,
            text='RESET ESTADÍSTICAS TODOS LOS CLIENTES',
            command=self._reset_clientes_todos,
            style_key='action_warning_small'
        )
        btn_all.pack(padx=20, pady=(0, 10), anchor='w')
        
        btn_pts = ButtonFactory.create_button(
            parent=card_all,
            text='BORRAR TODOS LOS MOVIMIENTOS DE PUNTOS',
            command=self._borrar_puntos_todos,
            style_key='action_danger_small'
        )
        btn_pts.pack(padx=20, pady=(0, 15), anchor='w')

    def _build_fiscal_tab(self):
        # Card Albaranes
        card_alb = self._create_card(self.tab_fiscal, 'ALBARANES')
        frame_alb = ctk.CTkFrame(card_alb, fg_color='transparent')
        frame_alb.pack(fill='x', padx=20, pady=(0, 15))
        
        btn_alb = ButtonFactory.create_button(parent=frame_alb, text='BORRAR TODOS', command=self._borrar_albaranes_ui, style_key='action_danger_small')
        btn_alb.pack(side='left', padx=(0, 15))
        
        self.check_alb_reset = ctk.CTkCheckBox(frame_alb, text='Resetear contador', font=get_font('label', module=self.module_name), text_color=self.colors.get('text_dim', '#999999'), fg_color=self.colors.get('primary', '#2196F3'))
        self.check_alb_reset.pack(side='left')

        # Card Facturas
        card_fac = self._create_card(self.tab_fiscal, 'FACTURAS')
        frame_fac = ctk.CTkFrame(card_fac, fg_color='transparent')
        frame_fac.pack(fill='x', padx=20, pady=(0, 15))
        
        btn_fac = ButtonFactory.create_button(parent=frame_fac, text='BORRAR TODAS', command=self._borrar_facturas_ui, style_key='action_danger_small')
        btn_fac.pack(side='left', padx=(0, 15))
        
        self.check_fac_reset = ctk.CTkCheckBox(frame_fac, text='Resetear contador', font=get_font('label', module=self.module_name), text_color=self.colors.get('text_dim', '#999999'), fg_color=self.colors.get('primary', '#2196F3'))
        self.check_fac_reset.pack(side='left')

    def _build_produccion_tab(self):
        # Card Órdenes
        card = self._create_card(self.tab_produccion, 'ÓRDENES Y STOCK DE PRODUCCIÓN')
        
        frame = ctk.CTkFrame(card, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=(0, 15))
        
        btn = ButtonFactory.create_button(parent=frame, text='BORRAR TODAS LAS ÓRDENES', command=self._borrar_produccion_ordenes, style_key='action_danger_small')
        btn.pack(side='left', padx=(0, 15))
        
        self.check_prod_seq = ctk.CTkCheckBox(frame, text='Resetear contadores (ID)', font=get_font('label', module=self.module_name), text_color=self.colors.get('text_dim', '#999999'), fg_color=self.colors.get('primary', '#2196F3'))
        self.check_prod_seq.pack(side='left')

        # Otras utilidades
        util_frame = ctk.CTkFrame(card, fg_color='transparent')
        util_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        ButtonFactory.create_button(parent=util_frame, text='LIMPIAR STOCK DISEÑOS', command=self._borrar_produccion_stock_disenos, style_key='action_warning_small').pack(side='left', padx=(0, 10))
        ButtonFactory.create_button(parent=util_frame, text='LIMPIAR STOCK BASES', command=self._borrar_produccion_stock_bases, style_key='action_warning_small').pack(side='left', padx=(0, 10))
        ButtonFactory.create_button(parent=util_frame, text='BORRAR RECETAS', command=self._borrar_produccion_recetas, style_key='action_warning_small').pack(side='left')

    def _build_peligro_tab(self):
        # Card Reset Completo
        card = self._create_card(self.tab_peligro, 'ZONA DE PELIGRO CRÍTICO')
        
        ctk.CTkLabel(
            card,
            text='⚠️ Esta pestaña contiene acciones IRREVERSIBLES.',
            font=get_font('label', module=self.module_name),
            text_color='#FF5252'
        ).pack(anchor='w', padx=20, pady=(0, 20))

        btn = ButtonFactory.create_button(
            parent=card,
            text='RESET COMPLETO DE LA BASE DE DATOS',
            command=self._reset_completo,
            style_key='action_danger_small'
        )
        btn.pack(fill='x', padx=20, pady=(0, 20))

        ctk.CTkLabel(
            card,
            text='Borra tickets, cierres, albaranes, facturas, producción, catálogo,\nresetea contadores y estadísticas de clientes.',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text_dim', '#999999'),
            justify='center'
        ).pack(pady=(0, 20))

    # --- LÓGICA ---

    def _do_search_productos(self):
        query = self.entry_search_prod.get()
        if len(query) < 2:
            return
        
        # Limpiar resultados previos visualmente? 
        # No hace falta, el TagSelector maneja los seleccionados por separado.
        results = self._search_productos(query)
        if not results:
            ToastWidget.show(self.parent, 'No se encontraron productos', tipo='warning')
            return
            
        # Añadir resultados al selector para que el usuario elija
        for res in results:
            self.tag_selector_productos.add_tag(res['id'], res['nombre_display'])
        
        self.entry_search_prod.delete(0, 'end')

    def _do_search_clientes(self):
        query = self.entry_search_cli.get()
        if len(query) < 2:
            return
        results = self._search_clientes(query)
        if not results:
            ToastWidget.show(self.parent, 'No se encontraron clientes', tipo='warning')
            return
        for res in results:
            self.tag_selector_clientes.add_tag(res['id'], res['nombre_display'])
        self.entry_search_cli.delete(0, 'end')

    def _reset_clientes_selectivos(self):
        ids = self.tag_selector_clientes.get_selected_ids()
        if not ids:
            show_warning(self.container, 'Atención', 'Selecciona clientes primero')
            return
        def _confirmar():
            if self.service.reset_tesoro_clientes(ids):
                ToastWidget.show(self.parent, f'{len(ids)} clientes reseteados', tipo='success')
                self.tag_selector_clientes.clear()
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', f'¿Resetear {len(ids)} clientes seleccionados?', callback=_confirmar)

    def _reset_clientes_todos(self):
        def _confirmar():
            if self.service.reset_tesoro_clientes(None):
                ToastWidget.show(self.parent, 'Todos los clientes reseteados', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, '⚠️ PELIGRO', '¿Resetear estadísticas de TODOS los clientes?', callback=_confirmar)

    def _borrar_puntos_todos(self):
        def _confirmar():
            if self.service.borrar_points_movements():
                ToastWidget.show(self.parent, 'Movimientos de puntos borrados', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar TODOS los puntos de fidelización?', callback=_confirmar)

    def _borrar_tickets_ui(self):
        reset = self.check_tickets_reset.get()
        def _confirmar():
            if self.service.borrar_tickets(None, reset_counter=reset):
                ToastWidget.show(self.parent, 'Ventas borradas correctamente', tipo='success')
            else:
                show_error(self.container, 'Error', 'No se pudieron borrar los tickets')
        show_warning(self.container, 'Confirmar', '¿Borrar TODAS las ventas?\nEsta acción no se puede deshacer.', callback=_confirmar)

    def _borrar_productos_todos(self):
        reset = self.check_prod_reset.get()
        def _confirmar():
            if self.service.borrar_productos(None, reset_counter=reset):
                ToastWidget.show(self.parent, 'Catálogo borrado correctamente', tipo='success')
            else:
                show_error(self.container, 'Error', 'No se pudo borrar el catálogo')
        show_warning(self.container, 'Confirmar', '¿Borrar TODO el catálogo de productos?\nSe eliminarán precios y códigos de barras vinculados.', callback=_confirmar)

    def _borrar_productos_selectivos(self):
        ids = self.tag_selector_productos.get_selected_ids()
        if not ids:
            show_warning(self.container, 'Atención', 'Selecciona productos primero')
            return
        def _confirmar():
            if self.service.borrar_productos(ids):
                ToastWidget.show(self.parent, f'{len(ids)} productos borrados', tipo='success')
                self.tag_selector_productos.clear()
            else:
                show_error(self.container, 'Error', 'Fallo al borrar productos')
        show_warning(self.container, 'Confirmar', f'¿Borrar {len(ids)} productos seleccionados?', callback=_confirmar)

    def _borrar_albaranes_ui(self):
        reset = self.check_alb_reset.get()
        def _confirmar():
            if self.service.borrar_albaranes(None, reset_counter=reset):
                ToastWidget.show(self.parent, 'Albaranes borrados', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar todos los albaranes?', callback=_confirmar)

    def _borrar_facturas_ui(self):
        reset = self.check_fac_reset.get()
        def _confirmar():
            if self.service.borrar_facturas(None, reset_counter=reset):
                ToastWidget.show(self.parent, 'Facturas borradas', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar todas las facturas?', callback=_confirmar)

    def _borrar_cierres_ui(self):
        reset = self.check_cierres_reset.get()
        def _confirmar():
            if self.service.borrar_cierres(reset_counter=reset):
                ToastWidget.show(self.parent, 'Cierres borrados', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar todos los cierres?', callback=_confirmar)


    def _search_clientes(self, query):
        if not self.db or not query or len(query) < 2:
            return []
        try:
            sql = "SELECT id, nombre FROM clientes WHERE nombre LIKE ? OR dni LIKE ? ORDER BY nombre LIMIT 20"
            rows = self.db.fetch_all(sql, (f'%{query}%', f'%{query}%'))
            results = []
            for row in rows:
                # El fetch_all puede devolver tuplas o diccionarios según la config de la DB
                if isinstance(row, dict):
                    results.append({'id': row['id'], 'nombre_display': row['nombre']})
                else:
                    results.append({'id': row[0], 'nombre_display': row[1]})
            return results
        except Exception:
            logging.exception('Error buscando clientes')
            return []

    def _search_productos(self, query):
        if not self.db or not query or len(query) < 2:
            return []
        try:
            sql = "SELECT id, nombre FROM productos WHERE nombre LIKE ? OR sku LIKE ? ORDER BY nombre LIMIT 20"
            rows = self.db.fetch_all(sql, (f'%{query}%', f'%{query}%'))
            results = []
            for row in rows:
                if isinstance(row, dict):
                    results.append({'id': row['id'], 'nombre_display': row['nombre']})
                else:
                    results.append({'id': row[0], 'nombre_display': row[1]})
            return results
        except Exception:
            logging.exception('Error buscando productos')
            return []

    def get_widget(self):
        return self._outer

    def _borrar_produccion_ordenes(self):
        reset = self.check_prod_seq.get()
        def _confirmar():
            if self.service.borrar_produccion_ordenes():
                if reset:
                    self.service.reset_produccion_contadores()
                ToastWidget.show(self.parent, 'Producción limpiada', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar todas las órdenes de producción?', callback=_confirmar)

    def _borrar_produccion_stock_disenos(self):
        def _confirmar():
            if self.service.borrar_produccion_stock_disenos():
                ToastWidget.show(self.parent, 'Stock diseños limpio', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar stock acumulado de diseños?', callback=_confirmar)

    def _borrar_produccion_stock_bases(self):
        def _confirmar():
            if self.service.borrar_produccion_stock_bases():
                ToastWidget.show(self.parent, 'Stock bases limpio', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar stock de bases?', callback=_confirmar)

    def _borrar_produccion_recetas(self):
        def _confirmar():
            if self.service.borrar_produccion_recetas():
                ToastWidget.show(self.parent, 'Recetas borradas', tipo='success')
            else:
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', '¿Borrar todas las recetas?', callback=_confirmar)

    def _reset_completo(self):
        def _segunda():
            def _ejecutar():
                if self.service.reset_completo():
                    ToastWidget.show(self.parent, 'BASE DE DATOS RESETEADA', tipo='success')
                else:
                    show_error(self.container, 'Error', 'Fallo en reset completo')
            show_warning(self.container, '⚠️⚠️ ÚLTIMA CONFIRMACIÓN', 'Acción IRREVERSIBLE. ¿Continuar?', callback=_ejecutar)
        show_warning(self.container, '⚠️ RESET COMPLETO', 'Se borrarán todos los datos y contadores.\n¿Continuar?', callback=_segunda)
