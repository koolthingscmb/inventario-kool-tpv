"""
Diálogo de entrada de texto con campo de input.
"""
import customtkinter as ctk
import logging

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory


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
            self.entry.focus_set()
        except Exception:
            pass

    def _crear_contenido(self, titulo, mensaje, valor_defecto):
        """Crear widgets del diálogo."""
        from .content_container import create_dialog_content_container

        tipo_config = self.dialogs_colors.get(self.tipo, {})

        title_font = self._get_font('title')
        message_font = self._get_font('message')
        input_font = self._get_font('input')
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
            icon_label.pack(pady=(10, 15))

        # Título
        if titulo:
            title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
            titulo_label = ctk.CTkLabel(
                content_parent,
                text=titulo.upper(),
                font=title_font,
                text_color=title_color
            )
            titulo_label.pack(pady=(0, 15))

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
            mensaje_label.pack(pady=(0, 20))

        # Entry
        entry_width = int(self.geometry_cfg.get('entry_width', self.fallbacks['geometry']['entry_width'])) if isinstance(self.geometry_cfg.get('entry_width', None), int) else int(self.fallbacks['geometry']['entry_width'])
        entry_height = int(self.geometry_cfg.get('entry_height', self.fallbacks['geometry']['entry_height'])) if isinstance(self.geometry_cfg.get('entry_height', None), int) else int(self.fallbacks['geometry']['entry_height'])

        entry_params = {
            "master": content_parent,
            "width": entry_width,
            "height": entry_height,
            "font": input_font,
            "justify": 'center'
        }

        if self.password:
            entry_params["show"] = "*"

        self.entry = ctk.CTkEntry(**entry_params)
        self.entry.pack(pady=(0, 25))
        if valor_defecto:
            self.entry.insert(0, str(valor_defecto))
            self.entry.select_range(0, 'end')

        # Botones
        btn_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        btn_frame.pack()

        style_key = self._get_button_style_key()

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

        # Aceptar
        try:
            btn_accept = ButtonFactory.create_button(
                parent=btn_frame,
                text='ACEPTAR',
                command=self._on_accept,
                style_key=style_key,
                font=button_font
            )
        except Exception as e:
            logging.warning(f"Error creando botón ACEPTAR: {e}, usando fallback")
            btn_accept = ctk.CTkButton(
                btn_frame,
                text='ACEPTAR',
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
        self.btn = btn_accept

        # Navegación TAB y foco
        try:
            self._setup_button_focus(btn_cancel, is_accept=False)
            self._setup_button_focus(btn_accept, is_accept=True)
            btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
            btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
        except Exception:
            pass

    def _on_accept(self):
        """Aceptar: devolver valor ingresado."""
        valor = self.entry.get().strip()
        self.result = valor
        try:
            if self.callback and callable(self.callback):
                self.callback(valor)
        except Exception:
            logging.exception('Error ejecutando callback de InputDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar sin valor."""
        self.result = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def get_input(self):
        """Esperar y devolver resultado."""
        self.wait_window()
        return self.result
