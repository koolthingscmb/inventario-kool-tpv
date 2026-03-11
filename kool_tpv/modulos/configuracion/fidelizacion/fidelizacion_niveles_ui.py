import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.nav_list import NavList
from kool_tpv.base_datos.niveles_service import NivelesService


class FidelizacionNivelesUI:
    def __init__(self, parent, db, module_name='config', keyboard_manager=None):
        self.parent = parent
        self.db = db
        self.module_name = module_name
        self.keyboard_manager = keyboard_manager
        self.service = NivelesService(db)

        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en FidelizacionNivelesUI')
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Estado
        self.selected_nivel = None
        self.modo_edicion = False  # True si estamos editando, False si creando nuevo

        # Header frame (grid 8 columnas)
        self.header_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.header_frame.pack(fill='x', padx=20, pady=20)

        for c in range(8):
            self.header_frame.grid_columnconfigure(c, weight=1)

        entry_kw = {
            'fg_color': bg,
            'text_color': self.colors.get('text', '#FFFFFF'),
            'border_width': 2,
            'border_color': self.colors.get('border', self.colors.get('primary')),
            'font': get_font('entry', module=module_name)
        }

        # Fila 0: LEVEL | NOMBRE LEVEL
        ctk.CTkLabel(
            self.header_frame,
            text='Level:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=0, column=0, sticky='w', padx=6, pady=6)

        self.entry_level = ctk.CTkEntry(self.header_frame, width=80, **entry_kw)
        self.entry_level.grid(row=0, column=1, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(
            self.header_frame,
            text='Nombre Level:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=0, column=2, sticky='w', padx=6, pady=6)

        self.entry_nombre = ctk.CTkEntry(self.header_frame, **entry_kw)
        self.entry_nombre.grid(row=0, column=3, columnspan=5, sticky='ew', padx=6, pady=6)

        # Fila 1: GRAFISMO | PUNTOS MÍNIMOS
        ctk.CTkLabel(
            self.header_frame,
            text='Grafismo:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=1, column=0, sticky='w', padx=6, pady=6)

        self.entry_grafismo = ctk.CTkEntry(self.header_frame, **entry_kw)
        self.entry_grafismo.grid(row=1, column=1, columnspan=3, sticky='ew', padx=6, pady=6)

        ctk.CTkLabel(
            self.header_frame,
            text='Puntos mínimos:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=1, column=4, sticky='w', padx=6, pady=6)

        self.entry_puntos = ctk.CTkEntry(self.header_frame, width=120, **entry_kw)
        self.entry_puntos.grid(row=1, column=5, columnspan=3, sticky='ew', padx=6, pady=6)

        # Fila 2: TIPO RECOMPENSA (combobox) | DETALLE RECOMPENSA
        ctk.CTkLabel(
            self.header_frame,
            text='Tipo Recompensa:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=2, column=0, sticky='w', padx=6, pady=6)

        self.combo_tipo_recompensa = ctk.CTkComboBox(
            self.header_frame,
            values=['', 'Descuento', 'Artículo'],
            fg_color=bg,
            button_color=self.colors.get('primary', '#FF9800'),
            border_color=self.colors.get('border', self.colors.get('primary')),
            text_color=self.colors.get('text'),
            font=get_font('entry', module=module_name)
        )
        self.combo_tipo_recompensa.grid(row=2, column=1, columnspan=2, sticky='ew', padx=6, pady=6)
        self.combo_tipo_recompensa.set('')

        ctk.CTkLabel(
            self.header_frame,
            text='Detalle:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text')
        ).grid(row=2, column=3, sticky='w', padx=6, pady=6)

        self.entry_detalle = ctk.CTkEntry(self.header_frame, **entry_kw)
        self.entry_detalle.grid(row=2, column=4, columnspan=4, sticky='ew', padx=6, pady=6)

        # Fila 3: Botones GUARDAR y NUEVO NIVEL
        btn_frame = ctk.CTkFrame(self.header_frame, fg_color='transparent')
        btn_frame.grid(row=3, column=0, columnspan=8, sticky='ew', pady=10)

        btn_guardar = create_action_button(btn_frame, 'guardar', self._on_guardar)
        btn_guardar.pack(side='left', padx=10)

        btn_nuevo = create_action_button(btn_frame, 'nuevo_nivel', self._on_nuevo_nivel)
        btn_nuevo.pack(side='left', padx=10)

        # NavList para niveles
        self.nav_list = NavList(
            self.container,
            columns=[
                ('level', 80, 'Level'),
                ('nombre_nivel', 200, 'Nombre'),
                ('grafismo_nivel', 150, 'Grafismo'),
                ('gasto_minimo', 150, 'Puntos Mín.')
            ],
            on_select=self._on_nivel_select,
            module_name=module_name,
            keyboard_manager=self.keyboard_manager
        )
        self.nav_list.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Footer: botón Eliminar
        self.footer = ctk.CTkFrame(self.container, fg_color='transparent')
        self.footer.pack(side='bottom', fill='x', padx=12, pady=12)

        btn_eliminar = create_action_button(self.footer, 'eliminar', self._on_eliminar)
        btn_eliminar.pack(side='left', padx=8)

        # Cargar niveles
        self._load_niveles()

    def get_widget(self):
        return self.container

    def _load_niveles(self):
        """Cargar niveles desde BD."""
        try:
            niveles = self.service.get_all_niveles()

            self.nav_list.clear_items()

            for nivel in niveles:
                self.nav_list.add_item({
                    'id': nivel['id'],
                    'level': str(nivel['level']),
                    'nombre_nivel': nivel['nombre_nivel'],
                    'grafismo_nivel': nivel['grafismo_nivel'],
                    'gasto_minimo': str(nivel['gasto_minimo']),
                    'tipo_recompensa': nivel['tipo_recompensa'],
                    'detalle_recompensa': nivel['detalle_recompensa']
                })

        except Exception:
            logging.exception('Error cargando niveles')

    def _on_nivel_select(self, data):
        """Cargar nivel seleccionado en formulario."""
        self.selected_nivel = data
        self.modo_edicion = True

        try:
            self.entry_level.delete(0, 'end')
            self.entry_level.insert(0, data.get('level', ''))

            self.entry_nombre.delete(0, 'end')
            self.entry_nombre.insert(0, data.get('nombre_nivel', ''))

            self.entry_grafismo.delete(0, 'end')
            self.entry_grafismo.insert(0, data.get('grafismo_nivel', ''))

            self.entry_puntos.delete(0, 'end')
            self.entry_puntos.insert(0, data.get('gasto_minimo', ''))

            tipo_rec = data.get('tipo_recompensa', '')
            self.combo_tipo_recompensa.set(tipo_rec if tipo_rec else '')

            self.entry_detalle.delete(0, 'end')
            self.entry_detalle.insert(0, data.get('detalle_recompensa', ''))

        except Exception:
            logging.exception('Error cargando nivel en formulario')

    def _on_nuevo_nivel(self):
        """Preparar formulario para crear nuevo nivel."""
        self.modo_edicion = False
        self.selected_nivel = None

        # Calcular siguiente level disponible
        siguiente_level = self._calcular_siguiente_level()

        # Limpiar entries
        self.entry_level.delete(0, 'end')
        self.entry_level.insert(0, str(siguiente_level))

        self.entry_nombre.delete(0, 'end')
        self.entry_grafismo.delete(0, 'end')
        self.entry_puntos.delete(0, 'end')
        self.combo_tipo_recompensa.set('')
        self.entry_detalle.delete(0, 'end')

    def _calcular_siguiente_level(self):
        """Calcular próximo número de level disponible."""
        return self.service.get_next_level()

    def _on_guardar(self):
        """Guardar nivel (INSERT si nuevo, UPDATE si edición)."""
        # Validar campos obligatorios
        level = self.entry_level.get().strip()
        nombre = self.entry_nombre.get().strip()
        grafismo = self.entry_grafismo.get().strip()
        puntos = self.entry_puntos.get().strip()

        if not level or not nombre or not grafismo or not puntos:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(
                self.container,
                'Campos obligatorios',
                'Level, Nombre, Grafismo y Puntos mínimos son obligatorios'
            )
            return

        # Validar que level y puntos sean numéricos
        try:
            level_num = int(level)
            puntos = puntos.replace(',', '.')
            puntos_num = float(puntos)
        except ValueError:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'Level debe ser entero y Puntos numérico')
            return

        # Preparar datos
        tipo_rec = self.combo_tipo_recompensa.get().strip()
        detalle_rec = self.entry_detalle.get().strip()

        data = {
            'level': level_num,
            'nombre_nivel': nombre,
            'grafismo_nivel': grafismo,
            'gasto_minimo': puntos_num,
            'tipo_recompensa': tipo_rec if tipo_rec else None,
            'detalle_recompensa': detalle_rec if detalle_rec else None
        }

        # Guardar o actualizar
        if self.modo_edicion and self.selected_nivel:
            ok = self.service.update_nivel(self.selected_nivel['id'], data)
            accion = 'actualizado'
        else:
            ok = self.service.save_nivel(data)
            accion = 'creado'

        if ok:
            self._load_niveles()
            self._on_nuevo_nivel()

            from kool_tpv.utils.custom_dialog import show_success
            show_success(self.container, 'Guardado', f'Nivel {accion} correctamente')
        else:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar')

    def _on_eliminar(self):
        """Eliminar nivel seleccionado (con confirmación)."""
        if not self.selected_nivel:
            from kool_tpv.utils.custom_dialog import show_warning
            show_warning(self.container, 'Atención', 'Selecciona un nivel primero')
            return

        from kool_tpv.utils.custom_dialog import show_warning

        def _confirmar_eliminar():
            ok = self.service.delete_nivel(self.selected_nivel['id'])

            if ok:
                self._load_niveles()
                self._on_nuevo_nivel()

                from kool_tpv.utils.custom_dialog import show_success
                show_success(self.container, 'Eliminado', 'Nivel eliminado correctamente')
            else:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.container, 'Error', 'No se pudo eliminar')

        show_warning(
            self.container,
            'Confirmar eliminación',
            f'¿Eliminar nivel {self.selected_nivel.get("level")} - {self.selected_nivel.get("nombre_nivel")}?',
            callback=_confirmar_eliminar
        )