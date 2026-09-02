import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.tag_selector import TagSelector
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.modulos.fidelizacion.fidelizacion_repository import FidelizacionRepository
from kool_tpv.utils.widgets.notificaciones import ToastWidget


class FidelizacionProductosUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.fidel_repo = FidelizacionRepository(db)

        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en FidelizacionProductosUI')
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Header frame
        self.header_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.header_frame.pack(fill='x', padx=20, pady=20)

        # TagSelector para productos (más grande)
        lbl_productos = ctk.CTkLabel(
            self.header_frame,
            text='Productos:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_productos.pack(anchor='w', pady=(0, 5))

        self.tag_selector = TagSelector(
            self.header_frame,
            module_name=module_name,
            placeholder='Buscar producto...',
            on_change=self._update_navlist,
            fg_color=bg
        )
        self.tag_selector.pack(fill='x', pady=(0, 15))

        # Asignar función de búsqueda
        self.tag_selector.set_search_function(self._search_productos)

        # Frame para tipo y valor (en misma línea)
        controls_frame = ctk.CTkFrame(self.header_frame, fg_color=bg)
        controls_frame.pack(fill='x', pady=(0, 10))

        # Radio buttons: Porcentaje / Fijo
        lbl_tipo = ctk.CTkLabel(
            controls_frame,
            text='Tipo:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_tipo.pack(side='left', padx=(0, 10))

        self.tipo_var = ctk.StringVar(value='porcentaje')

        radio_porcentaje = ctk.CTkRadioButton(
            controls_frame,
            text='%',
            variable=self.tipo_var,
            value='porcentaje',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF'),
            fg_color=self.colors.get('primary', '#FF9800')
        )
        radio_porcentaje.pack(side='left', padx=(0, 10))

        radio_fijo = ctk.CTkRadioButton(
            controls_frame,
            text='Fijo',
            variable=self.tipo_var,
            value='fijo',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF'),
            fg_color=self.colors.get('primary', '#FF9800')
        )
        radio_fijo.pack(side='left', padx=(0, 30))

        # Entry valor
        lbl_valor = ctk.CTkLabel(
            controls_frame,
            text='Valor:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_valor.pack(side='left', padx=(0, 10))

        self.entry_valor = ctk.CTkEntry(
            controls_frame,
            width=100,
            fg_color=bg,
            text_color=self.colors.get('text', '#FFFFFF'),
            border_width=2,
            border_color=self.colors.get('border', self.colors.get('primary')),
            font=get_font('entry', module=module_name)
        )
        self.entry_valor.pack(side='left', padx=(0, 20))

        # Botón confirmar
        btn_confirmar = create_action_button(
            controls_frame, 'guardar', self._on_confirmar,
            module='config', palette_key='primary'
        )
        btn_confirmar.pack(side='left', padx=10)

        # NavList para mostrar productos seleccionados
        self.nav_list = VirtualNavList(
            self.container,
            columns=[
                ('nombre', 300, 'Producto'),
                ('fidelizacion_tipo', 100, 'Tipo'),
                ('fidelizacion_valor', 100, 'Valor')
            ],
            module_name=module_name
        )
        self.nav_list.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # TagSelector notificará cambios vía callback `on_change`

    def get_widget(self):
        return self.container

    def _search_productos(self, query: str):
        """Función de búsqueda para TagSelector."""
        if not self.db or not query or len(query) < 2:
            return []

        try:
            sql = """
                SELECT id, nombre
                FROM productos
                WHERE nombre LIKE ? OR sku LIKE ?
                ORDER BY nombre
                LIMIT 20
            """
            rows = self.db.fetch_all(sql, (f'%{query}%', f'%{query}%'))

            results = []
            for row in rows:
                try:
                    prod_id = row[0] if isinstance(row, tuple) else row['id']
                    nombre = row[1] if isinstance(row, tuple) else row['nombre']
                    results.append({
                        'id': prod_id,
                        'nombre_display': nombre
                    })
                except Exception:
                    logging.exception('Error procesando fila de producto')

            return results

        except Exception:
            logging.exception('Error buscando productos')
            return []

    def _update_navlist(self):
        """Actualizar NavList con productos del TagSelector."""
        try:
            selected_ids = self.tag_selector.get_selected_ids()

            if not selected_ids:
                self.nav_list.clear_items()
                return

            # Obtener datos de productos desde BD
            if not self.db:
                return

            placeholders = ','.join('?' * len(selected_ids))
            query = f"""
                SELECT id, nombre, 
                       COALESCE(fidelizacion_tipo, 'porcentaje') as tipo,
                       COALESCE(fidelizacion_valor, 0) as valor
                FROM productos
                WHERE id IN ({placeholders})
            """
            rows = self.db.fetch_all(query, selected_ids)

            self.nav_list.clear_items()
            items_to_set = []

            for row in rows:
                try:
                    prod_id = row[0] if isinstance(row, tuple) else row['id']
                    nombre = row[1] if isinstance(row, tuple) else row['nombre']
                    tipo = row[2] if isinstance(row, tuple) else row['tipo']
                    valor = row[3] if isinstance(row, tuple) else row['valor']

                    # Formatear tipo para display
                    tipo_display = '%' if tipo == 'porcentaje' else 'Fijo'

                    items_to_set.append({
                        'id': prod_id,
                        'nombre': nombre,
                        'fidelizacion_tipo': tipo_display,
                        'fidelizacion_valor': str(valor)
                    })
                except Exception:
                    logging.exception('Error procesando producto para NavList')
            
            self.nav_list.set_items(items_to_set)

        except Exception:
            logging.exception('Error actualizando NavList')

    def _on_confirmar(self):
        """Guardar tipo y valor para todos los productos seleccionados."""
        if not self.db:
            return

        selected_ids = self.tag_selector.get_selected_ids()

        if not selected_ids:
            from kool_tpv.utils.widgets.notificaciones import show_warning
            show_warning(self.container, 'Selecciona al menos un producto')
            return

        tipo = self.tipo_var.get()
        valor = self.entry_valor.get().strip()

        # Validar numérico (admitir coma y punto)
        valor = valor.replace(',', '.')
        try:
            float(valor)
        except ValueError:
            ToastWidget.show(self.container, 'INTRODUCE UN VALOR NUMÉRICO VÁLIDO', tipo='error')
            return

        try:
            productos_updates = [
                (prod_id, tipo, float(valor))
                for prod_id in selected_ids
            ]
            self.fidel_repo.actualizar_fidelizacion_productos_bulk(productos_updates)

            # Limpiar y actualizar
            self.tag_selector.clear()
            self.entry_valor.delete(0, 'end')
            self._update_navlist()

            tipo_display = '%' if tipo == 'porcentaje' else 'puntos fijos'
            ToastWidget.show(self.parent, f'{len(selected_ids)} producto(s) actualizado(s) a {valor} {tipo_display}', tipo='success')

        except Exception:
            logging.exception('Error guardando fidelización en productos')
            ToastWidget.show(self.container, 'NO SE PUDO GUARDAR', tipo='error')
