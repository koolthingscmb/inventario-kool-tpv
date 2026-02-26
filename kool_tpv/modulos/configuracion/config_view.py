import logging
import json
from pathlib import Path
import unicodedata
import customtkinter as ctk

from kool_tpv.utils.templates.base_module_view import BaseModuleView
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.modulos.configuracion.impresion.textos_ui import TextosPlantillaUI


class ConfigView(BaseModuleView):
    def __init__(self, parent, db, keyboard_manager=None):
        # Initialize base template with module key 'config'
        super().__init__(parent, config_section='config')
        try:
            self.keyboard_mgr = keyboard_manager
        except Exception:
            self.keyboard_mgr = None
        try:
            self._module_key = 'config'
            self.module_name = 'config'
        except Exception:
            pass
        # Mapeo breadcrumb callbacks para navegación clickeable
        self.breadcrumb_callbacks = {
            'CONFIG': None,  # se asigna después de los handlers
            'IMPRESIÓN': None,
            'GENERAL': None,
            'USUARIO': None,
            'FIDELIZACIÓN': None,
            'IMPRESORA': None,
            'TEXTOS TICKETS': None,
            'PLANTILLAS': None,
        }

        try:
            # Inicializar breadcrumb (los callbacks se actualizarán tras crear handlers)
            try:
                self.actualizar_ruta('CONFIG', callbacks=self.breadcrumb_callbacks)
            except Exception:
                pass
        except Exception:
            pass
        self.parent = parent
        self.db = db
        try:
            self.auth_service = AuthService(db)
        except Exception:
            self.auth_service = None

        # Load menu buttons for this module and rebind to local handlers
        try:
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)
            menu = cfg.get('config', {}) if isinstance(cfg, dict) else {}
            buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
        except Exception:
            logging.exception('Error leyendo buttons_menu.json en ConfigView')
            buttons = []

        action_map = {
            'open_config_general': self.show_general,
            'open_config_impresion': self.show_impresion,
            'open_config_usuario': self.show_usuario,
            'open_config_fidelizacion': self.show_fidelizacion,
        }

        try:
            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            for b in buttons:
                lbl = (b.get('label') or b.get('text') or '')
                action = b.get('action')
                norm_lbl = _norm(lbl)
                for child in list(self._menu_frame.winfo_children()):
                    try:
                        txt = child.cget('text') if hasattr(child, 'cget') else None
                        if txt and _norm(txt) == norm_lbl:
                            if action in action_map:
                                def _wrap(func):
                                    def _wrapped(*a, **k):
                                        try:
                                            return func(*a, **k)
                                        except Exception:
                                            logging.exception("Error al ejecutar acción %r:", getattr(func, '__name__', str(func)))
                                            raise
                                    return _wrapped
                                try:
                                    child.configure(command=_wrap(action_map[action]))
                                except Exception:
                                    logging.exception("Failed configuring command for %r", lbl)
                            else:
                                logging.warning("  Action %r not found in action_map", action)
                            break
                    except Exception:
                        logging.exception("Error inspeccionando child en ConfigView")
        except Exception:
            logging.exception('Error enlazando botones en ConfigView')

        # Completar mapping de callbacks para breadcrumb (ahora que handlers existen)
        try:
            self.breadcrumb_callbacks.update({
                'CONFIG': self.show_config_root,
                'IMPRESIÓN': self.show_impresion,
                'GENERAL': self.show_general,
                'USUARIO': self.show_usuario,
                'FIDELIZACIÓN': self.show_fidelizacion,
                'IMPRESORA': self.show_impresora_config,
                'TEXTOS TICKETS': self.show_textos_tickets,
                'PLANTILLAS': self.show_plantillas,
            })
        except Exception:
            # No crítico: si falla, navegacion clickeable no disponible
            logging.exception('No se pudo inicializar breadcrumb_callbacks')

    def show_general(self):
        """Mostrar config general (sin protección password)."""
        try:
            from kool_tpv.modulos.configuracion.config_general_ui import ConfigGeneralUI

            try:
                general_ui = ConfigGeneralUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(general_ui):
                    try:
                            self.actualizar_ruta('CONFIG / GENERAL', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo GENERAL...')
            except Exception:
                logging.exception('Error instanciando ConfigGeneralUI en show_general')
        except Exception:
            logging.exception('Error en show_general')

    def show_impresion(self):
        """Abrir submenu de Impresión: cambia sidebar y muestra opciones."""
        try:
            # Cargar submenu buttons desde JSON
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)

            submenu = cfg.get('config', {}).get('impresion_submenu', {})
            buttons = submenu.get('buttons', [])

            # Limpiar sidebar actual
            for child in list(self._menu_frame.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

            # Recrear botones del submenu
            action_map = {
                'show_impresora_config': self.show_impresora_config,
                'show_textos_tickets': self.show_textos_tickets,
                'show_plantillas': self.show_plantillas,
            }

            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            for b in buttons:
                text = b.get('text', '')
                fg_color = b.get('fg_color', '#000000')
                hover_color = b.get('hover_color', '#8A3A3A')
                text_color = b.get('text_color', '#FF0000')
                border_color = b.get('border_color', '#FF0000')
                border_width = b.get('border_width', 4)
                action = b.get('action')

                btn = ctk.CTkButton(
                    self._menu_frame,
                    text=text,
                    fg_color=fg_color,
                    hover_color=hover_color,
                    text_color=text_color,
                    border_color=border_color,
                    border_width=border_width,
                    font=("Courier New", 26, "bold"),
                    width=200,
                    height=56,
                    corner_radius=8
                )

                if action in action_map:
                    btn.configure(command=action_map[action])

                btn.pack(pady=8, padx=12, fill='x')

            # Actualizar breadcrumb
            try:
                self.actualizar_ruta('CONFIG / IMPRESIÓN', callbacks=self.breadcrumb_callbacks)
            except Exception:
                pass

            logging.info('Config: submenu IMPRESIÓN cargado')

        except Exception:
            logging.exception('Error en show_impresion')

    def show_usuario(self):
        """Mostrar config de usuarios (protegido por password admin)."""
        try:
            parent = self._get_dialog_parent()

            from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning

            password = show_password_dialog(
                parent,
                titulo="Autenticación Admin",
                mensaje="Introduce contraseña de administrador:"
            )

            if password is None or password == "":
                return

            if self.auth_service and self.auth_service.validate_admin_password(password):
                logging.info('Config: abriendo USUARIO (autenticado)...')
                # TODO: implementar UI de gestión de usuarios
            else:
                show_warning(
                    parent,
                    "ACCESO DENEGADO",
                    "Contraseña incorrecta.\nInténtalo de nuevo.",
                    callback=self.show_usuario
                )

        except Exception:
            logging.exception('Error en show_usuario')

    def show_fidelizacion(self):
        """Mostrar config de fidelización (protegido por password admin)."""
        try:
            parent = self._get_dialog_parent()

            from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning

            password = show_password_dialog(
                parent,
                titulo="Autenticación Admin",
                mensaje="Introduce contraseña de administrador:"
            )

            if password is None or password == "":
                return

            if self.auth_service and self.auth_service.validate_admin_password(password):
                logging.info('Config: abriendo FIDELIZACIÓN (autenticado)...')
                # TODO: implementar UI de gestión de fidelización
            else:
                show_warning(
                    parent,
                    "ACCESO DENEGADO",
                    "Contraseña incorrecta.\nInténtalo de nuevo.",
                    callback=self.show_fidelizacion
                )

        except Exception:
            logging.exception('Error en show_fidelizacion')

    def _get_dialog_parent(self):
        """Obtener ventana padre correcta para diálogos.

        Returns:
            Widget padre apropiado
        """
        try:
            return self.parent.winfo_toplevel()
        except Exception:
            try:
                return self.parent
            except Exception:
                return self

    def show_impresora_config(self):
        """Mostrar configuración de impresora."""
        try:
            from kool_tpv.modulos.configuracion.impresion.impresora_ui import ImpresoraUI

            try:
                impresora_ui = ImpresoraUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(impresora_ui):
                    try:
                        self.actualizar_ruta('CONFIG / IMPRESIÓN / IMPRESORA', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo IMPRESORA...')
            except Exception:
                logging.exception('Error instanciando ImpresoraUI')
        except Exception:
            logging.exception('Error en show_impresora_config')

    def show_textos_tickets(self):
        """Mostrar configuración de textos de tickets (Plantilla)."""
        try:
            try:
                textos_ui = TextosPlantillaUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(textos_ui):
                    try:
                        self.actualizar_ruta('CONFIG / IMPRESIÓN / TEXTOS TICKETS', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo TEXTOS TICKETS (Plantilla)...')
            except Exception:
                logging.exception('Error instanciando TextosPlantillaUI')
        except Exception:
            logging.exception('Error en show_textos_tickets')

    def show_plantillas(self):
        """Placeholder para plantillas (a implementar después)."""
        try:
            logging.info('Config: PLANTILLAS - pendiente implementación')
            from kool_tpv.utils.custom_dialog import show_warning
            parent = self._get_dialog_parent()
            show_warning(parent, 'Plantillas', 'Funcionalidad en desarrollo')
        except Exception:
            logging.exception('Error en show_plantillas')

    def show_config_root(self):
        """Volver a vista raíz de Config (limpiar sidebar y central)."""
        try:
            # Recargar sidebar original de config
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)

            menu = cfg.get('config', {})
            buttons = menu.get('buttons', [])

            # Limpiar sidebar
            for child in list(self._menu_frame.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

            # Recrear botones originales
            action_map = {
                'open_config_general': self.show_general,
                'open_config_impresion': self.show_impresion,
                'open_config_usuario': self.show_usuario,
                'open_config_fidelizacion': self.show_fidelizacion,
            }

            for b in buttons:
                text = b.get('text', '')
                fg_color = b.get('fg_color', '#000000')
                hover_color = b.get('hover_color', '#8A3A3A')
                text_color = b.get('text_color', '#FF0000')
                border_color = b.get('border_color', '#FF0000')
                border_width = b.get('border_width', 4)
                action = b.get('action')

                btn = ctk.CTkButton(
                    self._menu_frame,
                    text=text,
                    fg_color=fg_color,
                    hover_color=hover_color,
                    text_color=text_color,
                    border_color=border_color,
                    border_width=border_width,
                    font=("Courier New", 26, "bold"),
                    width=200,
                    height=56,
                    corner_radius=8
                )

                if action in action_map:
                    btn.configure(command=action_map[action])

                btn.pack(pady=8, padx=12, fill='x')

            # Limpiar área central
            for child in list(self.central_area.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

            # Actualizar breadcrumb
            try:
                self.actualizar_ruta('CONFIG', callbacks=self.breadcrumb_callbacks)
            except Exception:
                logging.exception('Error actualizando ruta en show_config_root')

        except Exception:
            logging.exception('Error en show_config_root')
