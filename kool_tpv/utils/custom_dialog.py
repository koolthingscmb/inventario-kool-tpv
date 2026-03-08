"""
Custom Dialog helper para diálogos modales con branding corporativo.

Soporta 4 tipos: success, error, warning, info
con iconos temáticos D&D y colores apropiados.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import logging
import json


def _load_dialog_config():
    """Carga configuración de diálogos desde JSON con fallbacks centralizados.

    Returns:
        tuple: (colors_dict, fonts_dict, geometry_dict, fallbacks_dict)
    """
    # Fallbacks centralizados (solo se usan si falla la carga del JSON)
    FALLBACKS = {
        'colors': {
            'bg': '#000000',
            'border': '#3498db',
            'title_text': '#00FF00',
            'message_text': '#FFFFFF',
            'button_bg': '#3498db',
            'button_hover': '#2980b9',
            'button_text': '#000000',
            'cancel_bg': '#666666',
            'cancel_hover': '#555555',
            'button_focus_border': '#FFFFFF'
        },
        'geometry': {
            'width': 580,
            'height': 400,
            'border_width': 4,
            'icon_size': 96,
            'button_width': 160,
            'button_height': 55,
            'corner_radius': 0,
            'wraplength': 500,
            'focus_border_width': 3,
            'entry_width': 300,
            'entry_height': 35
        },
        'fonts': {
            'dialog_title': ('Courier New', 28, 'bold'),
            'dialog_message': ('Courier New', 20),
            'dialog_button': ('Courier New', 18, 'bold'),
            'dialog_input': ('Roboto-Regular', 16)
        }
    }

    try:
        config_dir = Path(__file__).resolve().parents[1] / "config"

        # Cargar colores
        with open(config_dir / "colors_config.json", 'r', encoding='utf-8') as f:
            colors_data = json.load(f)
            dialogs_colors = colors_data.get('global', {}).get('dialogs', {})

        # Cargar fuentes
        with open(config_dir / "font_config.json", 'r', encoding='utf-8') as f:
            fonts_data = json.load(f)

        # Extraer geometría
        geometry = dialogs_colors.get('geometry', {})

        return dialogs_colors, fonts_data, geometry, FALLBACKS

    except Exception as e:
        logging.exception("Error cargando configuración de diálogos, usando fallbacks")
        # En caso de error total, devolver solo fallbacks
        return {}, {}, {}, FALLBACKS


class CustomDialog(ctk.CTkToplevel):
    """Diálogo modal personalizado que toma estilos desde JSON.

    Carga colores, fuentes y geometría desde los archivos de configuración
    y aplica valores de forma defensiva. Mantiene la API pública.
    """

    def __init__(self, parent, tipo='info', titulo='', mensaje='', btn_text='Aceptar', callback=None, confirm=False):
        """
        Args:
            parent: Ventana padre
            tipo: 'success', 'error', 'warning', 'info'
            titulo: Título del diálogo
            mensaje: Mensaje a mostrar
            btn_text: Texto del botón
            callback: Función a ejecutar al cerrar (opcional)
        """
        super().__init__(parent)

        self.callback = callback
        # Cargar configuración desde JSON
        self.dialogs_colors, self.fonts_data, self.geometry_cfg, self.fallbacks = _load_dialog_config()

        allowed_types = list(self.dialogs_colors.keys()) if self.dialogs_colors else ['info', 'success', 'warning', 'error', 'password']
        self.tipo = tipo if tipo in allowed_types else 'info'
        self.confirm = bool(confirm)
        self.result = False

        # Configurar ventana
        self.title(titulo)
        # geometry desde configuración o valores relativos a pantalla
        try:
            width = self.geometry_cfg.get('width') if isinstance(self.geometry_cfg.get('width'), int) else None
            height = self.geometry_cfg.get('height') if isinstance(self.geometry_cfg.get('height'), int) else None
        except Exception:
            width = None
            height = None

        # Valores calculados si faltan en la config
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
        self.resizable(False, False)

        # Obtener configuración del tipo específico
        tipo_config = self.dialogs_colors.get(self.tipo, {})

        try:
            bg = tipo_config.get('bg', None)
            border_color = tipo_config.get('border', None)
            border_width = int(self.geometry_cfg.get('border_width', self.fallbacks['geometry']['border_width'])) if isinstance(self.geometry_cfg.get('border_width', None), int) else int( max(1, min(width, height) * 0.01) )

            if bg is not None:
                self.configure(fg_color=bg)
            if border_color is not None:
                self.configure(border_width=border_width, border_color=border_color)
        except Exception as e:
            logging.warning(f"Error aplicando estilos: {e}")

        # Prepare window hidden so we can set geometry before mapping
        try:
            self.withdraw()
        except Exception:
            pass

        # Modal (set transient while hidden)
        try:
            self.transient(parent)
        except Exception:
            pass

        # Centrar ventana
        try:
            self._center_window(parent, width, height)
        except Exception:
            pass

        # Show window immediately (no animation) and then grab focus
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

        self._crear_contenido(titulo, mensaje, btn_text)

        # Bindings globales (solo ESC para cerrar/cancelar)
        try:
            if self.confirm:
                self.bind('<Escape>', lambda e: self._on_cancel())
            else:
                self.bind('<Escape>', lambda e: self._on_close())
        except Exception:
            try:
                self.bind('<Escape>', lambda e: self._on_close())
            except Exception:
                pass

        # Foco en el botón (sin delay)
        try:
            self.btn.focus_set()
        except Exception:
            pass

    def _center_window(self, parent, w, h):
        """Centra la ventana respecto al padre o pantalla."""
        try:
            self.update_idletasks()
            if parent is not None and getattr(parent, 'winfo_ismapped', None) and parent.winfo_ismapped():
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
        except Exception as e:
            logging.warning(f"Error centrando ventana: {e}")

    def _get_font(self, font_key):
        """Obtiene tupla de fuente desde configuración.

        Args:
            font_key: Clave en font_config.json (ej: 'dialog_title')

        Returns:
            tuple: (family, size, weight) o (family, size)
        """
        try:
            font_data = self.fonts_data.get(font_key, {})
            # Prefer values from font_config.json, otherwise use centralized fallback
            fallback_font_tuple = self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')
            family = font_data.get('family') or fallback_font_tuple[0]
            size = font_data.get('size') or fallback_font_tuple[1]
            weight = font_data.get('weight', 'normal')

            if weight and weight != 'normal':
                return (family, size, weight)
            return (family, size)
        except Exception:
            # Si falla, intentar obtener del fallback o usar default mínimo
            try:
                # Devolver la entrada desde FALLBACKS; asumimos que existe
                return self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')
            except Exception:
                return self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')

    def _setup_button_focus(self, btn, is_accept=True):
        """Configura eventos de foco en un botón.

        Args:
            btn: Widget CTkButton
            is_accept: True si es botón Aceptar, False si es Cancelar
        """
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        focus_border = tipo_config.get('button_focus_border', self.fallbacks['colors']['button_focus_border'])
        focus_width = int(self.geometry_cfg.get('focus_border_width', self.fallbacks['geometry']['focus_border_width'])) if isinstance(self.geometry_cfg.get('focus_border_width', None), int) else int(self.fallbacks['geometry']['focus_border_width'])
        normal_width = 0  # Sin borde cuando no tiene foco

        def on_focus_in(event):
            try:
                btn.configure(border_width=focus_width, border_color=focus_border)
            except Exception:
                pass

        def on_focus_out(event):
            try:
                btn.configure(border_width=normal_width)
            except Exception:
                pass

        # Bind eventos de foco
        try:
            btn.bind('<FocusIn>', on_focus_in)
            btn.bind('<FocusOut>', on_focus_out)
        except Exception:
            pass

        # Bind Enter para ejecutar acción del botón
        try:
            if is_accept:
                btn.bind('<Return>', lambda e: self._on_accept())
            else:
                btn.bind('<Return>', lambda e: self._on_cancel())
        except Exception:
            pass

    def _cargar_icono(self):
        """Cargar icono según tipo."""
        try:
            base = Path(__file__).resolve().parents[1]  # kool_tpv/
            icons_dir = base / "assets" / "dialogs"
            preferred = icons_dir / f"dialog_{self.tipo}.png"

            tried = []
            # Try preferred
            tried.append(preferred)
            if not preferred.exists():
                # fallback to a generic warning/error icon
                fallback = icons_dir / "dialog_error.png"
                tried.append(fallback)

            icon_size = int(self.geometry_cfg.get('icon_size', self.fallbacks['geometry']['icon_size'])) if isinstance(self.geometry_cfg.get('icon_size', None), int) else int(self.fallbacks['geometry']['icon_size'])
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

    def _crear_contenido(self, titulo, mensaje, btn_text):
        """Crear widgets del diálogo usando configuración."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})

        # Obtener fuentes
        title_font = self._get_font('dialog_title')
        message_font = self._get_font('dialog_message')
        button_font = self._get_font('dialog_button')

        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(0, 10))

        # Título
        if titulo:
            title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
            titulo_label = ctk.CTkLabel(
                main_frame,
                text=titulo.upper(),
                font=title_font,
                text_color=title_color
            )
            titulo_label.pack(pady=(10, 15))

        # Mensaje
        if mensaje:
            msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
            wraplength = int(self.geometry_cfg.get('wraplength', self.fallbacks['geometry']['wraplength'])) if isinstance(self.geometry_cfg.get('wraplength', None), int) else int(self.fallbacks['geometry']['wraplength'])
            mensaje_label = ctk.CTkLabel(
                main_frame,
                text=mensaje.upper(),
                font=message_font,
                text_color=msg_color,
                wraplength=wraplength,
                justify='center'
            )
            mensaje_label.pack(pady=(0, 25))

        # Botones usando geometría
        btn_width = int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])) if isinstance(self.geometry_cfg.get('button_width', None), int) else int(self.fallbacks['geometry']['button_width'])
        btn_height = int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])) if isinstance(self.geometry_cfg.get('button_height', None), int) else int(self.fallbacks['geometry']['button_height'])
        corner_radius = int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])) if isinstance(self.geometry_cfg.get('corner_radius', None), int) else int(self.fallbacks['geometry']['corner_radius'])

        if self.confirm:
            btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
            btn_frame.pack()

            # Cancelar
            btn_cancel = ctk.CTkButton(
                btn_frame,
                text='CANCELAR',
                command=self._on_cancel,
                fg_color=tipo_config.get('cancel_bg', self.fallbacks['colors']['cancel_bg']),
                hover_color=tipo_config.get('cancel_hover', self.fallbacks['colors']['cancel_hover']),
                text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                font=button_font,
                width=btn_width,
                height=btn_height,
                corner_radius=corner_radius,
                border_width=0  # Inicial sin borde
            )
            btn_cancel.pack(side='left', padx=(0, 10))
            self._setup_button_focus(btn_cancel, is_accept=False)

            # Aceptar
            btn_accept = ctk.CTkButton(
                btn_frame,
                text=btn_text.upper(),
                command=self._on_accept,
                fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                font=button_font,
                width=btn_width,
                height=btn_height,
                corner_radius=corner_radius,
                border_width=0  # Inicial sin borde
            )
            btn_accept.pack(side='left')
            self._setup_button_focus(btn_accept, is_accept=True)
            self.btn = btn_accept

            # Configurar navegación TAB
            try:
                btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
                btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
            except Exception:
                pass

            # Referencias para cleanup
            self.btn_cancel = btn_cancel
            self.btn_accept = btn_accept

        else:
            # Botón único
            self.btn = ctk.CTkButton(
                main_frame,
                text=btn_text.upper(),
                command=self._on_close,
                fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
                hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
                text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
                font=button_font,
                width=btn_width,
                height=btn_height,
                corner_radius=corner_radius,
                border_width=0
            )
            self.btn.pack()
            self._setup_button_focus(self.btn, is_accept=True)

    def _on_close(self):
        """Cerrar diálogo y ejecutar callback si existe."""
        try:
            if self.callback and callable(self.callback):
                self.callback()
        except Exception:
            logging.exception('Error ejecutando callback de CustomDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_accept(self):
        try:
            self.result = True
            if self.callback and callable(self.callback):
                try:
                    self.callback(True)
                except Exception:
                    logging.exception('Error ejecutando callback en accept')
        except Exception:
            logging.exception('Error en _on_accept CustomDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        try:
            self.result = False
            if self.callback and callable(self.callback):
                try:
                    self.callback(False)
                except Exception:
                    logging.exception('Error ejecutando callback en cancel')
        except Exception:
            logging.exception('Error en _on_cancel CustomDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()


def show_success(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de éxito."""
    """Mostrar diálogo de éxito.

    Siempre devuelve True (el usuario confirmó haber visto el mensaje).
    """
    dlg = CustomDialog(parent, tipo='success', titulo=titulo, mensaje=mensaje, callback=callback)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return True  # Success siempre devuelve True (usuario vio el mensaje)


def show_error(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de error.

    Si confirm=True, muestra botones 'Cancelar' y 'Aceptar' y devuelve True/False.
    Útil para: "Error al guardar, ¿Reintentar?"
    """
    dlg = CustomDialog(parent, tipo='error', titulo=titulo, mensaje=mensaje, 
                       callback=callback, confirm=confirm)
    try:
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False)


def show_warning(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de advertencia.

    Si confirm=True, muestra botones 'Cancelar' y 'Aceptar' y devuelve True/False.
    """
    dlg = CustomDialog(parent, tipo='warning', titulo=titulo, mensaje=mensaje, 
                       callback=callback, confirm=confirm)
    try:
        # Bloquear ejecución hasta que el usuario responda
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False)


def show_info(parent, titulo, mensaje, callback=None, confirm=False):
    """Mostrar diálogo de información."""
    dlg = CustomDialog(parent, tipo='info', titulo=titulo, mensaje=mensaje, callback=callback, confirm=confirm)
    try:
        # Modal: wait for user action
        dlg.wait_window()
    except Exception:
        pass
    return getattr(dlg, 'result', False if confirm else True)


class CustomInputDialog(ctk.CTkToplevel):
    """Diálogo de entrada personalizado con icono y validación.

    Soporta enmascarado cuando se solicita un `password` (show='*').
    """

    def __init__(self, parent, tipo='success', titulo='', mensaje='', valor_defecto='', callback=None, password=False):
        """
        Args:
            parent: Ventana padre
            tipo: tipo de icono ('success' recomendado para tesoro)
            titulo: Título del diálogo
            mensaje: Mensaje/pregunta
            valor_defecto: Valor inicial del campo
            callback: Función a ejecutar al aceptar (recibe valor como arg)
        """
        super().__init__(parent)

        self.callback = callback
        # Cargar configuración
        self.dialogs_colors, self.fonts_data, self.geometry_cfg, self.fallbacks = _load_dialog_config()

        allowed_types = list(self.dialogs_colors.keys()) if self.dialogs_colors else ['info', 'success', 'warning', 'error', 'password']
        self.tipo = tipo if tipo in allowed_types else 'success'
        self.result = None
        self.password = bool(password)

        # Configurar ventana y geometría
        self.title(titulo)
        try:
            width = self.geometry_cfg.get('width') if isinstance(self.geometry_cfg.get('width'), int) else None
            height = self.geometry_cfg.get('height') if isinstance(self.geometry_cfg.get('height'), int) else None
        except Exception:
            width = None
            height = None

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
        self.resizable(False, False)
        try:
            tipo_config = self.dialogs_colors.get(self.tipo, {})
            bg = tipo_config.get('bg', None)
            border_color = tipo_config.get('border', None)
            border_width = int(self.geometry_cfg.get('border_width', self.fallbacks['geometry']['border_width'])) if isinstance(self.geometry_cfg.get('border_width', None), int) else int(self.fallbacks['geometry']['border_width'])
            if bg is not None:
                self.configure(fg_color=bg)
            if border_color is not None:
                self.configure(border_width=border_width, border_color=border_color)
        except Exception:
            pass

        # Prepare window hidden and transient
        try:
            self.withdraw()
        except Exception:
            pass
        try:
            self.transient(parent)
        except Exception:
            pass

        try:
            self._center_window(parent, width, height)
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

        # crear contenido
        self._crear_contenido(titulo, mensaje, valor_defecto)


        # Bindings globales (solo ESC para cancelar)
        try:
            self.bind('<Escape>', lambda e: self._on_cancel())
        except Exception:
            pass

        try:
            self.entry.focus_set()
        except Exception:
            pass

    def _cargar_icono(self):
        """Cargar icono según tipo."""
        try:
            base = Path(__file__).resolve().parents[1]  # kool_tpv/
            icon_path = base / "assets" / "dialogs" / f"dialog_{self.tipo}.png"

            icon_size = int(self.geometry_cfg.get('icon_size', self.fallbacks['geometry']['icon_size'])) if isinstance(self.geometry_cfg.get('icon_size', None), int) else int(self.fallbacks['geometry']['icon_size'])
            if icon_path.exists():
                img = Image.open(icon_path)
                img = img.resize((icon_size, icon_size), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(icon_size, icon_size))
        except Exception:
            logging.exception(f'Error cargando icono dialog_{self.tipo}.png en InputDialog')

        return None

    def _crear_contenido(self, titulo, mensaje, valor_defecto):
        """Crear widgets del diálogo InputDialog usando configuración."""
        tipo_config = self.dialogs_colors.get(self.tipo, {})

        # Fuentes
        title_font = None
        try:
            title_font = self._get_font('dialog_title')
        except Exception:
            # Obtener desde FALLBACKS (debe existir)
            try:
                title_font = self.fallbacks.get('fonts', {}).get('dialog_title')
            except Exception:
                title_font = None
        input_font = self._get_font('dialog_input')
        button_font = self._get_font('dialog_button')

        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(10, 15))

        # Título
        if titulo:
            title_color = tipo_config.get('title_text', self.fallbacks['colors']['title_text'])
            titulo_label = ctk.CTkLabel(
                main_frame,
                text=titulo.upper(),
                font=title_font,
                text_color=title_color
            )
            titulo_label.pack(pady=(0, 15))

        # Mensaje
        if mensaje:
            msg_color = tipo_config.get('message_text', self.fallbacks['colors']['message_text'])
            wraplength = int(self.geometry_cfg.get('wraplength', self.fallbacks['geometry']['wraplength'])) if isinstance(self.geometry_cfg.get('wraplength', None), int) else int(self.fallbacks['geometry']['wraplength'])
            mensaje_label = ctk.CTkLabel(
                main_frame,
                text=mensaje.upper(),
                font=self._get_font('dialog_message'),
                text_color=msg_color,
                wraplength=wraplength,
                justify='center'
            )
            mensaje_label.pack(pady=(0, 20))

        # Entry
        entry_width = int(self.geometry_cfg.get('entry_width', self.fallbacks['geometry']['entry_width'])) if isinstance(self.geometry_cfg.get('entry_width', None), int) else int(self.fallbacks['geometry']['entry_width'])
        entry_height = int(self.geometry_cfg.get('entry_height', self.fallbacks['geometry']['entry_height'])) if isinstance(self.geometry_cfg.get('entry_height', None), int) else int(self.fallbacks['geometry']['entry_height'])

        entry_params = {
            "master": main_frame,
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
        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack()

        # CANCELAR
        btn_cancel = ctk.CTkButton(
            btn_frame,
            text='CANCELAR',
            command=self._on_cancel,
            fg_color=tipo_config.get('cancel_bg', self.fallbacks['colors']['cancel_bg']),
            hover_color=tipo_config.get('cancel_hover', self.fallbacks['colors']['cancel_hover']),
            text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
            font=button_font,
            width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])) if isinstance(self.geometry_cfg.get('button_width', None), int) else int(self.fallbacks['geometry']['button_width']),
            height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])) if isinstance(self.geometry_cfg.get('button_height', None), int) else int(self.fallbacks['geometry']['button_height']),
            corner_radius=int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])) if isinstance(self.geometry_cfg.get('corner_radius', None), int) else int(self.fallbacks['geometry']['corner_radius']),
            border_width=0
        )
        btn_cancel.pack(side='left', padx=(0, 10))

        # ACEPTAR
        btn_accept = ctk.CTkButton(
            btn_frame,
            text='ACEPTAR',
            command=self._on_accept,
            fg_color=tipo_config.get('button_bg', self.fallbacks['colors']['button_bg']),
            hover_color=tipo_config.get('button_hover', self.fallbacks['colors']['button_hover']),
            text_color=tipo_config.get('button_text', self.fallbacks['colors']['button_text']),
            font=button_font,
            width=int(self.geometry_cfg.get('button_width', self.fallbacks['geometry']['button_width'])) if isinstance(self.geometry_cfg.get('button_width', None), int) else int(self.fallbacks['geometry']['button_width']),
            height=int(self.geometry_cfg.get('button_height', self.fallbacks['geometry']['button_height'])) if isinstance(self.geometry_cfg.get('button_height', None), int) else int(self.fallbacks['geometry']['button_height']),
            corner_radius=int(self.geometry_cfg.get('corner_radius', self.fallbacks['geometry']['corner_radius'])) if isinstance(self.geometry_cfg.get('corner_radius', None), int) else int(self.fallbacks['geometry']['corner_radius']),
            border_width=0
        )
        btn_accept.pack(side='left')
        self.btn = btn_accept

        # Focus behavior and TAB navigation
        try:
            self._setup_button_focus(btn_cancel, is_accept=False)
            self._setup_button_focus(btn_accept, is_accept=True)
            btn_cancel.bind('<Tab>', lambda e: (btn_accept.focus_set(), 'break'))
            btn_accept.bind('<Tab>', lambda e: (btn_cancel.focus_set(), 'break'))
        except Exception:
            pass

    def _on_accept(self):
        """Aceptar: ejecutar callback con el valor ingresado."""
        valor = self.entry.get().strip()
        self.result = valor
        try:
            if self.callback and callable(self.callback):
                self.callback(valor)
        except Exception:
            logging.exception('Error ejecutando callback de CustomInputDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar sin ejecutar callback."""
        self.result = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _center_window(self, parent, w, h):
        """Centra la ventana respecto al padre o pantalla."""
        try:
            self.update_idletasks()
            if parent is not None and getattr(parent, 'winfo_ismapped', None) and parent.winfo_ismapped():
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
        except Exception as e:
            logging.warning(f"Error centrando ventana InputDialog: {e}")

    def _setup_button_focus(self, btn, is_accept=True):
        """Configura eventos de foco en un botón para InputDialog.

        Args:
            btn: Widget CTkButton
            is_accept: True si es botón Aceptar, False si es Cancelar
        """
        tipo_config = self.dialogs_colors.get(self.tipo, {})
        focus_border = tipo_config.get('button_focus_border', self.fallbacks['colors']['button_focus_border'])
        focus_width = int(self.geometry_cfg.get('focus_border_width', self.fallbacks['geometry']['focus_border_width'])) if isinstance(self.geometry_cfg.get('focus_border_width', None), int) else int(self.fallbacks['geometry']['focus_border_width'])
        normal_width = 0

        def on_focus_in(event):
            try:
                btn.configure(border_width=focus_width, border_color=focus_border)
            except Exception:
                pass

        def on_focus_out(event):
            try:
                btn.configure(border_width=normal_width)
            except Exception:
                pass

        try:
            btn.bind('<FocusIn>', on_focus_in)
            btn.bind('<FocusOut>', on_focus_out)
            if is_accept:
                btn.bind('<Return>', lambda e: self._on_accept())
            else:
                btn.bind('<Return>', lambda e: self._on_cancel())
        except Exception:
            pass

    def _get_font(self, font_key):
        """Obtener fuente desde la configuración de fonts cargada."""
        try:
            font_data = self.fonts_data.get(font_key, {})
            # Prefer values from font_config.json, otherwise use centralized fallback
            fallback_font_tuple = self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')
            family = font_data.get('family') or fallback_font_tuple[0]
            size = font_data.get('size') or fallback_font_tuple[1]
            weight = font_data.get('weight', 'normal')
            if weight and weight != 'normal':
                return (family, size, weight)
            return (family, size)
        except Exception:
            # Si falla, intentar obtener del fallback o usar default mínimo
            try:
                # Devolver la entrada desde FALLBACKS; asumimos que existe
                return self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')
            except Exception:
                return self.fallbacks.get('fonts', {}).get(font_key) or self.fallbacks.get('fonts', {}).get('dialog_message')

    def get_input(self):
        """Esperar a que el diálogo se cierre y devolver el resultado.

        Usa wait_window para bloquear hasta que el usuario cierre.
        """
        self.wait_window()
        return self.result


def show_input_dialog(parent, titulo, mensaje, tipo='success', valor_defecto='', callback=None, password=False):
    """Mostrar diálogo de entrada y devolver valor ingresado o None si canceló.

    Args:
        password: si True, el campo será enmascarado (show='*').
    """
    dialog = CustomInputDialog(parent, tipo=tipo, titulo=titulo, mensaje=mensaje, valor_defecto=valor_defecto, callback=callback, password=password)
    return dialog.get_input()


def show_password_dialog(parent, titulo="Contraseña", mensaje="Introduce tu contraseña:"):
    """Mostrar diálogo de input enmascarado para password.

    Returns:
        str o None: Password ingresado o None si canceló
    """
    return show_input_dialog(parent, titulo=titulo, mensaje=mensaje, tipo="info", password=True)


def show_text_viewer(parent, titulo, texto, width=600, height=800, callback=None):
    """Helper que muestra TextViewDialog del módulo `textview_dialog`.

    Esto mantiene compatibilidad con llamadas previas a `show_text_viewer`
    importando desde `kool_tpv.utils.custom_dialog`.
    """
    try:
        from kool_tpv.utils.textview_dialog import show_text_viewer as _show
        _show(parent, titulo, texto, width=width, height=height, callback=callback)
    except Exception:
        logging.exception('Error delegando a textview_dialog.show_text_viewer')
