import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font
from kool_tpv.modulos.configuracion.reset_service import ResetService
from kool_tpv.utils.widgets.tag_selector import TagSelector


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
        self.container = ctk.CTkFrame(parent, fg_color=bg)

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

        # === CLIENTES ===
        self._add_title('CLIENTES')

        # TagSelector clientes
        self.tag_selector_clientes = TagSelector(
            self.container,
            module_name=module_name,
            placeholder='Buscar cliente...',
            fg_color=bg
        )
        self.tag_selector_clientes.set_search_function(self._search_clientes)
        self.tag_selector_clientes.pack(fill='x', padx=40, pady=(0, 10))

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET TESORO (SELECTIVO)', command=self._reset_tesoro_selectivo, style_key='action_warning')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Resetear puntos de clientes seleccionados arriba',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET TESORO (TODOS)', command=self._reset_tesoro_todos, style_key='action_warning')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='⚠️ Resetear puntos de TODOS los clientes',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        # === PRODUCTOS ===
        self._add_title('PRODUCTOS')

        # TagSelector productos
        self.tag_selector_productos = TagSelector(
            self.container,
            module_name=module_name,
            placeholder='Buscar producto...',
            fg_color=bg
        )
        self.tag_selector_productos.set_search_function(self._search_productos)
        self.tag_selector_productos.pack(fill='x', padx=40, pady=(0, 10))

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='BORRAR PRODUCTOS', command=self._borrar_productos, style_key='action_warning')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Eliminar productos seleccionados arriba',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        # === TICKETS ===
        self._add_title('TICKETS')
        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='BORRAR TODOS', command=self._borrar_tickets, style_key='action_danger')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='⚠️ Eliminar TODOS los tickets (y movimientos relacionados)',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        # === CIERRES ===
        self._add_title('CIERRES')
        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='BORRAR TODOS', command=self._borrar_cierres, style_key='action_danger')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Eliminar todos los cierres de caja',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        # === CONTADORES ===
        self._add_title('CONTADORES FISCALES')
        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET TICKETS', command=self._reset_ticket_counter, style_key='action_primary')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET CIERRES', command=self._reset_cierre_counter, style_key='action_primary')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET ALBARANES', command=self._reset_albaran_counter, style_key='action_primary')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        frame = ctk.CTkFrame(self.container, fg_color='transparent')
        frame.pack(fill='x', padx=20, pady=3)
        btn = ButtonFactory.create_button(parent=frame, text='RESET FACTURAS', command=self._reset_factura_counter, style_key='action_primary')
        btn.pack(side='left', padx=(0, 15))
        ctk.CTkLabel(
            frame,
            text='Reiniciar contador a 0',
            font=get_font('label', module=self.module_name),
            text_color=self.colors.get('text', '#999999'),
            anchor='w'
        ).pack(side='left', fill='x', expand=True)

        # === RESET COMPLETO ===
        danger_frame = ctk.CTkFrame(self.container, fg_color='#B71C1C', corner_radius=8, border_width=4, border_color='#FFFFFF')
        danger_frame.pack(fill='x', padx=20, pady=30)

        ctk.CTkLabel(
            danger_frame,
            text='⚠️⚠️⚠️ ZONA DE PELIGRO ⚠️⚠️⚠️',
            font=get_font('title', module=module_name),
            text_color='#FFFFFF'
        ).pack(pady=15)

        btn = ButtonFactory.create_button(parent=danger_frame, text='RESET COMPLETO DE BD', command=self._reset_completo, style_key='action_danger')
        btn.pack(pady=(0, 10), padx=20, fill='x')

        ctk.CTkLabel(
            danger_frame,
            text='Borra tickets, cierres, albaranes, facturas, resetea contadores y tesoro',
            font=get_font('label', module=module_name),
            text_color='#FFCCCC'
        ).pack(pady=(0, 15))

    def get_widget(self):
        return self.container

    def _add_title(self, text):
        ctk.CTkLabel(
            self.container,
            text=text,
            font=get_font('title', module=self.module_name),
            text_color=self.colors.get('secondary', '#FFB74D'),
            anchor='w'
        ).pack(anchor='w', padx=20, pady=(20, 10))

    # _add_button removed: buttons are created via ButtonFactory to centralize styles

    def _search_clientes(self, query):
        if not self.db or not query or len(query) < 2:
            return []
        try:
            sql = "SELECT id, nombre FROM clientes WHERE nombre LIKE ? OR dni LIKE ? ORDER BY nombre LIMIT 20"
            rows = self.db.fetch_all(sql, (f'%{query}%', f'%{query}%'))
            results = []
            for row in rows:
                cliente_id = row[0] if isinstance(row, tuple) else row['id']
                nombre = row[1] if isinstance(row, tuple) else row['nombre']
                results.append({'id': cliente_id, 'nombre_display': nombre})
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
                prod_id = row[0] if isinstance(row, tuple) else row['id']
                nombre = row[1] if isinstance(row, tuple) else row['nombre']
                results.append({'id': prod_id, 'nombre_display': nombre})
            return results
        except Exception:
            logging.exception('Error buscando productos')
            return []

    def _reset_tesoro_selectivo(self):
        cliente_ids = self.tag_selector_clientes.get_selected_ids()
        if not cliente_ids:
            from kool_tpv.utils.custom_dialog import show_warning
            show_warning(self.container, 'Atención', 'Selecciona clientes primero')
            return

        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_tesoro_clientes(cliente_ids)
            self.tag_selector_clientes.clear()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', f'{len(cliente_ids)} cliente(s) reseteado(s)')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', f'¿Resetear {len(cliente_ids)} cliente(s)?', callback=_confirmar)

    def _reset_tesoro_todos(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_tesoro_clientes(None)
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Tesoro TODOS reseteado')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, '⚠️ PELIGRO', '¿Resetear tesoro TODOS?', callback=_confirmar)

    def _borrar_productos(self):
        producto_ids = self.tag_selector_productos.get_selected_ids()
        if not producto_ids:
            from kool_tpv.utils.custom_dialog import show_warning
            show_warning(self.container, 'Atención', 'Selecciona productos primero')
            return

        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.borrar_productos(producto_ids)
            self.tag_selector_productos.clear()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', f'{len(producto_ids)} producto(s) borrado(s)')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', f'¿Borrar {len(producto_ids)} producto(s)?', callback=_confirmar)

    def _borrar_tickets(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.borrar_tickets(None)
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Tickets borrados')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, '⚠️ PELIGRO', 'Borrar TODOS los tickets?', callback=_confirmar)

    def _borrar_cierres(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.borrar_cierres()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Cierres borrados')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', 'Borrar TODOS los cierres?', callback=_confirmar)

    def _reset_ticket_counter(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_ticket_counter()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Contador reseteado')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', 'Reset contador tickets?', callback=_confirmar)

    def _reset_cierre_counter(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_cierre_counter()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Contador reseteado')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', 'Reset contador cierres?', callback=_confirmar)

    def _reset_albaran_counter(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_albaran_counter()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Contador reseteado')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', 'Reset contador albaranes?', callback=_confirmar)

    def _reset_factura_counter(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _confirmar():
            ok = self.service.reset_factura_counter()
            if ok:
                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'OK', 'Contador reseteado')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'Fallo')
        show_warning(self.container, 'Confirmar', 'Reset contador facturas?', callback=_confirmar)

    def _reset_completo(self):
        from kool_tpv.utils.custom_dialog import show_warning
        def _segunda():
            def _ejecutar():
                ok = self.service.reset_completo()
                if ok:
                    from kool_tpv.utils.custom_dialog import show_success
                    show_success(self.container, '⚠️ HECHO', 'BD limpiada')
                else:
                    from kool_tpv.utils.custom_dialog import show_error
                    show_error(self.container, 'Error', 'Fallo')
            show_warning(self.container, '⚠️⚠️ ÚLTIMA CONFIRMACIÓN', 'NO se puede deshacer. ¿CONTINUAR?', callback=_ejecutar)
        show_warning(self.container, '⚠️ RESET COMPLETO', 'Borrará TODO.\n¿Continuar?', callback=_segunda)
