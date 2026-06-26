
import logging
import customtkinter as ctk
from kool_tpv.utils.config_loader import load_colors, create_action_button
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.widgets.notificaciones import ToastWidget


class FidelizacionGeneralUI:
    def __init__(self, parent, db, module_name='config'):
        self.parent = parent
        self.db = db
        self.module_name = module_name

        try:
            self.colors = load_colors(module_name)
        except Exception:
            logging.exception('Error cargando colores en FidelizacionGeneralUI')
            self.colors = {}

        bg = self.colors.get('background', '#000000')
        self.container = ctk.CTkFrame(parent, fg_color=bg)

        # Header frame
        self.header_frame = ctk.CTkFrame(self.container, fg_color=bg)
        self.header_frame.pack(fill='x', padx=20, pady=20)

        # Label porcentaje actual (readonly)
        lbl_actual = ctk.CTkLabel(
            self.header_frame,
            text='% General actual:',
            font=get_font('label', module=module_name),
            text_color=self.colors.get('text', '#FFFFFF')
        )
        lbl_actual.pack(side='left', padx=(0, 10))

        self.lbl_valor_actual = ctk.CTkLabel(
            self.header_frame,
            text='0',
            font=get_font('title', module=module_name),
            text_color=self.colors.get('secondary', '#FFB74D')
        )
        self.lbl_valor_actual.pack(side='left', padx=(0, 30))

        # Entry nuevo porcentaje
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

        # Botón confirmar
        btn_confirmar = create_action_button(self.header_frame, 'guardar', self._on_confirmar)
        btn_confirmar.pack(side='left', padx=10)

        # Cargar valor actual
        self._load_data()

    def get_widget(self):
        return self.container

    def _load_data(self):
        """Cargar % general actual desde BD."""
        if not self.db:
            return

        try:
            query = "SELECT valor FROM configuracion WHERE clave = 'fide_porcentaje_general'"
            row = self.db.fetch_one(query)
            valor = row[0] if row else '0'
            self.lbl_valor_actual.configure(text=valor)
        except Exception:
            logging.exception('Error cargando fide_porcentaje_general')
            self.lbl_valor_actual.configure(text='0')

    def _on_confirmar(self):
        """Guardar nuevo % general en BD."""
        if not self.db:
            return

        nuevo_valor = self.entry_nuevo.get().strip()

        # Validar que sea numérico
        try:
            float(nuevo_valor)
        except ValueError:
            ToastWidget.show(self.container, 'INTRODUCE UN VALOR NUMÉRICO VÁLIDO', tipo='error')
            return

        try:
            conn = self.db.connection
            cur = conn.cursor()
            cur.execute('BEGIN')

            cur.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                ('fide_porcentaje_general', nuevo_valor)
            )

            conn.commit()

            # Actualizar label
            self.lbl_valor_actual.configure(text=nuevo_valor)
            self.entry_nuevo.delete(0, 'end')

            ToastWidget.show(self.parent, f'% general actualizado a {nuevo_valor}', tipo='success')

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.exception('Error guardando fide_porcentaje_general')
            ToastWidget.show(self.container, 'NO SE PUDO GUARDAR', tipo='error')
