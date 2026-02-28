"""SimpleDialog: Diálogos de información con botón único o confirmación."""
from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk

from kool_tpv.utils.dialogs.base_dialog import BaseDialog
from kool_tpv.utils.font_loader import get_font


class SimpleDialog(BaseDialog):
    """Diálogo simple con icono + título + mensaje + botón(es).

    Soporta dos modos:
    - confirm=False: Botón único "ACEPTAR" (info/notificación)
    - confirm=True: Dos botones "CANCELAR" + "ACEPTAR" (confirmación)
    """

    # Cache de configuración de botones
    _button_config = None

    def __init__(
        self,
        parent,
        tipo: str = 'info',
        titulo: str = '',
        mensaje: str = '',
        callback: Optional[Callable] = None,
        confirm: bool = False
    ):
        """
        Args:
            parent: Ventana padre
            tipo: 'success', 'error', 'warning', 'info'
            titulo: Título del diálogo
            mensaje: Mensaje a mostrar
            callback: Función callback (recibe True si acepta, False si cancela)
            confirm: Si True, muestra botones Cancelar + Aceptar
        """
        self.confirm = confirm

        # Llamar a BaseDialog.__init__ (configura ventana, colors, etc.)
        super().__init__(parent, tipo, titulo, mensaje, callback)

        # Crear contenido
        self._create_content()

        # Bindings de teclado
        self._setup_bindings()

        # Focus en botón principal
        try:
            self.btn_accept.focus_set()
        except Exception:
            pass

    @classmethod
    def _load_button_config(cls) -> dict:
        """Carga dialog_buttons_config.json (cached)."""
        if cls._button_config is not None:
            return cls._button_config

        try:
            config_path = Path(__file__).resolve().parents[2] / 'config' / 'dialog_buttons_config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._button_config = json.load(f)
                logging.debug(f'dialog_buttons_config.json cargado')
                return cls._button_config
        except Exception:
            logging.exception('Error cargando dialog_buttons_config.json, usando defaults')
            cls._button_config = {
                'aceptar': {
                    'text': 'ACEPTAR',
                    'width': 180,
                    'height': 55,
                    'corner_radius': 0,
                    'font_type': 'button',
                    'text_color': '#000000',
                    'fg_color_key': 'success',
                    'hover_color_key': 'success_hover'
                },
                'cancelar': {
                    'text': 'CANCELAR',
                    'width': 180,
                    'height': 55,
                    'corner_radius': 0,
                    'font_type': 'button',
                    'text_color': '#000000',
                    'fg_color_key': 'secondary',
                    'hover_color_key': 'secondary_hover'
                }
            }
            return cls._button_config

    def _create_content(self):
        """Crear contenido del diálogo."""
        padding = self.config.get('global', {}).get('padding', 30)

        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=padding, pady=padding)

        # Icono
        icon = self._load_icon()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(0, 15))
            icon_label._img_ref = icon  # Mantener referencia

        # Título
        if self.titulo:
            title_font = self._get_title_font()
            title_color = self._get_title_color()

            titulo_label = ctk.CTkLabel(
                main_frame,
                text=self.titulo.upper(),
                font=title_font,
                text_color=title_color
            )
            titulo_label.pack(pady=(0, 15))

        # Mensaje
        if self.mensaje:
            message_font = self._get_message_font()

            # Color del mensaje según tipo
            type_cfg = self.config.get('types', {}).get(self.tipo, {})
            border_key = type_cfg.get('border_color_key', 'info')
            message_color = self.colors.get(border_key, '#3498db')

            mensaje_label = ctk.CTkLabel(
                main_frame,
                text=self.mensaje.upper(),
                font=message_font,
                text_color=message_color,
                wraplength=600,
                justify='center'
            )
            mensaje_label.pack(pady=(0, 30))

        # Botones
        self._create_buttons(main_frame)

    def _create_buttons(self, parent):
        """Crear botones centrados."""
        button_cfg = self._load_button_config()

        # Frame contenedor centrado
        btn_container = ctk.CTkFrame(parent, fg_color='transparent')
        btn_container.pack(anchor='center')

        if self.confirm:
            # Modo confirmación: Cancelar + Aceptar
            self._create_button(btn_container, 'cancelar', self._on_cancel, side='left', padx=(0, 15))
            self._create_button(btn_container, 'aceptar', self._on_accept, side='left')
        else:
            # Modo simple: solo Aceptar
            self._create_button(btn_container, 'aceptar', self._on_close, side='left')

    def _create_button(self, parent, button_key: str, command: Callable, side='left', padx=0):
        """Crear un botón desde configuración."""
        button_cfg = self._load_button_config()
        cfg = button_cfg.get(button_key, {})

        # Obtener valores de config
        text = cfg.get('text', 'OK')
        width = cfg.get('width', 180)
        height = cfg.get('height', 55)
        corner_radius = cfg.get('corner_radius', 0)
        text_color = cfg.get('text_color', '#000000')

        # Colores
        fg_key = cfg.get('fg_color_key', 'primary')
        hover_key = cfg.get('hover_color_key', 'primary_hover')
        fg_color = self.colors.get(fg_key, '#3498db')
        hover_color = self.colors.get(hover_key, '#2980b9')

        # Fuente
        font_type = cfg.get('font_type', 'button')
        font = get_font(font_type)

        # Crear botón
        btn = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=corner_radius,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            font=font
        )
        btn.pack(side=side, padx=padx)

        # Guardar referencia (para focus)
        if button_key == 'aceptar':
            self.btn_accept = btn
        elif button_key == 'cancelar':
            self.btn_cancel = btn

        return btn

    def _setup_bindings(self):
        """Configurar bindings de teclado."""
        if self.confirm:
            # Modo confirmación: Escape=Cancelar, Enter=Aceptar
            self.bind('&lt;Escape&gt;', lambda e: self._on_cancel())
            self.bind('&lt;Return&gt;', lambda e: self._on_accept())
        else:
            # Modo simple: ambas teclas cierran
            self.bind('&lt;Escape&gt;', lambda e: self._on_close())
            self.bind('&lt;Return&gt;', lambda e: self._on_close())

    def _on_close(self):
        """Cerrar (botón único, retorna True)."""
        self._safe_close(result=True)

    def _on_accept(self):
        """Aceptar (confirmación, retorna True)."""
        self._safe_close(result=True)

    def _on_cancel(self):
        """Cancelar (confirmación, retorna False)."""
        self._safe_close(result=False)


