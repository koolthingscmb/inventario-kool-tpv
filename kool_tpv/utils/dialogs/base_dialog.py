"""
Clase base para diálogos modales con configuración desde JSON.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import logging

from .config_loader import load_dialog_config, FALLBACKS
from .content_container import create_dialog_content_container
from kool_tpv.utils.factories.button_factory import ButtonFactory


class BaseDialog(ctk.CTkToplevel):
    """Diálogo modal base con configuración desde JSON.

    Carga colores, fuentes y geometría desde archivos de configuración.
    Las subclases implementan el contenido específico en _crear_contenido().
    """

    def __init__(self, parent, tipo='info', titulo='', callback=None):
        super().__init__(parent)

        self.callback = callback
        # parent used to schedule callbacks so they survive dialog destruction
        try:
            self._cb_parent = parent if parent is not None and callable(getattr(parent, 'after', None)) else self
        except Exception:
            self._cb_parent = self

        # Cargar configuración desde JSON
        self.dialogs_colors, self.fonts_data, self.geometry_cfg, self.fallbacks = load_dialog_config()

        # Filtrar tipos válidos
        valid_dialog_types = ['info', 'success', 'warning', 'error', 'password']
        allowed_types = [k for k in self.dialogs_colors.keys() if k in valid_dialog_types] if self.dialogs_colors else valid_dialog_types
        self.tipo = tipo if tipo in allowed_types else 'info'
        self.result = None

        # Configurar ventana
        self.title(titulo)
        self._setup_geometry(parent)
        self.resizable(False, False)

        # Aplicar estilos
        self._apply_styles()

        # Setup modal
        self._setup_modal(parent)

    def _setup_geometry(self, parent):
        """Configurar geometría de ventana."""
        try:
            width = self.geometry_cfg.get('width') if isinstance(self.geometry_cfg.get('width'), int) else None
            height = self.geometry_cfg.get('height') if isinstance(self.geometry_cfg.get('height'), int) else None
        except Exception:
            width = None
            height = None

        # Valores calculados si faltan
        try:
            self.update_idletasks()
            if not width:
                width = int(self.winfo_screenwidth() * 0.6)
            if not height:
                height = int(self.winfo_screenheight() * 0.45)
        except Exception:
            width = width or self.fallbacks['geometry']['width']
            height = height or self.fallbacks['geometry']['height']

        self.geometry(f"{width}x{height}")
        self._dialog_width = width
        self._center_window(parent, width, height)

    def _apply_styles(self):
        """Aplicar colores y bordes desde configuración."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        try:
            bg = tipo_config.get('bg', None)
            border_color = tipo_config.get('border', None)
            border_width = int(self.geometry_cfg.get('border_width', self.fallbacks['geometry']['border_width'])) if isinstance(self.geometry_cfg.get('border_width', None), int) else int(max(1, min(self._dialog_width, 400) * 0.01))

            if bg is not None:
                self.configure(fg_color=bg)
            if border_color is not None:
                self.configure(border_width=border_width, border_color=border_color)
        except Exception as e:
            logging.warning(f"Error aplicando estilos: {e}")

    def _setup_modal(self, parent):
        """Configurar comportamiento modal."""
        try:
            self.withdraw()
        except Exception:
            pass
        try:
            self.transient(parent)
        except Exception:
            pass
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

    def _center_window(self, parent, w, h):
        """Centra la ventana en el centro de la pantalla.

        Todos los diálogos aparecen en el mismo lugar (centro de pantalla),
        independientemente de dónde esté la ventana padre.
        """
        try:
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (w // 2)
            y = (self.winfo_screenheight() // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception as e:
            logging.warning(f"Error centrando ventana: {e}")

    def _get_font(self, font_key):
        """Obtiene tupla de fuente desde configuración."""
        try:
            dialog_fonts = self.fonts_data.get('components', {}).get('dialog', {})
            font_data = dialog_fonts.get(font_key, {})

            fallback_map = {
                'title': 'dialog_title',
                'message': 'dialog_message',
                'button': 'dialog_button',
                'input': 'dialog_input'
            }
            fallback_key = fallback_map.get(font_key, 'dialog_message')
            fallback_font_tuple = self.fallbacks.get('fonts', {}).get(fallback_key, ('Courier New', 16))

            family = font_data.get('family') or fallback_font_tuple[0]
            size = font_data.get('size') or fallback_font_tuple[1]
            weight = font_data.get('weight', 'normal')

            if weight and weight != 'normal':
                return (family, size, weight)
            return (family, size)
        except Exception:
            fallback_map = {
                'title': 'dialog_title',
                'message': 'dialog_message',
                'button': 'dialog_button',
                'input': 'dialog_input'
            }
            fallback_key = fallback_map.get(font_key, 'dialog_message')
            return self.fallbacks.get('fonts', {}).get(fallback_key, ('Courier New', 16))

    def _get_button_style_key(self):
        """Obtiene style_key de ButtonFactory según tipo."""
        style_map = {
            'info': 'dialog_info_btn',
            'success': 'dialog_success_btn',
            'warning': 'dialog_warning_btn',
            'error': 'dialog_error_btn',
            'password': 'dialog_password_btn'
        }
        return style_map.get(self.tipo, 'dialog_info_btn')

    def _setup_button_focus(self, btn, is_accept=True):
        """Configura eventos de foco en un botón."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        focus_border = tipo_config.get('button_focus_border', self.fallbacks['colors']['button_focus_border'])
        focus_width = int(self.geometry_cfg.get('focus_border_width', self.fallbacks['geometry']['focus_border_width'])) if isinstance(self.geometry_cfg.get('focus_border_width', None), int) else int(self.fallbacks['geometry']['focus_border_width'])
        try:
            normal_width = int(btn.cget('border_width'))
        except Exception:
            normal_width = 0
        try:
            normal_border_color = btn.cget('border_color')
        except Exception:
            normal_border_color = None

        def on_focus_in(event):
            try:
                btn.configure(border_width=focus_width, border_color=focus_border)
            except Exception:
                pass

        def on_focus_out(event):
            try:
                if normal_border_color is not None:
                    btn.configure(border_width=normal_width, border_color=normal_border_color)
                else:
                    btn.configure(border_width=normal_width)
            except Exception:
                pass

        try:
            btn.bind('<FocusIn>', on_focus_in)
            btn.bind('<FocusOut>', on_focus_out)
        except Exception:
            pass

        try:
            if is_accept:
                btn.bind('<Return>', lambda e: self._on_accept() or "break")
            else:
                btn.bind('<Return>', lambda e: self._on_cancel() or "break")
        except Exception:
            pass

    def _calcular_wraplength(self):
        """Calcula wraplength dinámico basado en configuración."""
        wraplength_cfg = self.geometry_cfg.get('wraplength', self.fallbacks['geometry']['wraplength'])
        if wraplength_cfg == 'auto':
            padding_x = int(self.geometry_cfg.get('padding_x', 20))
            return max(200, self._dialog_width - (padding_x * 2) - 40)
        else:
            return int(wraplength_cfg) if isinstance(wraplength_cfg, (int, float)) else int(self.fallbacks['geometry']['wraplength'])

    def _crear_barra_titulo(self, parent, titulo):
        """Crea la barra superior con color de fondo según tipo, icono pequeño y título.

        Args:
            parent: Frame contenedor donde se empaqueta la barra.
            titulo: Texto del título (se convierte a mayúsculas).

        Returns:
            El frame de contenido inferior (donde deben ir mensaje, entry, etc.)
        """
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        bar_bg = tipo_config.get('title_bar_bg', self.fallbacks['colors']['title_bar_bg'])
        bar_text = tipo_config.get('title_bar_text', self.fallbacks['colors']['title_bar_text'])
        bar_height = int(self.geometry_cfg.get('title_bar_height', self.fallbacks['geometry']['title_bar_height']))
        bar_icon_size = int(self.geometry_cfg.get('icon_size', self.fallbacks['geometry']['icon_size']))
        bar_pad = max(4, bar_height // 6)

        # Barra superior
        bar = ctk.CTkFrame(parent, fg_color=bar_bg, corner_radius=0, height=bar_height)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)

        # Icono pequeño en la barra
        icon_img = self._cargar_icono(bar_icon_size)
        if icon_img:
            lbl_icon = ctk.CTkLabel(bar, image=icon_img, text='', fg_color=bar_bg)
            lbl_icon.image = icon_img
            lbl_icon.pack(side='left', padx=(bar_pad, bar_pad))

        # Título en la barra
        title_font = self._get_font('title')
        lbl_title = ctk.CTkLabel(
            bar,
            text=titulo.upper(),
            font=title_font,
            text_color=bar_text,
            fg_color=bar_bg
        )
        lbl_title.pack(side='left', padx=(0, bar_pad))

        # Frame de contenido debajo de la barra
        content_bg = tipo_config.get('bg', self.fallbacks['colors']['bg'])
        content_frame = ctk.CTkFrame(parent, fg_color=content_bg, corner_radius=0)
        content_frame.pack(fill='both', expand=True)
        return content_frame

    def _crear_botones(self, parent, btn_text='Aceptar', confirm=False):
        """Crea los botones del diálogo de forma unificada.

        Args:
            parent: Frame contenedor.
            btn_text: Texto del botón principal.
            confirm: Si True, muestra Cancelar + Aceptar. Si False, solo Aceptar.

        Returns:
            El botón principal (para focus_set).
        """
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        button_font = self._get_font('button')
        btn_w = int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width']))
        btn_h = int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height']))
        corner_radius = int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius']))
        style_key = self._get_button_style_key()

        btn_frame = ctk.CTkFrame(parent, fg_color='transparent')
        btn_frame.pack(pady=(0, 10))

        if confirm:
            # Cancelar
            try:
                btn_cancel = ButtonFactory.create_button(
                    parent=btn_frame,
                    text='CANCELAR',
                    command=self._on_cancel,
                    style_key='dialog_cancel_btn',
                    font=button_font
                )
            except Exception:
                btn_cancel = ctk.CTkButton(
                    btn_frame,
                    text='CANCELAR',
                    command=self._on_cancel,
                    fg_color=tipo_config.get('cancel_bg', self.fallbacks['colors']['cancel_bg']),
                    hover_color=tipo_config.get('cancel_hover', self.fallbacks['colors']['cancel_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=btn_w,
                    height=btn_h,
                    corner_radius=corner_radius,
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
            except Exception:
                btn_accept = ctk.CTkButton(
                    btn_frame,
                    text=btn_text.upper(),
                    command=self._on_accept,
                    fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                    hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=btn_w,
                    height=btn_h,
                    corner_radius=corner_radius,
                    border_width=0
                )
            btn_accept.pack(side='left')
            self._setup_button_focus(btn_accept, is_accept=True)

            # Navegación TAB
            try:
                btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
                btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
            except Exception:
                pass

            self.btn_cancel = btn_cancel
            self.btn_accept = btn_accept
            return btn_accept
        else:
            # Botón único
            try:
                btn = ButtonFactory.create_button(
                    parent=btn_frame,
                    text=btn_text,
                    command=self._on_close,
                    style_key=style_key,
                    font=button_font
                )
            except Exception:
                btn = ctk.CTkButton(
                    btn_frame,
                    text=btn_text.upper(),
                    command=self._on_close,
                    fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                    hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                    text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                    font=button_font,
                    width=btn_w,
                    height=btn_h,
                    corner_radius=corner_radius,
                    border_width=0
                )
            btn.pack()
            self._setup_button_focus(btn, is_accept=True)
            return btn

    def _cargar_icono(self, size=None):
        """Cargar icono según tipo, redimensionado al tamaño indicado."""
        try:
            base = Path(__file__).resolve().parents[2]
            icons_dir = base / "assets" / "dialogs"
            preferred = icons_dir / f"dialog_{self.tipo}.png"

            tried = [preferred]
            if not preferred.exists():
                fallback = icons_dir / "dialog_error.png"
                tried.append(fallback)

            icon_size = int(size if size is not None else self.geometry_cfg.get('icon_size', self.fallbacks['geometry']['icon_size']))
            for p in tried:
                try:
                    if p.exists():
                        logging.info(f'Loading dialog icon: {p}')
                        img = Image.open(p)
                        img = img.resize((icon_size, icon_size), Image.LANCZOS)
                        return ctk.CTkImage(light_image=img, dark_image=img, size=(icon_size, icon_size))
                except Exception:
                    logging.exception(f'Error cargando icono desde {p}')
        except Exception:
            logging.exception(f'Error cargando icono dialog_{self.tipo}.png')

        return None

    def _on_accept(self):
        """Método a sobrescribir en subclases."""
        pass

    def _on_cancel(self):
        """Método a sobrescribir en subclases."""
        pass

    def _on_close(self):
        """Método a sobrescribir en subclases."""
        pass
