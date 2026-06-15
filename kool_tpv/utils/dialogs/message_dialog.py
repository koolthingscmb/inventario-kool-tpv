"""
Diálogo de mensaje con botón simple o confirmación (Cancelar/Aceptar).
"""
import customtkinter as ctk
import logging

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory


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
        """Crear widgets del diálogo."""
        from .content_container import create_dialog_content_container

        tipo_config = self.dialogs_colors.get(self.tipo, {})

        title_font = self._get_font('title')
        message_font = self._get_font('message')
        button_font = self._get_font('button')

        # Frame principal
        padding_x = int(self.geometry_cfg.get('padding_x', 20))
        padding_y = int(self.geometry_cfg.get('padding_y', 20))
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=padding_x, pady=padding_y)
        content_parent = create_dialog_content_container(main_frame, self.geometry_cfg)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(content_parent, image=icon, text='')
            icon_label.pack(pady=(0, 10))

        # Título
        if titulo:
            title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
            titulo_label = ctk.CTkLabel(
                content_parent,
                text=titulo.upper(),
                font=title_font,
                text_color=title_color
            )
            titulo_label.pack(pady=(10, 15))

        # Mensaje
        if mensaje:
            msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
            wraplength = self._calcular_wraplength()
            mensaje_label = ctk.CTkLabel(
                content_parent,
                text=mensaje.upper(),
                font=message_font,
                text_color=msg_color,
                wraplength=wraplength,
                justify='center'
            )
            mensaje_label.pack(pady=(0, 25))

        # Botones
        style_key = self._get_button_style_key()

        if self.confirm:
            btn_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
            btn_frame.pack()

            # Cancelar
            try:
                btn_cancel = ButtonFactory.create_button(
                    parent=btn_frame,
                    text='CANCELAR',
                    command=self._on_cancel,
                    style_key='dialog_cancel_btn',
                    font=button_font
                )
            except Exception as e:
                logging.warning(f"Error creando botón CANCELAR: {e}, usando fallback")
                btn_cancel = ctk.CTkButton(
                    btn_frame,
                    text='CANCELAR',
                    command=self._on_cancel,
                    fg_color=tipo_config.get('cancel_bg', self.fallbacks['colors']['cancel_bg']),
                    hover_color=tipo_config.get('cancel_hover', self.fallbacks['colors']['cancel_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])),
                    height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])),
                    corner_radius=int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])),
                    border_width=0
                )
            btn_cancel.pack(side='left', padx=(0, 10))
            self._setup_button_focus(btn_cancel, is_accept=False)

            # Aceptar
            try:
                btn_accept = ButtonFactory.create_button(
                    parent=btn_frame,
                    text=btn_text,
                    command=self._on_accept,
                    style_key=style_key,
                    font=button_font
                )
            except Exception as e:
                logging.warning(f"Error creando botón ACEPTAR: {e}, usando fallback")
                btn_accept = ctk.CTkButton(
                    btn_frame,
                    text=btn_text.upper(),
                    command=self._on_accept,
                    fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                    hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])),
                    height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])),
                    corner_radius=int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])),
                    border_width=0
                )
            btn_accept.pack(side='left')
            self._setup_button_focus(btn_accept, is_accept=True)
            self.btn = btn_accept

            # Navegación TAB
            try:
                btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
                btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
            except Exception:
                pass

            self.btn_cancel = btn_cancel
            self.btn_accept = btn_accept
        else:
            # Botón único
            try:
                self.btn = ButtonFactory.create_button(
                    parent=content_parent,
                    text=btn_text,
                    command=self._on_close,
                    style_key=style_key,
                    font=button_font
                )
            except Exception as e:
                logging.warning(f"Error creando botón: {e}, usando fallback")
                self.btn = ctk.CTkButton(
                    content_parent,
                    text=btn_text.upper(),
                    command=self._on_close,
                    fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                    hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])),
                    height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])),
                    corner_radius=int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])),
                    border_width=0
                )
            self.btn.pack()
            self._setup_button_focus(self.btn, is_accept=True)

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