# ============================================================================
# HELPERS PÚBLICOS (compatibilidad con API anterior)
# ============================================================================

def show_success(parent, titulo: str, mensaje: str, callback: Optional[Callable] = None) -> bool:
    """Mostrar diálogo de éxito.

    Returns:
        True (siempre, el usuario vio el mensaje)
    """
    dlg = SimpleDialog(parent, tipo='success', titulo=titulo, mensaje=mensaje, callback=callback, confirm=False)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return True


def show_error(parent, titulo: str, mensaje: str, callback: Optional[Callable] = None, confirm: bool = False) -> bool:
    """Mostrar diálogo de error.

    Args:
        confirm: Si True, muestra Cancelar+Aceptar y retorna True/False

    Returns:
        True si acepta, False si cancela (si confirm=True)
        True siempre (si confirm=False)
    """
    dlg = SimpleDialog(parent, tipo='error', titulo=titulo, mensaje=mensaje, callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False if confirm else True)


def show_warning(parent, titulo: str, mensaje: str, callback: Optional[Callable] = None, confirm: bool = False) -> bool:
    """Mostrar diálogo de advertencia.

    Args:
        confirm: Si True, muestra Cancelar+Aceptar y retorna True/False

    Returns:
        True si acepta, False si cancela
    """
    dlg = SimpleDialog(parent, tipo='warning', titulo=titulo, mensaje=mensaje, callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False)


def show_info(parent, titulo: str, mensaje: str, callback: Optional[Callable] = None, confirm: bool = False) -> bool:
    """Mostrar diálogo de información.

    Args:
        confirm: Si True, muestra Cancelar+Aceptar

    Returns:
        True si acepta, False si cancela (si confirm=True)
        True siempre (si confirm=False)
    """
    dlg = SimpleDialog(parent, tipo='info', titulo=titulo, mensaje=mensaje, callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False if confirm else True)
