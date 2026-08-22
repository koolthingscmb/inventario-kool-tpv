"""Almacen module orchestrator (BaseModuleView pattern).

Provee una vista base que integra en la navegación principal del TPV.
La implementación es mínima: registra menú, provee `open` y `close`, y expone
el servicio maestro para las vistas UI.
"""
from typing import Optional
import logging
import json
from pathlib import Path

import unicodedata

import customtkinter as ctk
import tkinter as tk

from kool_tpv.modulos.almacen.services.maestro_service import MaestroService
from kool_tpv.utils.templates.base_module_view import BaseModuleView


class AlmacenView(BaseModuleView):
    """AlmacenView usando la plantilla `BaseModuleView`.

    Reusa la estética del sidebar y enlaza las acciones definidas en
    `buttons_menu.json` a métodos `show_*` simples que por ahora solo loguean.
    """

    def __init__(self, parent, db, keyboard_manager=None):
        # Initialize base template with module key 'almacen'
        super().__init__(parent, config_section='almacen')
        # Guardar referencia al KeyboardManager (opcional)
        try:
            self.keyboard_mgr = keyboard_manager
        except Exception:
            self.keyboard_mgr = None
        # Asegurar clave de módulo para carga de paleta
        try:
            # store lowercase key for config lookup and keep display name
            self._module_key = 'almacen'
            self.module_name = 'almacen'
        except Exception:
            pass
        # update breadcrumb to module on entry
        try:
            self.actualizar_ruta('ALMACEN')
        except Exception:
            pass
        self.parent = parent
        self.db = db
        self.service = MaestroService(db)

        # Rebind menu buttons to local handlers based on buttons_menu.json
        try:
            base = Path(__file__).resolve().parents[2]
            cfg_file = base / 'config' / 'buttons_menu.json'
            cfg = {}
            if cfg_file.exists():
                with cfg_file.open('r', encoding='utf-8') as fh:
                    cfg = json.load(fh)
            menu = cfg.get('almacen', {}) if isinstance(cfg, dict) else {}
            buttons = menu.get('buttons', []) if isinstance(menu, dict) else []
        except Exception:
            logging.exception('Error leyendo buttons_menu.json en AlmacenView')
            buttons = []

        # Map action names to methods
        action_map = {
            'show_crear': self.show_crear,
            'show_busqueda': self.show_busqueda,
            'show_albaranes': self.show_albaranes,
            'show_tipos': self.show_tipos,
            'show_categorias': self.show_categorias,
            'show_proveedores': self.show_proveedores,
            'show_entrada_manual': self.show_entrada_manual,
            'show_consultar': self.show_consultar,
            'show_menus': self.show_menus,
        }

        # Iterate over configured buttons and rebind matching buttons in the UI
        try:
            def _norm(s: str) -> str:
                try:
                    return ''.join(ch for ch in unicodedata.normalize("NFKD", (s or '')).upper() if not unicodedata.combining(ch)).strip()
                except Exception:
                    return (s or '').upper().strip()

            # Load visual/font/layout configs for this module
            try:
                base_cfg = Path(__file__).resolve().parents[2]
                # colors
                colors_cfg = {}
                cfile = base_cfg / 'config' / 'colors_config.json'
                if cfile.exists():
                    with cfile.open('r', encoding='utf-8') as fh:
                        colors_cfg = json.load(fh) or {}
                module_colors = colors_cfg.get('almacen', {}) if isinstance(colors_cfg, dict) else {}
                button_palette = (module_colors.get('buttons', {}) or {}).get('primary', {}) or {}
            except Exception:
                logging.exception('Error cargando colors_config para AlmacenView')
                module_colors = {}
                button_palette = {}

            try:
                # fonts
                font_cfg = {}
                ffile = base_cfg / 'config' / 'font_config.json'
                if ffile.exists():
                    with ffile.open('r', encoding='utf-8') as fh:
                        font_cfg = json.load(fh) or {}
                module_font_cfg = (font_cfg.get('modules', {}) or {}).get('almacen', {})
                # prefer module button/font definitions, else app.nav_button
                app_nav_font = (font_cfg.get('app', {}) or {}).get('nav_button', {})
            except Exception:
                logging.exception('Error cargando font_config para AlmacenView')
                module_font_cfg = {}
                app_nav_font = {}

            try:
                # layout sizes
                layout_cfg = {}
                lfile = base_cfg / 'config' / 'layout_config.json'
                if lfile.exists():
                    with lfile.open('r', encoding='utf-8') as fh:
                        layout_cfg = json.load(fh) or {}
                almacen_layout = (layout_cfg.get('modules', {}) or {}).get('almacen', {}) or {}
                sidebar_btn_layout = almacen_layout.get('sidebar_button', {}) or {}
            except Exception:
                logging.exception('Error cargando layout_config para AlmacenView')
                sidebar_btn_layout = {}

            for b in buttons:
                lbl = (b.get('label') or b.get('text') or '')
                action = b.get('action')
                norm_lbl = _norm(lbl)
                # find child button in menu_frame with same text
                for child in list(self._menu_frame.winfo_children()):
                    try:
                        txt = child.cget('text') if hasattr(child, 'cget') else None
                        if txt and _norm(txt) == norm_lbl:
                            # bind the action if exists
                            if action in action_map:
                                # wrap to capture exceptions when executing the bound action
                                def _wrap(func):
                                    def _wrapped(*a, **k):
                                        try:
                                            return func(*a, **k)
                                        except Exception:
                                            logging.exception("Error al ejecutar acción %r:", getattr(func, '__name__', str(func)))
                                            raise
                                    return _wrapped
                                # Styling is delegated to ButtonFactory via style_key.
                                # Previously the view attempted to construct a visual
                                # `cfg` dict and call `child.configure(**cfg)`. That
                                # logic has been removed so appearance is controlled
                                # centrally by the factory/styles config.

                                try:
                                    child.configure(command=_wrap(action_map[action]))
                                except Exception:
                                    logging.exception("Failed configuring command for %r", lbl)
                            else:
                                logging.warning("  Action %r not found in action_map", action)
                            break
                    except Exception:
                        logging.exception("Error inspeccionando child en AlmacenView")
        except Exception:
            logging.exception('Error enlazando botones en AlmacenView')

        # Stack de navegación: lista de callables para volver hacia atrás
        self._nav_stack = []

        # Memoria para mantener contexto al navegar
        self._last_proveedor_id = None

        # Estado de búsqueda para restaurar al volver de show_crear
        self._busqueda_termino = None
        self._busqueda_filtros = None  # (cat_id, tipo_id, estados)

        self.breadcrumb_callbacks = {
            'ALMACÉN': self.show_albaranes,
            'ALBARANES': self.show_albaranes,
            'BUSQUEDA': self.show_busqueda,
            'BÚSQUEDA': self.show_busqueda,
            'TIPOS': self.show_tipos,
            'CATEGORIAS': self.show_categorias,
            'CATEGORÍAS': self.show_categorias,
            'PROVEEDORES': self.show_proveedores,
            'CONSULTAR': self.show_consultar,
            'ENTRADA MANUAL': self.show_entrada_manual,
            'SALIDA MANUAL': self.show_salida_manual,
            'DEVOLUCIÓN': self.show_devolucion,
            'MENUS': self.show_menus,
            'MENÚS': self.show_menus,
        }

    def _on_power(self):
        """Gestionar botón Power con stack de navegación.

        Returns:
            True si gestionó la acción (navegó hacia atrás), False si debe cerrarse el módulo.
        """
        try:
            # 1. Verificar cambios sin guardar
            if not self._check_unsaved_changes():
                return True  # Usuario canceló, NO cerrar nada

            # 2. Si hay vistas en el stack, navegar hacia atrás
            if self._nav_stack:
                previous_view = self._nav_stack.pop()
                if callable(previous_view):
                    previous_view()
                    return True
                else:
                    self._nav_stack.clear()

            # 3. Stack vacío: ¿hay contenido en central_area?
            if self.central_area.winfo_children():
                children = self.central_area.winfo_children()
                if children:
                    current_widget = children[0]
                    # El widget empaquetado puede ser un container/frame;
                    # el _ui_owner apunta a la instancia UI real (ej: BusquedaUI)
                    ui_owner = getattr(current_widget, '_ui_owner', current_widget)
                    if hasattr(ui_owner, 'search_var'):
                        try:
                            termino = (ui_owner.search_var.get() or '').strip()
                            if termino:
                                # BusquedaUI con búsqueda activa → recargar vacía
                                self._busqueda_termino = None
                                self._busqueda_filtros = None
                                self.show_busqueda()
                                return True
                            else:
                                # BusquedaUI sin búsqueda → salir del módulo
                                return False
                        except Exception:
                            pass

                # Otras vistas: destruir y volver al raíz
                for widget in self.central_area.winfo_children():
                    widget.destroy()
                self.actualizar_ruta('ALMACÉN')
                return True

            # 4. Central vacío → permitir que main.py cierre el módulo
            return False
        except Exception:
            logging.exception('Error en _on_power de AlmacenView')
            return False
    
    def show_crear(self, producto_id: int = None):
        """Instancia y muestra la UI de creación/edición en la zona central."""
        try:
            from .ui.Productos.crear_producto_ui import CrearProductoUI

            # Push estado de búsqueda actual al stack para restaurar al volver
            if self._busqueda_termino is not None:
                termino = self._busqueda_termino
                filtros = self._busqueda_filtros
                self._nav_stack.append(lambda t=termino, f=filtros: self._show_busqueda_with_state(t, f))

            try:
                crear_ui = CrearProductoUI(self.central_area, db=self.db, producto_id=producto_id, module_name='almacen')
                widget = crear_ui.get_widget() if hasattr(crear_ui, 'get_widget') else crear_ui
                if self.set_central_content(widget):
                    self.actualizar_ruta('ALMACEN / CREAR_PRODUCTO', callbacks=self.breadcrumb_callbacks)

                if producto_id is not None:
                    try:
                        from .ui.Productos.cargar_producto import CargarProductoUI
                        loader = CargarProductoUI(self.central_area, db=self.db)
                        applied = loader.apply_to_ui(producto_id, crear_ui)
                        if not applied:
                            logging.warning('CrearProductoUI: no se aplicaron datos para producto_id=%s', producto_id)
                    except Exception:
                        logging.exception('Error aplicando datos de producto a CrearProductoUI')
            except Exception:
                logging.exception('No fue posible instanciar/mostrar CrearProductoUI en show_crear')

            logging.info('Abriendo crear...')
        except Exception:
            logging.exception('Error abriendo crear en AlmacenView')

    def _show_busqueda_with_state(self, termino, filtros):
        """Mostrar BusquedaUI restaurando un estado de búsqueda guardado."""
        self._busqueda_termino = termino
        self._busqueda_filtros = filtros
        self.show_busqueda()

    def show_busqueda(self):
        """Mostrar UI de búsqueda. Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            from .ui.busqueda_ui import BusquedaUI
            try:
                kwargs = {}
                if self._busqueda_termino is not None:
                    kwargs['termino_inicial'] = self._busqueda_termino
                    if self._busqueda_filtros:
                        kwargs['cat_id_inicial'] = self._busqueda_filtros[0]
                        kwargs['tipo_id_inicial'] = self._busqueda_filtros[1]
                        kwargs['estados_inicial'] = self._busqueda_filtros[2]
                    self._busqueda_termino = None
                    self._busqueda_filtros = None
                busq = BusquedaUI(self.central_area, db=self.db, owner=self, keyboard_manager=self.keyboard_mgr, **kwargs)
                if self.set_central_content(busq):
                    self.actualizar_ruta('ALMACEN / BUSQUEDA')
            except Exception:
                logging.exception('No fue posible instanciar BusquedaUI en show_busqueda')
            logging.info('Abriendo búsqueda...')
        except Exception:
            logging.exception('Error abriendo busqueda en AlmacenView')

    def show_albaranes(self):
        """Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            from .ui.albaranes_ui import AlbaranesUI
            try:
                albaranes_ui = AlbaranesUI(self.central_area, db=self.db, owner=self)
                if self.set_central_content(albaranes_ui):
                    self.actualizar_ruta('ALMACEN / ALBARANES')
                    logging.info('Abriendo albaranes...')
            except Exception:
                logging.exception('Error instanciando AlbaranesUI en show_albaranes')
        except Exception:
            logging.exception('Error abriendo albaranes en AlmacenView')

    def show_tipos(self):
        """Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            from .ui.tipos_ui import TiposUI
            try:
                tipos_ui = TiposUI(self.central_area, db=self.db, module_name='almacen')
                if self.set_central_content(tipos_ui):
                    self.actualizar_ruta('ALMACEN / TIPOS')
                    logging.info('Abriendo tipos...')
            except Exception:
                logging.exception('Error instanciando TiposUI en show_tipos')
        except Exception:
            logging.exception('Error abriendo tipos en AlmacenView')

    def show_categorias(self):
        """Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            from .ui.categorias_ui import CategoriasUI
            try:
                categorias_ui = CategoriasUI(self.central_area, db=self.db, module_name='almacen')
                if self.set_central_content(categorias_ui):
                    self.actualizar_ruta('ALMACEN / CATEGORIAS')
                    logging.info('Abriendo categorías...')
            except Exception:
                logging.exception('Error instanciando CategoriasUI en show_categorias')
        except Exception:
            logging.exception('Error abriendo categorias en AlmacenView')

    def show_proveedores(self, proveedor_id=None):
        """Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            if proveedor_id is None:
                proveedor_id = getattr(self, '_last_proveedor_id', None)

            from .ui.proveedores_ui import ProveedoresUI
            try:
                proveedores_ui = ProveedoresUI(self.central_area, db=self.db, owner=self, module_name='almacen')
                if self.set_central_content(proveedores_ui):
                    self.actualizar_ruta('ALMACEN / PROVEEDORES')

                    if proveedor_id:
                        try:
                            proveedores_ui.cargar_proveedor(proveedor_id)
                            self._last_proveedor_id = proveedor_id
                        except Exception:
                            logging.exception(f'Error cargando proveedor {proveedor_id} en show_proveedores')

                    logging.info('Abriendo proveedores...')
            except Exception:
                logging.exception('Error instanciando ProveedoresUI en show_proveedores')
        except Exception:
            logging.exception('Error abriendo proveedores en AlmacenView')

    def show_mapeo_csv(self, proveedor_id, proveedor_nombre=''):
        """Mostrar configurador de mapeos para un proveedor (pestaña CSV)."""
        self.show_configurar_mapeos(proveedor_id, proveedor_nombre, tab_inicial='CSV')

    def show_configurar_mapeos(self, proveedor_id, proveedor_nombre='', tab_inicial='CSV'):
        """Sub-vista de proveedores: push show_proveedores al stack."""
        self._nav_stack.append(lambda: self.show_proveedores())
        try:
            self._last_proveedor_id = proveedor_id

            from kool_tpv.modulos.produccion.ui.subvistas.proveedores.produccion_proveedores_configurador import ProduccionProveedoresConfigurador

            try:
                config_ui = ProduccionProveedoresConfigurador(
                    self.central_area,
                    db=self.db,
                    proveedor_id=proveedor_id,
                    proveedor_nombre=proveedor_nombre,
                    owner=self,
                    tab_inicial=tab_inicial,
                    module_name='almacen'
                )
                if self.set_central_content(config_ui):
                    self.actualizar_ruta(f'PROVEEDORES / CONFIGURAR MAPEOS ({tab_inicial})', callbacks=self.breadcrumb_callbacks)
                logging.info(f'Abriendo configurador de mapeos para proveedor {proveedor_id}...')
            except Exception:
                logging.exception('Error instanciando ProduccionProveedoresConfigurador en show_configurar_mapeos')
        except Exception:
            logging.exception('Error abriendo configurador de mapeos en AlmacenView')

    def show_entrada_manual(self, albaran_id=None):
        """Sub-vista de albaranes: push show_albaranes al stack."""
        self._nav_stack.append(lambda: self.show_albaranes())
        try:
            from .ui.albaranes.entrada_manual import EntradaManualUI
            try:
                entrada_ui = EntradaManualUI(self.central_area, db=self.db, module_name='almacen', albaran_id=albaran_id)
                if self.set_central_content(entrada_ui):
                    ruta = 'ALBARANES / EDITAR ALBARÁN' if albaran_id else 'ALBARANES / ENTRADA MANUAL'
                    self.actualizar_ruta(ruta, callbacks=self.breadcrumb_callbacks)
                    logging.info(f'Abriendo entrada manual (albaran_id={albaran_id})...')
            except Exception:
                logging.exception('Error instanciando EntradaManualUI en show_entrada_manual')
        except Exception:
            logging.exception('Error abriendo entrada manual en AlmacenView')
    
    def show_salida_manual(self):
        """Sub-vista de albaranes: push show_albaranes al stack."""
        self._nav_stack.append(lambda: self.show_albaranes())
        try:
            from .ui.albaranes.salida_manual import SalidaManualUI
            try:
                salida_ui = SalidaManualUI(self.central_area, db=self.db, keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(salida_ui):
                    self.actualizar_ruta('ALBARANES / SALIDA MANUAL', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo salida manual...')
            except Exception:
                logging.exception('Error instanciando SalidaManualUI en show_salida_manual')
        except Exception:
            logging.exception('Error abriendo salida manual en AlmacenView')

    def show_devolucion(self):
        """Sub-vista de albaranes: push show_albaranes al stack."""
        self._nav_stack.append(lambda: self.show_albaranes())
        try:
            from .ui.albaranes.devolucion import DevolucionUI

            try:
                devolucion_ui = DevolucionUI(self.central_area, db=self.db, keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(devolucion_ui):
                    self.actualizar_ruta('ALBARANES / DEVOLUCIÓN', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo devolución...')
            except Exception:
                logging.exception('Error instanciando DevolucionUI en show_devolucion')
        except Exception:
            logging.exception('Error abriendo devolución en AlmacenView')

    def show_importar_albaran(self, borrador=None):
        """Sub-vista de albaranes: push show_albaranes al stack."""
        self._nav_stack.append(lambda: self.show_albaranes())
        try:
            from .ui.albaranes.importar_albaran import ImportarAlbaranUI
            try:
                importar_ui = ImportarAlbaranUI(self.central_area, db=self.db, owner=self, module_name='almacen', keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(importar_ui):
                    self.actualizar_ruta('ALBARANES / IMPORTAR CSV', callbacks=self.breadcrumb_callbacks)
                    logging.info('Abriendo importar albarán...')
                    if borrador:
                        importar_ui.container.after(100, lambda: importar_ui.cargar_borrador(borrador))
            except Exception:
                logging.exception('Error instanciando ImportarAlbaranUI en show_importar_albaran')
        except Exception:
            logging.exception('Error abriendo importar albarán en AlmacenView')

    def show_consultar(self):
        """Sub-vista de albaranes: push show_albaranes al stack."""
        self._nav_stack.append(lambda: self.show_albaranes())
        try:
            from .ui.albaranes.consultar_albaran import ConsultarAlbaranUI
            try:
                consultar_ui = ConsultarAlbaranUI(self.central_area, db=self.db, owner=self, keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(consultar_ui):
                    self.actualizar_ruta('ALBARANES / CONSULTAR', callbacks=self.breadcrumb_callbacks)
                    logging.info('Abriendo consultar albaranes...')
            except Exception:
                logging.exception('Error instanciando ConsultarAlbaranUI en show_consultar')
        except Exception:
            logging.exception('Error abriendo consultar en AlmacenView')
    
    def show_menus(self):
        """Vista top-level: limpia el stack."""
        self._nav_stack.clear()
        try:
            from .ui.Productos.menus_ui import MenusUI
            try:
                menus_ui = MenusUI(self.central_area, db=self.db, owner=self, keyboard_manager=self.keyboard_mgr)
                if self.set_central_content(menus_ui):
                    self.actualizar_ruta('ALMACEN / MENÚS')
                    logging.info('Abriendo gestión de menús...')
            except Exception:
                logging.exception('Error instanciando MenusUI en show_menus')
        except Exception:
            logging.exception('Error abriendo menus en AlmacenView')

    def attach_to_nav(self, nav_frame, button_config: dict):
        """Adjunta el botón del módulo al frame de navegación usando ButtonFactory."""
        try:
            from kool_tpv.utils.factories.button_factory import ButtonFactory

            btn = ButtonFactory.create_button(
                parent=nav_frame,
                text=button_config.get('text', 'ALMACÉN'),
                command=self.open,
                style_key='module_almacen',
                width=button_config.get('width'),
                height=button_config.get('height'),
                corner_radius=button_config.get('corner_radius')
            )
            btn.pack(side='left', padx=6)
            return btn
        except Exception:
            logging.exception('Error attach_to_nav AlmacenView')
            return None
