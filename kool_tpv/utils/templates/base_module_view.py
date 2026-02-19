"""BaseModuleView: plantilla base clonada de la barra lateral de `main.py`.

Provee una estructura homogénea para los módulos (sidebar + zona central)
para que los módulos como `almacen` reutilicen la misma estética.
"""
from pathlib import Path
import json
import logging
import re
import customtkinter as ctk
import tkinter as tk

from kool_tpv.utils.utils import SIDEBAR_WIDTH, COLOR_BG_TERMINAL, COLOR_BG_SIDEBAR, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.utils.widgets.clickable_breadcrumb import ClickableBreadcrumb


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
                action = b.get('action')
                # default command: log action (caller can rebind)
                cmd = (lambda name=action or lbl: logging.info(f'Menu action: {name}'))
                # Support BOTH styles: legacy (solid color) and new minimal (fg_color + border)
                btn_kwargs = {
                    'master': self._menu_frame,
                    'text': lbl.upper(),
                    'command': cmd,
                    'font': ("Roboto-SemiBold", 24),
                    'height': 56
                }
                # NEW minimal style with border
                if 'fg_color' in b:
                    btn_kwargs['fg_color'] = b.get('fg_color', '#000000')
                    btn_kwargs['border_color'] = b.get('border_color', '#FFFFFF')
                    btn_kwargs['border_width'] = b.get('border_width', 2)
                    btn_kwargs['text_color'] = b.get('text_color', '#FFFFFF')
                    btn_kwargs['hover_color'] = b.get('hover_color', b.get('border_color', '#FFFFFF'))
                else:
                    # LEGACY style: solid fill
                    btn_kwargs['fg_color'] = b.get('color', '#CCCCCC')
                    btn_kwargs['hover_color'] = b.get('hover_color', self.HOVER_COLOR)
                    btn_kwargs['text_color'] = 'black'
                    btn_kwargs['border_width'] = 0

                btn = ctk.CTkButton(**btn_kwargs)
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
                # Breadcrumb clickeable
                self.module_name = (config_section or 'MODULO').upper()
                self.breadcrumb = ClickableBreadcrumb(self.main_frame)
                self.breadcrumb.pack(anchor='nw', fill='x', padx=12, pady=(8, 6))

                # Inicializar con módulo base
                self.breadcrumb.update_parts([
                    ('SISTEMA_KOOL:', None),
                    (self.module_name, None)
                ])

            except Exception:
                logging.exception('Error creando breadcrumb en BaseModuleView')
            # Alias usado por módulos: central_area (below the ruta label)
            self.central_area = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BG_TERMINAL)
            self.central_area.pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error creando main_frame BaseModuleView')

        # Interceptar cierre de ventana desde X del sistema operativo
        try:
            top = parent.winfo_toplevel()
            if top:
                try:
                    # Vincular WM_DELETE_WINDOW a _on_power (verifica cambios)
                    top.protocol("WM_DELETE_WINDOW", self._on_power)
                    logging.info('Protocolo WM_DELETE_WINDOW vinculado a _on_power')
                except Exception:
                    logging.exception('Error vinculando WM_DELETE_WINDOW')
        except Exception:
            logging.exception('Error configurando protocolo cierre ventana')

    def set_central_content(self, content):
        """Replace the central area content with `content`.

        `content` can be:
          - an object with a `pack(**kwargs)` method (e.g., CrearProductoUI instance),
          - or an object exposing `get_widget()` that returns a widget/frame.

        The method clears previous children in `central_area` before packing the new content.
        """
        try:
            # Verificar cambios sin guardar ANTES de destruir UI actual
            if not self._check_unsaved_changes():
                return False
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
                    # Ensure widget exists before packing (it might have been destroyed)
                    exists = True
                    try:
                        if hasattr(widget, 'winfo_exists'):
                            exists = widget.winfo_exists()
                    except Exception:
                        exists = True
                    if not exists:
                        logging.warning('set_central_content: widget no existe, omitiendo pack')
                        return
                    widget.pack(fill='both', expand=True)

                    # Attach reference to the original UI instance if different
                    try:
                        if widget is not content:
                            try:
                                setattr(widget, '_ui_owner', content)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # AUTO-ACTUALIZAR BREADCRUMB para widgets empaquetados
                    try:
                        breadcrumb_name = self._extract_breadcrumb_name(content)
                        if breadcrumb_name:
                            self.actualizar_ruta(breadcrumb_name)
                    except Exception:
                        logging.exception('Error auto-actualizando breadcrumb')

                    return True
                except Exception:
                    pass

            # Otherwise, if content has pack, assume it will pack itself into the parent
            if hasattr(content, 'pack') and callable(getattr(content, 'pack')):
                try:
                    # Ensure the content was created with central_area as parent; call pack to show
                    content.pack(fill='both', expand=True)

                    # If we packed an instance (not a raw widget), attach owner ref
                    try:
                        setattr(content, '_ui_owner', content)
                    except Exception:
                        pass

                    # AUTO-ACTUALIZAR BREADCRUMB
                    try:
                        breadcrumb_name = self._extract_breadcrumb_name(content)
                        if breadcrumb_name:
                            self.actualizar_ruta(breadcrumb_name)
                    except Exception:
                        logging.exception('Error auto-actualizando breadcrumb')

                    return True
                except Exception:
                    logging.exception('Error al packear content en set_central_content')

            # AUTO-ACTUALIZAR BREADCRUMB incluso si pack falla
            try:
                breadcrumb_name = self._extract_breadcrumb_name(content)
                if breadcrumb_name:
                    self.actualizar_ruta(breadcrumb_name)
            except Exception:
                logging.exception('Error auto-actualizando breadcrumb')

            # Guardar referencia a UI actual
            try:
                self._current_ui = content
            except Exception:
                pass

            logging.info('set_central_content: content tipo no reconocido, intentando insert directo')
        except Exception:
            logging.exception('Error en set_central_content BaseModuleView')

        # Retornar True si llegamos aquí (navegación completada)
        return True

    # Placeholder handlers que las subclases pueden sobrescribir
    def _on_power(self):
        """Cerrar módulo/ventana verificando cambios sin guardar primero.

        Detecta automáticamente si es:
        - Ventana Toplevel separada → destruye ventana
        - Módulo integrado (Frame) → desempaqueta y restaura menú principal
        """
        try:
            # Verificar cambios sin guardar
            if not self._check_unsaved_changes():
                return False  # Usuario canceló

            # Detectar contexto: ¿Toplevel o Frame integrado?
            try:
                top = self.sidebar.winfo_toplevel()

                # Si parent es Toplevel → ventana separada
                try:
                    if isinstance(self.parent, ctk.CTkToplevel) or isinstance(self.parent, tk.Toplevel):
                        logging.info('Cerrando ventana Toplevel...')
                        try:
                            self.parent.destroy()
                        except Exception:
                            try:
                                top.destroy()
                            except Exception:
                                pass
                        return
                except Exception:
                    # Si customtkinter no expone CTkToplevel o falla isinstance, seguir
                    pass

                # Frame integrado → desempaquetar módulo
                logging.info('Cerrando módulo integrado (Frame)...')

                # Desempaquetar sidebar y main_frame
                try:
                    self.sidebar.pack_forget()
                except Exception:
                    pass

                try:
                    self.main_frame.pack_forget()
                except Exception:
                    pass

                # Restaurar nav_frame del parent si existe
                try:
                    if hasattr(self.parent, 'nav_frame'):
                        try:
                            self.parent.nav_frame.pack(side='left', fill='y')
                            logging.info('Menú principal restaurado')
                        except Exception:
                            logging.exception('Error restaurando nav_frame')
                except Exception:
                    logging.exception('Error comprobando/restaurando nav_frame')

            except Exception:
                logging.exception('Error detectando contexto en _on_power')
                return False

            return True

        except Exception:
            logging.exception('Error en _on_power')
            return False

    def actualizar_ruta(self, sub_seccion: str = None, callbacks: dict = None):
        """Actualiza el texto de la ruta/breadcrumb mostrado arriba del área central.

        Formato: SISTEMA_KOOL_TPV: / <MODULO> [ / <SUB_SECCION>]
        """
        try:
            base_module = (getattr(self, 'module_name', 'MODULO') or '').upper()

            # Construir lista de partes
            parts_data = [('SISTEMA_KOOL:', None), (base_module, None)]

            if sub_seccion:
                # Normalizar: eliminar módulo si está duplicado
                s = sub_seccion.upper()
                if s.startswith(base_module):
                    s = s[len(base_module):].lstrip(' /')

                # Separar por " / " y añadir cada parte
                if s:
                    subsecciones = [p.strip() for p in s.split('/') if p.strip()]
                    for subsec in subsecciones:
                        # Buscar callback si existe
                        callback = None
                        if callbacks and subsec in callbacks:
                            callback = callbacks[subsec]
                        parts_data.append((subsec, callback))

            # Actualizar widget breadcrumb
            if hasattr(self, 'breadcrumb') and self.breadcrumb is not None:
                try:
                    self.breadcrumb.update_parts(parts_data)
                except Exception:
                    logging.exception('Error actualizando breadcrumb widget')

        except Exception:
            logging.exception('Error actualizando ruta en BaseModuleView')

    def _extract_breadcrumb_name(self, content) -> str:
        """Extraer nombre legible de la UI para breadcrumb.

        Prioridad:
        1. Si content tiene atributo breadcrumb_name, usar ese
        2. Extraer de nombre de clase (ej: EntradaManualUI → ENTRADA MANUAL)
        3. Fallback: None (no actualizar breadcrumb)

        Args:
            content: Objeto UI (EntradaManualUI, CrearProductoUI, etc.)

        Returns:
            str: Nombre legible en mayúsculas o None
        """
        try:
            # Prioridad 1: atributo manual breadcrumb_name
            if hasattr(content, 'breadcrumb_name'):
                name = getattr(content, 'breadcrumb_name', '').strip()
                if name:
                    return name.upper()

            # Prioridad 2: extraer de nombre de clase
            class_name = content.__class__.__name__

            # Remover sufijos comunes
            for suffix in ['UI', 'View', 'Window', 'Frame']:
                if class_name.endswith(suffix):
                    class_name = class_name[:-len(suffix)]
                    break

            # Convertir CamelCase a palabras separadas
            # Insertar espacio antes de mayúsculas
            spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', class_name)
            # Insertar espacio antes de número
            spaced = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', spaced)

            # Limpiar y convertir a mayúsculas
            result = spaced.strip().upper()

            # Si el resultado es muy corto o vacío, retornar None
            if len(result) < 3:
                return None

            return result

        except Exception:
            logging.exception('Error extrayendo breadcrumb_name')
            return None

    def _check_unsaved_changes(self):
        """Verificar si la UI actual tiene cambios sin guardar.

        Busca en central_area una UI con método has_unsaved_changes().
        Si tiene cambios, muestra warning de confirmación.

        Returns:
            bool: True si puede continuar, False si usuario canceló
        """
        try:
            # Buscar UI actual en central_area
            for child in list(self.central_area.winfo_children()):
                # First check if the child has an attached UI owner
                owners = []
                try:
                    if hasattr(child, '_ui_owner'):
                        owners.append(getattr(child, '_ui_owner'))
                except Exception:
                    pass

                # Always include the widget itself as a fallback
                owners.append(child)

                for owner in owners:
                    try:
                        if hasattr(owner, 'has_unsaved_changes') and callable(owner.has_unsaved_changes):
                            try:
                                if owner.has_unsaved_changes():
                                    # Hay cambios sin guardar → mostrar warning
                                    from kool_tpv.utils.custom_dialog import show_warning
                                    result = show_warning(
                                        self.parent,
                                        "Cambios sin guardar",
                                        "Está procesando un albarán. Si sale perderá los cambios. ¿Continuar?",
                                        confirm=True
                                    )
                                    return result
                            except Exception:
                                logging.exception('Error comprobando has_unsaved_changes en owner')
                    except Exception:
                        logging.exception('Error verificando owner en _check_unsaved_changes')

            # No hay UI con cambios o no tiene el método
            return True

        except Exception:
            logging.exception('Error en _check_unsaved_changes')
            return True  # En caso de error, permitir continuar

    def _on_volver(self):
        # Subclasses should override this to implement back-navigation
        logging.info('VOLVER pressed (no action asignada)')
