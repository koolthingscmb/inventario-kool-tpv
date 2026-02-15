"""BaseModuleView: plantilla base clonada de la barra lateral de `main.py`.

Provee una estructura homogénea para los módulos (sidebar + zona central)
para que los módulos como `almacen` reutilicen la misma estética.
"""
from pathlib import Path
import json
import logging
import customtkinter as ctk
import tkinter as tk

from kool_tpv.utils.utils import SIDEBAR_WIDTH, COLOR_BG_TERMINAL, COLOR_BG_SIDEBAR, COLOR_MATRIX, FONT_TERMINAL


class BaseModuleView:
    """Plantilla base con sidebar y zona central.

    Uso mínimo:
        view = BaseModuleView(root)
        view.pack()  # si necesario
"""

    HOVER_COLOR = "#00A4DF"

    def __init__(self, parent, config_section: str = None):
        self.parent = parent
        # Sidebar (izquierda)
        self.sidebar = ctk.CTkFrame(parent, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=COLOR_BG_SIDEBAR)
        self.sidebar.pack(side="left", fill="y")
        try:
            self.sidebar.pack_propagate(False)
        except Exception:
            pass

        # Top area for power button and optional header
        try:
            from kool_tpv.utils.global_buttons import create_global_close_button
            self.power_button = create_global_close_button(self.sidebar, command=self._on_power)
            if self.power_button is not None:
                try:
                    self.power_button.pack(pady=(12, 20))
                except Exception:
                    pass
        except Exception:
            logging.exception('Error creando botón power en BaseModuleView')

        # Container for menu buttons
        self._menu_frame = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self._menu_frame.pack(side='top', fill='y', expand=False)

        # Load buttons from config file `buttons_menu.json` using provided section
        try:
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)
            section = (config_section or 'almacen')
            menu = cfg.get(section, {})
            buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
        except Exception:
            logging.exception('Error leyendo buttons_menu.json en BaseModuleView')
            buttons = []

        # Create menu buttons
        for b in buttons:
            try:
                lbl = b.get('label') or b.get('text') or 'BTN'
                color = b.get('color', '#CCCCCC')
                action = b.get('action')
                # default command: log action (caller can rebind)
                cmd = (lambda name=action or lbl: logging.info(f'Menu action: {name}'))
                btn = ctk.CTkButton(self._menu_frame, text=lbl.upper(), fg_color=color, hover_color=self.HOVER_COLOR, text_color='black', font=("Roboto-SemiBold", 24), command=cmd, height=56)
                btn.pack(pady=14, padx=20, fill='x')
            except Exception:
                logging.exception('Error creando boton menu BaseModuleView')

        # No 'VOLVER' button: the global power button will act as back inside modules.

        # Footer
        try:
            footer = ctk.CTkLabel(self.sidebar, text="KOOL TPV V1.0", text_color="white", font=("Roboto-Regular", 18))
            footer.pack(side='bottom', pady=10)
        except Exception:
            logging.exception('Error creando footer BaseModuleView')

        # Zona central (derecha)
        try:
            # main container uses terminal background to ensure flicker-free dark UI
            self.main_frame = ctk.CTkFrame(parent, fg_color=COLOR_BG_TERMINAL)
            self.main_frame.pack(side='right', fill='both', expand=True)
            # Add breadcrumb / ruta label at the top of central area (fixed)
            try:
                self.module_name = (config_section or 'MODULO').upper()
                self.lbl_ruta_sistema = ctk.CTkLabel(
                    self.main_frame,
                    text=f"SISTEMA_KOOL: / {self.module_name}",
                    font=FONT_TERMINAL,
                    text_color=COLOR_MATRIX,
                    anchor='w',
                    fg_color=COLOR_BG_TERMINAL,
                )
                self.lbl_ruta_sistema.pack(anchor='nw', fill='x', padx=12, pady=(8, 6))
            except Exception:
                logging.exception('Error creando lbl_ruta_sistema en BaseModuleView')
            # Alias usado por módulos: central_area (below the ruta label)
            self.central_area = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BG_TERMINAL)
            self.central_area.pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error creando main_frame BaseModuleView')

    def set_central_content(self, content):
        """Replace the central area content with `content`.

        `content` can be:
          - an object with a `pack(**kwargs)` method (e.g., CrearProductoUI instance),
          - or an object exposing `get_widget()` that returns a widget/frame.

        The method clears previous children in `central_area` before packing the new content.
        """
        try:
            # If content corresponds to an existing child, avoid destroying it
            candidate_widget = None
            try:
                if hasattr(content, 'get_widget') and callable(getattr(content, 'get_widget')):
                    candidate_widget = content.get_widget()
                elif hasattr(content, 'frame'):
                    candidate_widget = getattr(content, 'frame')
                elif hasattr(content, 'container'):
                    candidate_widget = getattr(content, 'container')
                else:
                    candidate_widget = content
            except Exception:
                candidate_widget = content

            # Clear existing children, but skip the candidate widget if it's already a child
            for child in list(self.central_area.winfo_children()):
                try:
                    if candidate_widget is not None and child is candidate_widget:
                        # skip destroying the widget we're about to insert
                        continue
                    child.destroy()
                except Exception:
                    try:
                        if candidate_widget is not None and child is candidate_widget:
                            continue
                        child.pack_forget()
                    except Exception:
                        pass

            # If content has get_widget(), use it
            widget = None
            if hasattr(content, 'get_widget') and callable(getattr(content, 'get_widget')):
                widget = content.get_widget()
            elif hasattr(content, 'frame'):
                widget = getattr(content, 'frame')
            elif hasattr(content, 'container'):
                widget = getattr(content, 'container')

            if widget is not None:
                try:
                    widget.pack(fill='both', expand=True)
                    return
                except Exception:
                    pass

            # Otherwise, if content has pack, assume it will pack itself into the parent
            if hasattr(content, 'pack') and callable(getattr(content, 'pack')):
                try:
                    # Ensure the content was created with central_area as parent; call pack to show
                    content.pack(fill='both', expand=True)
                    return
                except Exception:
                    logging.exception('Error al packear content en set_central_content')

            logging.info('set_central_content: content tipo no reconocido, intentando insert directo')
        except Exception:
            logging.exception('Error en set_central_content BaseModuleView')

    # Placeholder handlers que las subclases pueden sobrescribir
    def _on_power(self):
        try:
            # Default: close parent window if it's a Toplevel, otherwise do nothing
            top = self.sidebar.winfo_toplevel()
            try:
                top.destroy()
            except Exception:
                pass
        except Exception:
            pass

    def actualizar_ruta(self, sub_seccion: str = None):
        """Actualiza el texto de la ruta/breadcrumb mostrado arriba del área central.

        Formato: SISTEMA_KOOL_TPV: / <MODULO> [ / <SUB_SECCION>]
        """
        try:
            base = f"SISTEMA_KOOL: / {(getattr(self, 'module_name', 'MODULO') or '').upper()}"
            if sub_seccion:
                base = f"{base} / {sub_seccion.upper()}"
            if hasattr(self, 'lbl_ruta_sistema') and self.lbl_ruta_sistema is not None:
                try:
                    self.lbl_ruta_sistema.configure(text=base)
                except Exception:
                    try:
                        self.lbl_ruta_sistema['text'] = base
                    except Exception:
                        pass
        except Exception:
            logging.exception('Error actualizando ruta en BaseModuleView')

    def _on_volver(self):
        # Subclasses should override this to implement back-navigation
        logging.info('VOLVER pressed (no action asignada)')
