import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.font_loader import get_font


class FidelizacionTiposUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.module_name = module_name

        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en FidelizacionTiposUI')
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Buttons config
        self._buttons_cfg = self.colors.get('buttons', {})
        self._primary_btn = self._buttons_cfg.get('primary', {})

        # Estado
        self.selected_chip = None
        self.selected_tipo = None

        # Header frame (% actual readonly + entry nuevo % + botón)
        self.header_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.header_frame.pack(fill='x', padx=20, pady=20)

        # Label % actual (readonly)
        lbl_actual = ctk.CTkLabel(
            self.header_frame,
            text='% actual:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_actual.pack(side='left', padx=(0, 10))

        self.lbl_valor_actual = ctk.CTkLabel(
            self.header_frame,
            text='0',
            font=get_font('title', module=module_name),
            text_color=self.colors.get('secondary', '#FFB74D'),
            width=80
        )
        self.lbl_valor_actual.pack(side='left', padx=(0, 30))

        # Entry nuevo %
        lbl_nuevo = ctk.CTkLabel(
            self.header_frame,
            text='Nuevo %:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_nuevo.pack(side='left', padx=(0, 10))

        self.entry_nuevo = ctk.CTkEntry(
            self.header_frame,
            width=100,
            fg_color=bg,
            text_color=self.colors.get('text', '#FFFFFF'),
            border_width=2,
            border_color=self.colors.get('border', self.colors.get('primary')),
            font=get_font('entry', module=module_name)
        )
        self.entry_nuevo.pack(side='left', padx=(0, 20))

        # Botón guardar
        btn_guardar = create_action_button(self.header_frame, 'guardar', self._on_guardar)
        btn_guardar.pack(side='left', padx=10)

        # Chips frame (scrollable, grid 6 columnas)
        self.chips_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color=bg
        )
        self.chips_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        # Grid con 12 columnas para permitir chips de distintos tamaños
        for c in range(12):
            self.chips_frame.grid_columnconfigure(c, weight=1, uniform='col')

        # Cargar tipos
        self._load_tipos()

    def get_widget(self):
        return self.container

    def _load_tipos(self):
        """Cargar tipos desde BD y crear chips."""
        if not self.db:
            return

        try:
            # Limpiar chips existentes
            for w in list(self.chips_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            query = """
                SELECT id, nombre, COALESCE(fide_porcentaje, 0) as fide_porcentaje
                FROM tipos
                ORDER BY nombre
            """
            rows = self.db.fetch_all(query)

            if not rows:
                ctk.CTkLabel(
                    self.chips_frame,
                    text='No hay tipos',
                    text_color=self.colors.get('text', '#FFFFFF'),
                    fg_color='transparent'
                ).grid(row=0, column=0, padx=6, pady=6)
                return

            current_row = 0
            current_col = 0
            max_cols = 12  # Total de columnas en grid

            for i, row in enumerate(rows):
                try:
                    item_id = row[0] if isinstance(row, tuple) else row['id']
                    nombre = row[1] if isinstance(row, tuple) else row['nombre']
                    porcentaje = row[2] if isinstance(row, tuple) else row['fide_porcentaje']

                    # Calcular columnspan según longitud del texto
                    text_len = len(nombre)
                    if text_len <= 8:
                        colspan = 1
                    elif text_len <= 16:
                        colspan = 2
                    elif text_len <= 24:
                        colspan = 3
                    else:
                        colspan = 4

                    # Si no cabe en la fila actual, saltar a siguiente
                    if current_col + colspan > max_cols:
                        current_row += 1
                        current_col = 0

                    btn = ButtonFactory.create_button(
                        parent=self.chips_frame,
                        text=nombre,
                        command=None,
                        style_key="chip_default"
                    )
                    btn.grid(row=current_row, column=current_col, columnspan=colspan, padx=5, pady=5, sticky='ew')

                    # Guardar datos en el botón (tipos usan '_tipo_data')
                    setattr(btn, '_tipo_data', {
                        'id': item_id,
                        'nombre': nombre,
                        'fide_porcentaje': porcentaje
                    })

                    # Bind click
                    btn.bind('<Button-1>', lambda e, b=btn: self._select_chip(b))

                    # Avanzar columna
                    current_col += colspan

                except Exception:
                    logging.exception('Error procesando tipo en chips')
        except Exception:
            logging.exception('Error cargando tipos en chips')

    def _select_chip(self, btn):
        """Seleccionar chip y cargar datos en header."""
        try:
            # Deseleccionar anterior
            if self.selected_chip is not None:
                try:
                    ButtonFactory.apply_style(self.selected_chip, "chip_default")
                except Exception:
                    pass

            # Seleccionar nuevo
            self.selected_chip = btn
            try:
                ButtonFactory.apply_style(btn, "chip_selected")
            except Exception:
                pass

            # Cargar datos
            tipo_data = getattr(btn, '_tipo_data', None)
            if tipo_data:
                self.selected_tipo = tipo_data
                porcentaje = tipo_data.get('fide_porcentaje', 0)
                self.lbl_valor_actual.configure(text=str(porcentaje))
                logging.debug(f"Tipo seleccionado: {tipo_data.get('nombre')}, %: {porcentaje}")

        except Exception:
            logging.exception('Error seleccionando chip')

    def _on_guardar(self):
        """Guardar nuevo % para tipo seleccionado."""
        if not self.db:
            return

        if not self.selected_tipo:
            from kool_tpv.utils.custom_dialog import show_warning
            show_warning(self.container, 'Atención', 'Selecciona un tipo primero')
            return

        nuevo_valor = self.entry_nuevo.get().strip()

        # Validar numérico (admitir coma y punto)
        nuevo_valor = nuevo_valor.replace(',', '.')
        try:
            float(nuevo_valor)
        except ValueError:
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'Introduce un valor numérico válido')
            return

        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute(
                "UPDATE tipos SET fide_porcentaje = ? WHERE id = ?",
                (nuevo_valor, self.selected_tipo['id'])
            )

            conn.commit()

            # Actualizar label actual
            self.lbl_valor_actual.configure(text=nuevo_valor)
            self.entry_nuevo.delete(0, 'end')

            # Recargar chips para reflejar cambios
            self._load_tipos()

            from kool_tpv.utils.custom_dialog import show_success
            show_success(
                self.container,
                'Guardado',
                f'% actualizado a {nuevo_valor} para {self.selected_tipo["nombre"]}'
            )

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.exception('Error guardando fide_porcentaje en tipo')
            from kool_tpv.utils.custom_dialog import show_error
            show_error(self.container, 'Error', 'No se pudo guardar')
