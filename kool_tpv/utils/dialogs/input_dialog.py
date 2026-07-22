"""
Diálogo de entrada de texto con campo de input.
"""
import customtkinter as ctk
import logging

from .base_dialog import BaseDialog


class InputDialog(BaseDialog):
    """Diálogo de entrada de texto/password.

    Muestra un campo de entrada con título, mensaje y botones Cancelar/Aceptar.
    """

    def __init__(self, parent, tipo='success', titulo='', mensaje='', valor_defecto='', callback=None, password=False, window_title=None):
        # Inicializar base - pero vamos a sobrescribir algunas cosas
        super().__init__(parent, tipo=tipo, titulo=window_title if window_title else titulo, callback=callback)

        self.password = bool(password)
        self.result = None

        # Crear contenido
        self._crear_contenido(titulo, mensaje, valor_defecto)

        # Bindings
        try:
            self.bind('<Escape>', lambda e: self._on_cancel())
        except Exception:
            pass

        try:
            self.entry.bind('<Return>', lambda e: self._on_accept())
            self.entry.bind('<KP_Enter>', lambda e: self._on_accept())
        except Exception:
            pass

        # Posponer focus_force para que funcione en Windows después de grab_set/deiconify
        try:
            self.after(100, lambda: self.entry.focus_force())
        except Exception:
            pass

    def _crear_contenido(self, titulo, mensaje, valor_defecto):
        """Crear widgets del diálogo con barra de título + contenido + botones."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})

        message_font = self._get_font('message')
        input_font = self._get_font('input')

        # Frame principal sin padding (la barra va full-width)
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True)

        # Barra de título con icono pequeño
        content_frame = self._crear_barra_titulo(main_frame, titulo)

        # Contenido: mensaje + entry centrados
        padding_x = int(self.current_geom.get('padding_x', 20))
        padding_y = int(self.current_geom.get('padding_y', 20))

        content_wrapper = ctk.CTkFrame(content_frame, fg_color='transparent')
        content_wrapper.pack(fill='both', expand=True, padx=padding_x, pady=padding_y)

        # Mensaje
        if mensaje:
            msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
            wraplength = self._calcular_wraplength()
            mensaje_label = ctk.CTkLabel(
                content_wrapper,
                text=mensaje.upper(),
                font=message_font,
                text_color=msg_color,
                wraplength=wraplength,
                justify='center'
            )
            pady_msg = self.current_spacing.get('title_bottom', 10)
            mensaje_label.pack(pady=(0, pady_msg))

        # Entry
        entry_width = int(self.current_geom.get('entry_width', self.fallbacks['geometry']['entry_width']))
        entry_height = int(self.current_geom.get('entry_height', self.fallbacks['geometry']['entry_height']))

        entry_params = {
            "master": content_wrapper,
            "width": entry_width,
            "height": entry_height,
            "font": input_font,
            "justify": 'center'
        }

        if self.password:
            entry_params["show"] = "*"

        self.entry = ctk.CTkEntry(**entry_params)
        pady_entry = self.current_spacing.get('message_bottom', 10)
        self.entry.pack(pady=(0, pady_entry))

        if valor_defecto:
            self.entry.insert(0, str(valor_defecto))
            self.entry.select_range(0, 'end')

        # Botones unificados (siempre confirm en InputDialog: Cancelar + Aceptar)
        self.btn = self._crear_botones(content_frame, btn_text='ACEPTAR', confirm=True)

    def _ejecutar_callback(self, result=None):
        """Ejecuta el callback de forma segura."""
        if not self.callback or not callable(self.callback):
            return

        def _safe_call():
            try:
                # InputDialog siempre intenta pasar el valor (o None)
                try:
                    self.callback(result)
                except TypeError:
                    # Si falla por argumentos, llamar sin nada
                    self.callback()
            except Exception:
                logging.exception('Error ejecutando callback de InputDialog')

        try:
            self._cb_parent.after(20, _safe_call)
        except Exception:
            try:
                self.after(20, _safe_call)
            except Exception:
                _safe_call()

    def _on_accept(self):
        """Aceptar: devolver valor ingresado."""
        valor = self.entry.get().strip()
        self.result = valor
        self._ejecutar_callback(valor)
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar sin valor."""
        self.result = None
        self._ejecutar_callback(None)
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def get_input(self):
        """Esperar y devolver resultado."""
        self.wait_window()
        return self.result
