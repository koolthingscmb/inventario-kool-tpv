"""
Diálogo de configuración de cierre de caja.
Permite seleccionar qué secciones incluir en el ticket de cierre.
"""
import customtkinter as ctk
import logging

from .base_dialog import BaseDialog
from kool_tpv.utils.factories.button_factory import ButtonFactory


class CierreConfigDialog(BaseDialog):
    """Diálogo para configurar opciones de impresión del cierre.

    Muestra checkboxes para cada sección opcional del ticket.
    Retorna un dict con las opciones seleccionadas.
    """

    DEFAULT_SECTIONS = {
        'categorias': True,
        'tipos': True,
        'cajero': True,
        'productos': False,  # Por defecto desmarcado (puede ser muy largo)
        'iva': True,
        'tesoro': True,
    }

    def __init__(self, parent, callback=None, defaults=None):
        # Usar tipo 'info' para el diálogo
        super().__init__(parent, tipo='info', titulo='CONFIGURAR CIERRE', callback=callback)

        self.result = None
        self.sections = {}
        self.defaults = defaults or self.DEFAULT_SECTIONS.copy()

        # Crear contenido
        self._crear_contenido()

        # Bindings
        try:
            self.bind('<Escape>', lambda e: self._on_cancel())
        except Exception:
            pass

    def _crear_contenido(self):
        """Crear widgets del diálogo con checkboxes."""
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
            icon_label.pack(pady=(10, 15))

        # Título
        title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
        titulo_label = ctk.CTkLabel(
            content_parent,
            text='CONFIGURAR CIERRE',
            font=title_font,
            text_color=title_color
        )
        titulo_label.pack(pady=(0, 10))

        # Mensaje
        msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
        mensaje_label = ctk.CTkLabel(
            content_parent,
            text='SELECCIONA LAS SECCIONES A IMPRIMIR:',
            font=message_font,
            text_color=msg_color,
            wraplength=self._calcular_wraplength(),
            justify='center'
        )
        mensaje_label.pack(pady=(0, 20))

        # Frame de checkboxes
        checkbox_frame = ctk.CTkFrame(content_parent, fg_color='transparent')
        checkbox_frame.pack(pady=(0, 25))

        checkbox_font = self._get_font('message')

        # Crear checkboxes
        self.vars = {}
        sections_config = [
            ('categorias', 'Ventas por categoría'),
            ('tipos', 'Ventas por tipo'),
            ('cajero', 'Ventas por cajero'),
            ('productos', 'Ventas por producto'),
            ('iva', 'Desglose IVA'),
            ('tesoro', 'Puntos de Tesoro'),
        ]

        for key, label in sections_config:
            var = ctk.BooleanVar(value=self.defaults.get(key, True))
            self.vars[key] = var

            checkbox = ctk.CTkCheckBox(
                checkbox_frame,
                text=label,
                variable=var,
                font=checkbox_font,
                text_color=msg_color,
                hover_color=tipo_config.get('hover', self.fallbacks['colors']['hover']),
                fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
            )
            checkbox.pack(anchor='w', pady=5, padx=20)

        # Botones
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
            logging.warning(f"Error creando botón CANCELAR: {e}")
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
            )
        btn_cancel.pack(side='left', padx=(0, 10))

        # Ejecutar
        try:
            btn_accept = ButtonFactory.create_button(
                parent=btn_frame,
                text='EJECUTAR CIERRE',
                command=self._on_accept,
                style_key=self._get_button_style_key(),
                font=button_font
            )
        except Exception as e:
            logging.warning(f"Error creando botón EJECUTAR: {e}")
            btn_accept = ctk.CTkButton(
                btn_frame,
                text='EJECUTAR CIERRE',
                command=self._on_accept,
                fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                font=button_font,
                width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])),
                height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])),
            )
        btn_accept.pack(side='left')
        self.btn = btn_accept

        # Navegación TAB
        try:
            self._setup_button_focus(btn_cancel, is_accept=False)
            self._setup_button_focus(btn_accept, is_accept=True)
            btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
            btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
        except Exception:
            pass

    def _on_accept(self):
        """Aceptar: devolver configuración de secciones."""
        self.result = {key: var.get() for key, var in self.vars.items()}
        try:
            if self.callback and callable(self.callback):
                self.callback(self.result)
        except Exception:
            logging.exception('Error ejecutando callback de CierreConfigDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar sin resultado."""
        self.result = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def get_config(self):
        """Esperar y devolver configuración seleccionada."""
        self.wait_window()
        return self.result
