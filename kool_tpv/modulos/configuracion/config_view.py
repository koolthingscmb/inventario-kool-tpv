import logging
import json
from pathlib import Path
import unicodedata
import customtkinter as ctk

from kool_tpv.utils.templates.base_module_view import BaseModuleView
from kool_tpv.utils.auth_service import AuthService
from kool_tpv.modulos.configuracion.impresion.textos_ui import TextosPlantillaUI
from kool_tpv.utils.factories.button_factory import ButtonFactory


class ConfigView(BaseModuleView):
    def __init__(self, parent, db, keyboard_manager=None):
        # Pre-initialize attributes so action methods can be registered before
        # the base class runs (BaseModuleView may probe with hasattr).
        # Set basic instance attributes
        # `parent`, `db` and `auth_service` were initialized before calling super().
        # No need to reassign them here.

        # action_map: register method names as attributes so BaseModuleView
        # can find them during its own initialization
        # Reuse `action_map` already registered before super().__init__()

        # action_map: register method names as attributes so BaseModuleView
        # can find them during its own initialization (buttons are created
        # in BaseModuleView.__init__ and probe via hasattr).
        action_map = {
            'open_config_general': getattr(self, 'show_general', None),
            'open_config_impresion': getattr(self, 'show_impresion', None),
            'open_config_usuario': getattr(self, 'show_usuario', None),
            'show_usuarios': getattr(self, 'show_usuarios', None),
            'open_config_fidelizacion': getattr(self, 'show_fidelizacion', None),
            'open_config_reset': getattr(self, 'show_reset', None),
            'show_diseno_ui': getattr(self, 'show_diseno_ui', None),
            'show_fidelizacion_general': getattr(self, 'show_fidelizacion_general', None),
            'show_fidelizacion_categorias': getattr(self, 'show_fidelizacion_categorias', None),
            'show_fidelizacion_tipos': getattr(self, 'show_fidelizacion_tipos', None),
            'show_fidelizacion_productos': getattr(self, 'show_fidelizacion_productos', None),
            'show_fidelizacion_niveles': getattr(self, 'show_fidelizacion_niveles', None),
        }

        # Registrar métodos como atributos para que BaseModuleView los encuentre
        for action_name, method in action_map.items():
            if method is not None:
                try:
                    setattr(self, action_name, method)
                except Exception:
                    logging.exception('Error registrando action %s', action_name)

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
            'GENERAL FIDE': None,
            'CATEGORÍAS FIDE': None,
            'TIPOS FIDE': None,
            'PRODUCTOS FIDE': None,
            'NIVELES FIDE': None,
            'RESET': None,
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

        
        # Aplicar estilos desde configs (colors, fonts, layout)
        try:
            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            # Cargar configs de estilos
            try:
                base_cfg = Path(__file__).resolve().parents[2]

                # Colors
                colors_cfg = {}
                cfile = base_cfg / 'config' / 'colors_config.json'
                if cfile.exists():
                    with cfile.open('r', encoding='utf-8') as fh:
                        colors_cfg = json.load(fh) or {}
                module_colors = colors_cfg.get('config', {}) if isinstance(colors_cfg, dict) else {}
                button_palette = (module_colors.get('buttons', {}) or {}).get('primary', {}) or {}
            except Exception:
                logging.exception('Error cargando colors_config para ConfigView')
                module_colors = {}
                button_palette = {}

            try:
                # Fonts
                font_cfg = {}
                ffile = base_cfg / 'config' / 'font_config.json'
                if ffile.exists():
                    with ffile.open('r', encoding='utf-8') as fh:
                        font_cfg = json.load(fh) or {}
                module_font_cfg = (font_cfg.get('modules', {}) or {}).get('config', {})
                app_nav_font = (font_cfg.get('app', {}) or {}).get('nav_button', {})
            except Exception:
                logging.exception('Error cargando font_config para ConfigView')
                module_font_cfg = {}
                app_nav_font = {}

            try:
                # Layout
                layout_cfg = {}
                lfile = base_cfg / 'config' / 'layout_config.json'
                if lfile.exists():
                    with lfile.open('r', encoding='utf-8') as fh:
                        layout_cfg = json.load(fh) or {}
                config_layout = (layout_cfg.get('modules', {}) or {}).get('config', {}) or {}
                sidebar_btn_layout = config_layout.get('sidebar_button', {}) or {}
            except Exception:
                logging.exception('Error cargando layout_config para ConfigView')
                sidebar_btn_layout = {}

            # Aplicar estilos a cada botón
            for b in buttons:
                lbl = (b.get('label') or b.get('text') or '')
                action = b.get('action')
                norm_lbl = _norm(lbl)

                for child in list(self._menu_frame.winfo_children()):
                    try:
                        txt = child.cget('text') if hasattr(child, 'cget') else None
                        if txt and _norm(txt) == norm_lbl:
                            # Rebind command
                            if action in action_map:
                                def _wrap(func):
                                    def _wrapped(*a, **k):
                                        try:
                                            return func(*a, **k)
                                        except Exception:
                                            logging.exception("Error al ejecutar acción %r:", getattr(func, '__name__', str(func)))
                                            raise
                                    return _wrapped

                                # Styling is delegated to ButtonFactory via style_key.
                                # Removed inline style construction and child.configure(**cfg).

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
                'GENERAL FIDE': self.show_fidelizacion_general,
                'CATEGORÍAS FIDE': self.show_fidelizacion_categorias,
                'TIPOS FIDE': self.show_fidelizacion_tipos,
                'PRODUCTOS FIDE': self.show_fidelizacion_productos,
                'NIVELES FIDE': self.show_fidelizacion_niveles,
                'RESET': self.show_reset,
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
                'show_plantillas_informes': self.show_plantillas_informes,
            }

            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            for b in buttons:
                text = b.get('text', '')
                action = b.get('action')

                btn = ButtonFactory.create_button(
                    parent=self._menu_frame,
                    text=text,
                    command=action_map.get(action),
                    style_key='module_config'
                )

                btn.pack(pady=8, padx=12, fill='x')

            # Actualizar breadcrumb
            try:
                self.actualizar_ruta('CONFIG / IMPRESIÓN', callbacks=self.breadcrumb_callbacks)
            except Exception:
                pass

            logging.info('Config: submenu IMPRESIÓN cargado')

        except Exception:
            logging.exception('Error en show_impresion')

    def show_usuario(self, _result=None):
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

            is_valid = False
            try:
                if self.auth_service:
                    res = self.auth_service.validate_admin_password(password)
                else:
                    res = (False, None)

                if isinstance(res, tuple):
                    is_valid = bool(res[0])
                else:
                    is_valid = bool(res)
            except Exception:
                is_valid = False

            if is_valid:
                logging.info('Config: abriendo USUARIO (autenticado)...')
                try:
                    self.show_usuarios()
                except Exception:
                    logging.exception('Error mostrando UI de usuarios')
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
        """Abrir submenu de Fidelización: cambia sidebar y muestra opciones."""
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

            is_valid = False
            try:
                if self.auth_service:
                    res = self.auth_service.validate_admin_password(password)
                else:
                    res = (False, None)

                if isinstance(res, tuple):
                    is_valid = bool(res[0])
                else:
                    is_valid = bool(res)
            except Exception:
                is_valid = False

            if not is_valid:
                show_warning(
                    parent,
                    "ACCESO DENEGADO",
                    "Contraseña incorrecta.\nInténtalo de nuevo.",
                    callback=self.show_fidelizacion
                )
                return

            # Autenticado: cargar submenu
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)

            submenu = cfg.get('config', {}).get('fidelizacion_submenu', {})
            buttons = submenu.get('buttons', [])

            # Limpiar sidebar actual
            for child in list(self._menu_frame.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass

            # Recrear botones del submenu
            action_map = {
                'show_fidelizacion_general': self.show_fidelizacion_general,
                'show_fidelizacion_categorias': self.show_fidelizacion_categorias,
                'show_fidelizacion_tipos': self.show_fidelizacion_tipos,
                'show_fidelizacion_productos': self.show_fidelizacion_productos,
                'show_fidelizacion_niveles': self.show_fidelizacion_niveles,
            }

            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            for b in buttons:
                text = b.get('text', '')
                action = b.get('action')

                btn = ButtonFactory.create_button(
                    parent=self._menu_frame,
                    text=text,
                    command=action_map.get(action),
                    style_key='module_config'
                )

                btn.pack(pady=8, padx=12, fill='x')

            # Actualizar breadcrumb
            try:
                self.actualizar_ruta('CONFIG / FIDELIZACIÓN', callbacks=self.breadcrumb_callbacks)
            except Exception:
                pass

            logging.info('Config: submenu FIDELIZACIÓN cargado')

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

    def show_usuarios(self):
        """Mostrar gestión de usuarios (clon de ProveedoresUI)."""
        try:
            from kool_tpv.modulos.configuracion.usuarios.usuarios_ui import UsuariosUI
            try:
                ui = UsuariosUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / USUARIOS', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo USUARIOS...')
            except Exception:
                logging.exception('Error instanciando UsuariosUI')
        except Exception:
            logging.exception('Error en show_usuarios')

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
        """Mostrar configuración de plantilla PDF de albaranes."""
        try:
            from kool_tpv.modulos.configuracion.impresion.plantillas_albaran_ui import PlantillasAlbaranUI
            ui = PlantillasAlbaranUI(self.central_area, db=self.db, module_name='config')
            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('CONFIG / IMPRESIÓN / PLANTILLAS', callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info('Config: abriendo PLANTILLAS...')
        except Exception:
            logging.exception('Error en show_plantillas')

    def show_plantillas_informes(self):
        """Mostrar configuración de plantilla PDF de informes."""
        try:
            from kool_tpv.modulos.configuracion.impresion.plantillas_informes_ui import PlantillasInformesUI
            ui = PlantillasInformesUI(self.central_area, db=self.db, module_name='config')
            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('CONFIG / IMPRESIÓN / INFORMES', callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info('Config: abriendo PLANTILLAS INFORMES...')
        except Exception:
            logging.exception('Error en show_plantillas_informes')

    def show_diseno_ui(self):
        """Abrir el panel de configuración UI (ConfigTabView)."""
        try:
            from kool_tpv.modulos.config.ui.config_tab_view import ConfigTabView
            from kool_tpv.modulos.config.ui.services.ui_config_service import UIConfigService

            service = UIConfigService()

            root = self.parent
            if hasattr(root, 'reload_configs'):
                for cfg_name in ['colors_config', 'font_config', 'layout_config',
                                 'buttons_config', 'notificaciones_config', 'ui_dialogs']:
                    service.registrar_observer(cfg_name, lambda data, name=cfg_name: root.reload_configs(name))

            ui = ConfigTabView(self.central_area, service)
            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('CONFIG / DISEÑO UI', callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info('Config: abriendo DISEÑO UI...')
        except Exception:
            logging.exception('Error en show_diseno_ui')

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
                'show_usuarios': self.show_usuarios,
                'open_config_fidelizacion': self.show_fidelizacion,
                'show_diseno_ui': self.show_diseno_ui,
            }

            for b in buttons:
                text = b.get('text', '')
                action = b.get('action')

                btn = ButtonFactory.create_button(
                    parent=self._menu_frame,
                    text=text,
                    command=action_map.get(action),
                    style_key='module_config'
                )

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

    def show_fidelizacion_general(self):
        """Mostrar configuración de % general de fidelización."""
        try:
            from kool_tpv.modulos.configuracion.fidelizacion.fidelizacion_general_ui import FidelizacionGeneralUI
            try:
                ui = FidelizacionGeneralUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / FIDELIZACIÓN / GENERAL', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo FIDELIZACIÓN GENERAL...')
            except Exception:
                logging.exception('Error instanciando FidelizacionGeneralUI')
        except Exception:
            logging.exception('Error en show_fidelizacion_general')

    def show_fidelizacion_categorias(self):
        """Mostrar configuración de % por categorías."""
        try:
            from kool_tpv.modulos.configuracion.fidelizacion.fidelizacion_categorias_ui import FidelizacionCategoriasUI
            try:
                ui = FidelizacionCategoriasUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / FIDELIZACIÓN / CATEGORÍAS', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo FIDELIZACIÓN CATEGORÍAS...')
            except Exception:
                logging.exception('Error instanciando FidelizacionCategoriasUI')
        except Exception:
            logging.exception('Error en show_fidelizacion_categorias')

    def show_fidelizacion_tipos(self):
        """Mostrar configuración de % por tipos."""
        try:
            from kool_tpv.modulos.configuracion.fidelizacion.fidelizacion_tipos_ui import FidelizacionTiposUI
            try:
                ui = FidelizacionTiposUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / FIDELIZACIÓN / TIPOS', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo FIDELIZACIÓN TIPOS...')
            except Exception:
                logging.exception('Error instanciando FidelizacionTiposUI')
        except Exception:
            logging.exception('Error en show_fidelizacion_tipos')

    def show_fidelizacion_productos(self):
        """Mostrar configuración de puntos por productos."""
        try:
            from kool_tpv.modulos.configuracion.fidelizacion.fidelizacion_productos_ui import FidelizacionProductosUI
            try:
                ui = FidelizacionProductosUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / FIDELIZACIÓN / PRODUCTOS', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo FIDELIZACIÓN PRODUCTOS...')
            except Exception:
                logging.exception('Error instanciando FidelizacionProductosUI')
        except Exception:
            logging.exception('Error en show_fidelizacion_productos')

    def show_fidelizacion_niveles(self):
        """Mostrar gestión de niveles de fidelización."""
        try:
            from kool_tpv.modulos.configuracion.fidelizacion.fidelizacion_niveles_ui import FidelizacionNivelesUI
            try:
                ui = FidelizacionNivelesUI(self.central_area, db=self.db, module_name='config', keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / FIDELIZACIÓN / NIVELES', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo FIDELIZACIÓN NIVELES...')
            except Exception:
                logging.exception('Error instanciando FidelizacionNivelesUI')
        except Exception:
            logging.exception('Error en show_fidelizacion_niveles')

    def show_reset(self):
        """Mostrar herramienta de reset (protegido por password admin)."""
        try:
            parent = self._get_dialog_parent()
            from kool_tpv.utils.custom_dialog import show_password_dialog, show_warning

            password = show_password_dialog(
                parent,
                titulo="Autenticación Admin",
                mensaje="⚠️ HERRAMIENTA DE DESARROLLO\nIntroduce contraseña de administrador:"
            )

            if password is None or password == "":
                return

            is_valid = False
            try:
                if self.auth_service:
                    res = self.auth_service.validate_admin_password(password)
                else:
                    res = (False, None)

                if isinstance(res, tuple):
                    is_valid = bool(res[0])
                else:
                    is_valid = bool(res)
            except Exception:
                is_valid = False

            if not is_valid:
                show_warning(
                    parent,
                    "ACCESO DENEGADO",
                    "Contraseña incorrecta.\nInténtalo de nuevo.",
                    callback=self.show_reset
                )
                return

            # Autenticado: mostrar UI de reset
            from kool_tpv.modulos.configuracion.reset_ui import ResetUI
            try:
                ui = ResetUI(self.central_area, db=self.db, module_name='config')
                if self.set_central_content(ui):
                    try:
                        self.actualizar_ruta('CONFIG / RESET', callbacks=self.breadcrumb_callbacks)
                    except Exception:
                        pass
                    logging.info('Config: abriendo RESET (autenticado)...')
            except Exception:
                logging.exception('Error instanciando ResetUI')

        except Exception:
            logging.exception('Error en show_reset')
