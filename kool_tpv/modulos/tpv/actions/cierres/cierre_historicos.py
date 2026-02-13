"""UI para historial de cierres.

Usa `SelectionOverlayTemplate` + `SelectionOverlayVisor` y mantiene el
`VisorNegro` activo mientras la UI esté abierta (no cambia tamaños del template).
"""
import logging
from typing import Optional

import customtkinter as ctk

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.base_datos.cierre_service import CierreService


class CierreHistoricoUI(SelectionOverlayTemplate):
    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        ui_cfg = {
            'page_size': 25,
        }
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        self.db = db
        self.cierre_svc = CierreService(db)

        # Title
        self.title_text = 'HISTÓRICO CIERRES'
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Columns: map to keys returned by CierreService.listar_cierres
        self.columns_config = [
            ("id", "ID", 80, "center"),
            ("fecha_hora", "Fecha cierre", 180, "center"),
            ("num_ventas", "Nº ventas", 120, "center"),
            ("total_ingresos", "Total €", 120, "e"),
        ]
        try:
            self._aplicar_config_columnas(self.columns_config)
        except Exception:
            logging.exception('Error aplicando columnas en CierreHistoricoUI')

        # visor helper
        try:
            self.visor_helper = SelectionOverlayVisor(self)
        except Exception:
            logging.exception('Error instanciando SelectionOverlayVisor en CierreHistoricoUI')

    def data_loader(self, item_id=None):
        """Cargar cierres desde la BD. Retorna lista de dicts esperada por el visor."""
        try:
            # listar últimas 500 cierres
            rows = self.cierre_svc.listar_cierres(limit=500, offset=0)
            # rows already are dicts from CierreService._row_to_dict
            return rows or []
        except Exception:
            logging.exception('Error cargando cierres en CierreHistoricoUI')
            return []

    def show(self):
        """Mostrar overlay y asegurar VisorNegro siempre visible mientras esté abierto."""
        try:
            # Configure visor mode to create and show VisorNegro
            try:
                if getattr(self, 'visor_helper', None) is not None:
                    self.visor_helper.configure_vis_mode()
            except Exception:
                logging.exception('Error configurando visor en CierreHistoricoUI')

            # call parent show (will call _load_and_render)
            super().show()

            # Ensure VisorNegro has empty text initially
            try:
                if getattr(self, '_visor_negro', None) is not None:
                    try:
                        self._visor_negro.set_text('')
                        self._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            logging.exception('Error mostrando CierreHistoricoUI')

    def hide(self):
        """Ocultar overlay y también ocultar el VisorNegro asociado.

        No cambia dimensiones del visor ni del overlay.
        """
        try:
            try:
                if getattr(self, '_visor_negro', None) is not None:
                    try:
                        self._visor_negro.set_text('')
                        self._visor_negro.hide()
                    except Exception:
                        pass
            except Exception:
                pass
        finally:
            try:
                super().hide()
            except Exception:
                logging.exception('Error ocultando CierreHistoricoUI')
