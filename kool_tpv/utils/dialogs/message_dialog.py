"""
Diálogo de mensaje con botón simple o confirmación (Cancelar/Aceptar).
"""
import customtkinter as ctk
import logging

from .base_dialog import BaseDialog


class MessageDialog(BaseDialog):
    """Diálogo de mensaje con botón simple o confirmación.

    Soporta:
    - Diálogo simple: solo botón "Aceptar"
    - Diálogo de confirmación: botones "Cancelar" y "Aceptar"
    """

    def __init__(self, parent, tipo='info', titulo='', mensaje='', btn_text='Aceptar', callback=None, confirm=False):
        super().__init__(parent, tipo=tipo, titulo=titulo, callback=callback)

        self.confirm = bool(confirm)
        self.result = False

        # Crear contenido
        self._crear_contenido(titulo, mensaje, btn_text)

        # Bindings específicos
        try:
            if self.confirm:
                self.bind('<Escape>', lambda e: self._on_cancel())
                self.bind('<Return>', lambda e: self._on_accept())
            else:
                self.bind('<Escape>', lambda e: self._on_close())
                self.bind('<Return>', lambda e: self._on_close())
        except Exception:
            pass

        # Foco en botón principal
        try:
            self.btn.focus_set()
        except Exception:
            pass

    def _crear_contenido(self, titulo, mensaje, btn_text):
        """Crear widgets del diálogo con barra de título + contenido + botones."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        message_font = self._get_font('message')

        # Frame principal sin padding (la barra va full-width)
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True)

        # Barra de título con icono pequeño
        content_frame = self._crear_barra_titulo(main_frame, titulo)

        # Contenido: mensaje centrado
        padding_x = int(self.geometry_cfg.get('padding_x', 20))
        padding_y = int(self.geometry_cfg.get('padding_y', 20))

        msg_container = ctk.CTkFrame(content_frame, fg_color='transparent')
        msg_container.pack(fill='both', expand=True, padx=padding_x, pady=padding_y)

        if mensaje:
            msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
            wraplength = self._calcular_wraplength()
            mensaje_label = ctk.CTkLabel(
                msg_container,
                text=mensaje.upper(),
                font=message_font,
                text_color=msg_color,
                wraplength=wraplength,
                justify='center'
            )
            mensaje_label.pack(expand=True)

        # Botones unificados
        self.btn = self._crear_botones(content_frame, btn_text=btn_text, confirm=self.confirm)

    def _on_close(self):
        """Cerrar diálogo y ejecutar callback."""
        try:
            if self.callback and callable(self.callback):
                try:
                    cb = self.callback
                    self._cb_parent.after(20, lambda: cb())
                except Exception:
                    try:
                        self.after(20, lambda: cb())
                    except Exception:
                        logging.exception('Error ejecutando callback en _on_close')
        except Exception:
            logging.exception('Error en _on_close')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_accept(self):
        """Aceptar: cerrar con resultado True."""
        try:
            self.result = True
            if self.callback and callable(self.callback):
                try:
                    cb = self.callback
                    self._cb_parent.after(20, lambda: cb(True))
                except Exception:
                    try:
                        self.after(20, lambda: cb(True))
                    except Exception:
                        logging.exception('Error ejecutando callback en accept')
        except Exception:
            logging.exception('Error en _on_accept')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar con resultado False."""
        try:
            self.result = False
            if self.callback and callable(self.callback):
                try:
                    cb = self.callback
                    self._cb_parent.after(20, lambda: cb(False))
                except Exception:
                    try:
                        self.after(20, lambda: cb(False))
                    except Exception:
                        logging.exception('Error ejecutando callback en cancel')
        except Exception:
            logging.exception('Error en _on_cancel')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()
