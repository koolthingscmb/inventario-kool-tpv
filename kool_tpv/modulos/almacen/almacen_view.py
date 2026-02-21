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

    def __init__(self, parent, db):
        # Initialize base template with module key 'almacen'
        super().__init__(parent, config_section='almacen')
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
            'show_detalle_albaran': self.show_detalle_albaran,
        }

        # Iterate over configured buttons and rebind matching buttons in the UI
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

        # Mapeo breadcrumb → callbacks para navegación clickeable
        # Memoria para mantener contexto al navegar
        self._last_proveedor_id = None

        self.breadcrumb_callbacks = {
            'ALMACÉN': self.show_albaranes, # Click en ALMACÉN vuelve a vista principal albaranes
            'ALBARANES': self.show_albaranes,
            'CONSULTAR': self.show_consultar,
            'ENTRADA MANUAL': self.show_entrada_manual,
            'SALIDA MANUAL': self.show_salida_manual,
            'DEVOLUCIÓN': self.show_devolucion,
            'PROVEEDORES': self.show_proveedores, # ← AÑADIDO para navegación clickeable
        }

    # Simple handlers that currently log actions — to be implemented
    def show_crear(self, producto_id: int = None):
        """Instancia y muestra la UI de creación en la zona central."""
        try:
            from .ui.Productos.crear_producto_ui import CrearProductoUI
            # Always instantiate a fresh UI to avoid using destroyed widgets
            try:
                crear_ui = CrearProductoUI(self.central_area, db=self.db, producto_id=producto_id, module_name='almacen')
                # Prefer passing the actual widget to set_central_content to avoid
                # ambiguous packing behavior if the instance exposes both
                # get_widget() and pack(). This reduces race conditions with
                # previously destroyed widgets.
                navigated = False
                try:
                    widget = crear_ui.get_widget() if hasattr(crear_ui, 'get_widget') else crear_ui
                    navigated = self.set_central_content(widget)
                except Exception:
                    # fallback: try passing the instance itself
                    logging.exception('Error obteniendo widget desde CrearProductoUI, intentando pasar la instancia')
                    try:
                        navigated = self.set_central_content(crear_ui)
                    except Exception:
                        logging.exception('Fallo al pasar la instancia CrearProductoUI a set_central_content')

                # Actualizar breadcrumb DESPUÉS de verificar cambios (solo si navegación exitosa)
                if navigated:
                    try:
                        self.actualizar_ruta('ALMACEN / CREAR_PRODUCTO')
                    except Exception:
                        pass

                # If a producto_id was provided, attempt to prefill the UI using the loader
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

    def show_busqueda(self):
        try:
            from .ui.busqueda_ui import BusquedaUI
            try:
                busq = BusquedaUI(self.central_area, db=self.db, owner=self)
                if self.set_central_content(busq):
                    try:
                        self.actualizar_ruta('ALMACEN / BUSQUEDA')
                    except Exception:
                        pass
            except Exception:
                logging.exception('No fue posible instanciar BusquedaUI en show_busqueda')
            logging.info('Abriendo búsqueda...')
        except Exception:
            logging.exception('Error abriendo busqueda en AlmacenView')

    def show_albaranes(self):
        try:
            from .ui.albaranes_ui import AlbaranesUI
            try:
                albaranes_ui = AlbaranesUI(self.central_area, db=self.db, owner=self)
                if self.set_central_content(albaranes_ui):
                    try:
                        self.actualizar_ruta('ALMACEN / ALBARANES')
                    except Exception:
                        pass
                    logging.info('Abriendo albaranes...')
            except Exception:
                logging.exception('Error instanciando AlbaranesUI en show_albaranes')
        except Exception:
            logging.exception('Error abriendo albaranes en AlmacenView')

    def show_tipos(self):
        try:
            from .ui.tipos_ui import TiposUI

            # Always create a fresh UI instance to avoid reusing destroyed widgets
            try:
                tipos_ui = TiposUI(self.central_area, db=self.db, module_name='almacen')
                if self.set_central_content(tipos_ui):
                    try:
                        self.actualizar_ruta('ALMACEN / TIPOS')
                    except Exception:
                        pass
                    logging.info('Abriendo tipos...')
            except Exception:
                logging.exception('Error instanciando TiposUI en show_tipos')
        except Exception:
            logging.exception('Error abriendo tipos en AlmacenView')

    def show_categorias(self):
        try:
            from .ui.categorias_ui import CategoriasUI
            try:
                categorias_ui = CategoriasUI(self.central_area, db=self.db, module_name='almacen')
                if self.set_central_content(categorias_ui):
                    try:
                        self.actualizar_ruta('ALMACEN / CATEGORIAS')
                    except Exception:
                        pass
                    logging.info('Abriendo categorías...')
            except Exception:
                logging.exception('Error instanciando CategoriasUI en show_categorias')
        except Exception:
            logging.exception('Error abriendo categorias en AlmacenView')

    def show_proveedores(self, proveedor_id=None):
        try:
            # Si no se pasa ID, usar el último recordado
            if proveedor_id is None:
                proveedor_id = getattr(self, '_last_proveedor_id', None)

            from .ui.proveedores_ui import ProveedoresUI
            try:
                proveedores_ui = ProveedoresUI(self.central_area, db=self.db, owner=self, module_name='almacen')
                if self.set_central_content(proveedores_ui):
                    try:
                        self.actualizar_ruta('ALMACEN / PROVEEDORES')
                    except Exception:
                        pass

                    # Cargar proveedor si hay ID
                    if proveedor_id:
                        try:
                            proveedores_ui.cargar_proveedor(proveedor_id)
                            # Actualizar memoria con el ID cargado
                            self._last_proveedor_id = proveedor_id
                        except Exception:
                            logging.exception(f'Error cargando proveedor {proveedor_id} en show_proveedores')

                    logging.info('Abriendo proveedores...')
            except Exception:
                logging.exception('Error instanciando ProveedoresUI en show_proveedores')
        except Exception:
            logging.exception('Error abriendo proveedores en AlmacenView')

    def show_mapeo_csv(self, proveedor_id, proveedor_nombre=''):
        """Mostrar UI de configuración de mapeo CSV para un proveedor.

        Args:
            proveedor_id: ID del proveedor
            proveedor_nombre: Nombre del proveedor (para mostrar en UI)
        """
        try:
            # Guardar en memoria para breadcrumb
            try:
                self._last_proveedor_id = proveedor_id
            except Exception:
                pass

            from .ui.mapeo_csv_ui import MapeoCsvUI

            try:
                mapeo_ui = MapeoCsvUI(
                    self.central_area,
                    db=self.db,
                    proveedor_id=proveedor_id,
                    proveedor_nombre=proveedor_nombre,
                    owner=self
                )
                if self.set_central_content(mapeo_ui):
                    self.actualizar_ruta('PROVEEDORES / MAPEO CSV', callbacks=self.breadcrumb_callbacks)
                logging.info(f'Abriendo mapeo CSV para proveedor {proveedor_id}...')
            except Exception:
                logging.exception('Error instanciando MapeoCsvUI en show_mapeo_csv')
        except Exception:
            logging.exception('Error abriendo mapeo CSV en AlmacenView')

    def show_entrada_manual(self):
        """Mostrar UI de entrada manual de albaranes."""
        try:
            from .ui.albaranes.entrada_manual import EntradaManualUI
            try:
                entrada_ui = EntradaManualUI(self.central_area, db=self.db, module_name='almacen')
                if self.set_central_content(entrada_ui):
                    self.actualizar_ruta('ALBARANES / ENTRADA MANUAL', callbacks=self.breadcrumb_callbacks)
                    logging.info('Abriendo entrada manual...')
            except Exception:
                logging.exception('Error instanciando EntradaManualUI en show_entrada_manual')
        except Exception:
            logging.exception('Error abriendo entrada manual en AlmacenView')
    
    def show_salida_manual(self):
        """Mostrar UI de salida manual de albaranes."""
        try:
            from .ui.albaranes.salida_manual import SalidaManualUI

            try:
                salida_ui = SalidaManualUI(self.central_area, db=self.db)
                if self.set_central_content(salida_ui):
                    self.actualizar_ruta('ALBARANES / SALIDA MANUAL', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo salida manual...')
            except Exception:
                logging.exception('Error instanciando SalidaManualUI en show_salida_manual')
        except Exception:
            logging.exception('Error abriendo salida manual en AlmacenView')

    def show_devolucion(self):
        """Mostrar UI de devolución de albaranes."""
        try:
            from .ui.albaranes.devolucion import DevolucionUI

            try:
                devolucion_ui = DevolucionUI(self.central_area, db=self.db)
                if self.set_central_content(devolucion_ui):
                    self.actualizar_ruta('ALBARANES / DEVOLUCIÓN', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo devolución...')
            except Exception:
                logging.exception('Error instanciando DevolucionUI en show_devolucion')
        except Exception:
            logging.exception('Error abriendo devolución en AlmacenView')
    
    def show_consultar(self):
        """Mostrar UI de consulta de albaranes con filtros."""
        try:
            from .ui.albaranes.consultar_albaran import ConsultarAlbaranUI
            try:
                consultar_ui = ConsultarAlbaranUI(self.central_area, db=self.db, owner=self)
                if self.set_central_content(consultar_ui):
                    self.actualizar_ruta('ALBARANES / CONSULTAR', callbacks=self.breadcrumb_callbacks)
                    logging.info('Abriendo consultar albaranes...')
            except Exception:
                logging.exception('Error instanciando ConsultarAlbaranUI en show_consultar')
        except Exception:
            logging.exception('Error abriendo consultar en AlmacenView')
    
    def show_detalle_albaran(self, albaran_id):
        """Mostrar detalle de albarán para consulta/edición.

        Args:
            albaran_id (int): ID del albarán a mostrar
        """
        try:
            from .ui.albaranes.detalle_albaran import DetalleAlbaranUI
            try:
                detalle_ui = DetalleAlbaranUI(
                    self.central_area,
                    db=self.db,
                    albaran_id=albaran_id,
                    owner=self,
                    module_name='almacen',
                )
                if self.set_central_content(detalle_ui):
                    self.actualizar_ruta('ALBARANES / CONSULTAR / DETALLE', callbacks=self.breadcrumb_callbacks)
                    logging.info(f'Abriendo detalle albarán {albaran_id}...')
            except Exception:
                logging.exception('Error instanciando DetalleAlbaranUI en show_detalle_albaran')
        except Exception:
            logging.exception(f'Error abriendo detalle albarán {albaran_id} en AlmacenView')
    # attach_to_nav kept for compatibility with main navigation
    def attach_to_nav(self, nav_frame, button_config: dict):
        try:
            from kool_tpv.utils.global_buttons import create_nav_button
            btn = create_nav_button(nav_frame, text=button_config.get('text', 'ALMACÉN'), fg_color=button_config.get('color', '#32CD32'), hover_color=button_config.get('hover_color', '#00A4DF'), command=self.open)
            btn.pack(side='left', padx=6)
            return btn
        except Exception:
            logging.exception('Error attach_to_nav AlmacenView')
            return None
