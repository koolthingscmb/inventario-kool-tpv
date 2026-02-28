"""BaseDialog: Clase padre común para todos los diálogos del sistema."""
from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk

try:
    from PIL import Image
except ImportError:
    Image = None

from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.font_loader import get_font
from kool_tpv.utils.dialogs.dialog_manager import DialogManager


class BaseDialog(ctk.CTkToplevel):
    """Clase base para todos los diálogos con configuración centralizada."""

    # Cache de configuración (se carga una vez)
    _dialog_config = None

    def __init__(
        self,
        parent,
        tipo: str = 'info',
        titulo: str = '',
        mensaje: str = '',
        callback: Optional[Callable] = None
    ):
        """
        Args:
            parent: Ventana padre
            tipo: Tipo de diálogo (success/error/warning/info/tesoro/password)
            titulo: Título del diálogo
            mensaje: Mensaje a mostrar
            callback: Función a ejecutar al cerrar/aceptar
        """
        # Verificar throttling
        if not DialogManager.can_show():
            logging.warning(f'Dialog {tipo} bloqueado: ya hay uno activo')
            # No llamar super().__init__ para evitar crear ventana
            return

        super().__init__(parent)

        self.tipo = tipo
        self.titulo = titulo
        self.mensaje = mensaje
        self.callback = callback
        self.result = None

        # Registrar en DialogManager
        if not DialogManager.register(self):
            logging.error(f'No se pudo registrar dialog {tipo}')
            self.destroy()
            return

        # Cargar configuraciones
        self.config = self._load_dialog_config()
        self.colors = self._load_colors()

        # Configurar ventana
        self._setup_window()

        # Centrar ventana (oculta primero para calcular antes de mostrar)
        self.withdraw()
        self.update_idletasks()
        self._center_window()

        # Modal
        try:
            self.transient(parent)
        except Exception:
            logging.exception('Error setting transient')

        # Mostrar y hacer modal
        self.deiconify()
        try:
            self.grab_set()
        except Exception:
            logging.exception('Error en grab_set')

        # Logging
        logging.info(f"Dialog '{tipo}' abierto: {titulo}")

    @classmethod
    def _load_dialog_config(cls) -> dict:
        """Carga dialog_config.json (cached)."""
        if cls._dialog_config is not None:
            return cls._dialog_config

        try:
            config_path = Path(__file__).resolve().parents[2] / 'config' / 'dialog_config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._dialog_config = json.load(f)
                logging.debug(f'dialog_config.json cargado desde {config_path}')
                return cls._dialog_config
        except Exception:
            logging.exception('Error cargando dialog_config.json, usando defaults')
            cls._dialog_config = {
                'global': {
                    'width': 700,
                    'height': 500,
                    'border_width': 4,
                    'corner_radius': 0,
                    'bg_color_key': 'dialog_bg',
                    'icon_size': 120,
                    'title_font': 'title',
                    'message_font': 'subtitle',
                    'padding': 30
                },
                'types': {}
            }
            return cls._dialog_config

    def _load_colors(self) -> dict:
        """Carga colores desde colors_config.json."""
        try:
            colors = load_colors()  # Carga global
            return colors
        except Exception:
            logging.exception('Error cargando colors, usando fallback')
            return {
                'dialog_bg': '#000000',
                'dialog_text': '#00FF00',
                'success': '#2ecc71',
                'error': '#e74c3c',
                'warning': '#f39c12',
                'info': '#3498db'
            }

    def _setup_window(self):
        """Configurar propiedades de la ventana."""
        global_cfg = self.config.get('global', {})
        type_cfg = self.config.get('types', {}).get(self.tipo, {})

        # Título
        self.title(self.titulo or 'Dialog')

        # Tamaño (permite override por tipo)
        width = type_cfg.get('width', global_cfg.get('width', 700))
        height = type_cfg.get('height', global_cfg.get('height', 500))
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)

        # Colores
        bg_key = global_cfg.get('bg_color_key', 'dialog_bg')
        bg_color = self.colors.get(bg_key, '#000000')

        border_key = type_cfg.get('border_color_key', 'info')
        border_color = self.colors.get(border_key, '#3498db')

        border_width = global_cfg.get('border_width', 4)
        corner_radius = global_cfg.get('corner_radius', 0)

        try:
            self.configure(
                fg_color=bg_color,
                border_width=border_width,
                border_color=border_color,
                corner_radius=corner_radius
            )
        except Exception:
            logging.exception('Error configurando ventana')

    def _center_window(self):
        """Centrar ventana respecto al padre o pantalla."""
        try:
            self.update_idletasks()
            w = self.winfo_width()
            h = self.winfo_height()

            parent = self.master
            if parent and hasattr(parent, 'winfo_ismapped') and parent.winfo_ismapped():
                try:
                    parent.update_idletasks()
                    px = parent.winfo_rootx()
                    py = parent.winfo_rooty()
                    pw = parent.winfo_width() or parent.winfo_reqwidth()
                    ph = parent.winfo_height() or parent.winfo_reqheight()
                    x = px + max(0, (pw - w) // 2)
                    y = py + max(0, (ph - h) // 2)
                except Exception:
                    x = (self.winfo_screenwidth() // 2) - (w // 2)
                    y = (self.winfo_screenheight() // 2) - (h // 2)
            else:
                x = (self.winfo_screenwidth() // 2) - (w // 2)
                y = (self.winfo_screenheight() // 2) - (h // 2)

            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            logging.exception('Error centrando ventana')

    def _load_icon(self) -> Optional[ctk.CTkImage]:
        """Cargar icono según tipo desde assets/dialogs."""
        if Image is None:
            return None

        try:
            type_cfg = self.config.get('types', {}).get(self.tipo, {})
            icon_filename = type_cfg.get('icon', f'dialog_{self.tipo}.png')

            # Buscar carpeta assets
            base = Path(__file__).resolve().parents[2]  # kool_tpv/
            icon_path = base / 'assets' / 'dialogs' / icon_filename

            if not icon_path.exists():
                logging.warning(f'Icono no encontrado: {icon_path}')
                return None

            icon_size = self.config.get('global', {}).get('icon_size', 120)

            img = Image.open(icon_path).convert('RGBA')
            img = img.resize((icon_size, icon_size), Image.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(icon_size, icon_size))
            logging.info(f'Icono cargado: {icon_path}')
            return ctk_img

        except Exception:
            logging.exception(f'Error cargando icono para tipo {self.tipo}')
            return None

    def _safe_close(self, result=None):
        """Cerrar dialog de forma segura ejecutando callback y liberando recursos."""
        self.result = result

        # Ejecutar callback
        if self.callback and callable(self.callback):
            try:
                self.callback(result)
            except Exception:
                logging.exception('Error ejecutando callback de dialog')

        # Logging
        action = 'confirmado' if result else 'cancelado'
        logging.info(f"Dialog '{self.tipo}' {action}")

        # Liberar grab y DialogManager
        try:
            self.grab_release()
        except Exception:
            pass

        DialogManager.unregister()

        # Destruir ventana
        try:
            self.destroy()
        except Exception:
            logging.exception('Error destruyendo dialog')

    def _get_title_font(self):
        """Obtener fuente para título desde config."""
        font_type = self.config.get('global', {}).get('title_font', 'title')
        return get_font(font_type)

    def _get_message_font(self):
        """Obtener fuente para mensaje desde config."""
        font_type = self.config.get('global', {}).get('message_font', 'subtitle')
        return get_font(font_type)

    def _get_title_color(self) -> str:
        """Obtener color para título según tipo."""
        type_cfg = self.config.get('types', {}).get(self.tipo, {})
        color_key = type_cfg.get('title_color_key', 'dialog_text')
        return self.colors.get(color_key, '#00FF00')
