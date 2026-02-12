"""UI para histórico de cierres — basado en SelectionOverlayTemplate y SelectionOverlayVisor.

Muestra los últimos 25 cierres y mantiene siempre activo el VisorNegro.
Botones: Imprimir (blanco texto negro), Mostrar, Exportar, Ver Tickets.
"""
import logging
from typing import Optional, List, Dict, Any

import customtkinter as ctk

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.base_datos.cierre_service import CierreService
from kool_tpv.utils.custom_dialog import show_warning


class CierreHistoricoUI(SelectionOverlayTemplate):
    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        ui_cfg = {
            'page_size': 25,
        }
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        self.db = db
        self.cierre_svc = CierreService(self.db)
        self.visor_helper = SelectionOverlayVisor(self)

        # Title
        self.title_text = 'HISTÓRICO DE CIERRES'
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Columns required
        self.columns_config = [
            ("id", "Cierre ID", 100, "center"),
            ("fecha", "Fecha", 180, "center"),
            ("cajero", "Usuario", 140, "center"),
            ("num_ventas", "Total tickets", 120, "center"),
            ("total_ingresos", "Total €", 120, "e"),
        ]
        try:
            self._aplicar_config_columnas(self.columns_config)
        except Exception:
            logging.exception('Error aplicando columnas en CierreHistoricoUI')

        # Add buttons into header_actions_frame (template provides it)
        try:
            # Ensure header_actions_frame exists
            haf = getattr(self, 'header_actions_frame', None)
            if haf is None:
                haf = self.header_actions_frame = getattr(self, 'header_actions_frame', None)

            # Imprimir (white bg, black text)
            self.imprimir_btn = ctk.CTkButton(haf, text='Imprimir', fg_color='#FFFFFF', text_color='#000000', width=140, command=self._on_imprimir)
            self.mostrar_btn = ctk.CTkButton(haf, text='Mostrar', width=140, command=self._on_mostrar)
            self.exportar_btn = ctk.CTkButton(haf, text='Exportar', width=140, command=self._on_exportar)
            self.ver_tickets_btn = ctk.CTkButton(haf, text='Ver Tickets', width=140, command=self._on_ver_tickets)

            # Pack buttons left to right
            try:
                self.imprimir_btn.pack(side='left', padx=5)
                self.mostrar_btn.pack(side='left', padx=5)
                self.exportar_btn.pack(side='left', padx=5)
                self.ver_tickets_btn.pack(side='left', padx=5)
            except Exception:
                pass
        except Exception:
            logging.exception('Error creando botones header en CierreHistoricoUI')

        # Load initial items
        self._load_and_render('')

    def _load_and_render(self, termino: str = ''):
        try:
            # List latest 25 cierres, ordered desc by fecha
            items = self.cierre_svc.listar_cierres(limit=25, offset=0)
            # Convert to format expected by SelectionOverlayVisor
            rows = []
            for r in items or []:
                rows.append({
                    'id': r.get('id'),
                    'fecha': r.get('fecha_hora'),
                    'cajero': r.get('cajero'),
                    'num_ventas': r.get('num_ventas'),
                    'total_ingresos': r.get('total_ingresos'),
                })
            try:
                if getattr(self, 'visor_helper', None) is not None:
                    self.visor_helper.render_items(rows)
                else:
                    self._items = rows
                    self._current_page = 0
                    self._render_clients_page()
            except Exception:
                logging.exception('Error renderizando items en CierreHistoricoUI')
        except Exception:
            logging.exception('Error cargando cierres en CierreHistoricoUI')

    def _get_selected_single_id(self) -> Optional[int]:
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                return None
            if len(sel) > 1:
                # show warning
                try:
                    show_warning(self.overlay if getattr(self, 'overlay', None) is not None else None, 'ATENCIÓN', 'Solo puedes tener un cierre seleccionado')
                except Exception:
                    pass
                return None
            try:
                return int(sel[0])
            except Exception:
                return None
        except Exception:
            logging.exception('Error obteniendo selección en CierreHistoricoUI')
            return None

    def _on_mostrar(self):
        try:
            sid = self._get_selected_single_id()
            if sid is None:
                return
            cierre = self.cierre_svc.obtener_cierre_por_id(sid)
            text = cierre.get('cierre_text') if cierre else f'Cierre {sid} - sin texto'
            # Ensure VisorNegro exists and show text
            try:
                if getattr(self, 'view', None) is not None and getattr(self.view, 'cart_view', None) is not None:
                    parent = self.view.cart_view
                else:
                    parent = self.overlay
                from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
                if getattr(self, '_visor_negro', None) is None:
                    try:
                        self._visor_negro = VisorNegro(parent)
                    except Exception:
                        logging.exception('Error instanciando VisorNegro en CierreHistoricoUI')
                try:
                    self._visor_negro.set_text_color('#00FF00')
                except Exception:
                    pass
                try:
                    self._visor_negro.set_text(text)
                except Exception:
                    self._visor_negro.set_text(str(text))
                try:
                    self._visor_negro.show()
                except Exception:
                    pass
            except Exception:
                logging.exception('Error mostrando cierre en VisorNegro desde CierreHistoricoUI')
        except Exception:
            logging.exception('Error en _on_mostrar CierreHistoricoUI')

    def _on_imprimir(self):
        try:
            sid = self._get_selected_single_id()
            if sid is None:
                return
            cierre = self.cierre_svc.obtener_cierre_por_id(sid)
            text = cierre.get('cierre_text') if cierre else None
            # Direct print to stdout (no dialog)
            if text:
                try:
                    print(text)
                except Exception:
                    logging.exception('Error imprimiendo cierre (stdout)')
        except Exception:
            logging.exception('Error en _on_imprimir CierreHistoricoUI')

    def _on_exportar(self):
        try:
            # Placeholder: export selected list to PDF (to implement)
            sel = list(self.tree.selection() or [])
            if not sel:
                show_warning(self.overlay if getattr(self, 'overlay', None) is not None else None, 'ATENCIÓN', 'No hay cierres seleccionados para exportar')
                return
            # For now, just log
            logging.info('Exportar solicitado para cierres: %s', sel)
        except Exception:
            logging.exception('Error en _on_exportar CierreHistoricoUI')

    def _on_ver_tickets(self):
        try:
            sid = self._get_selected_single_id()
            if sid is None:
                return
            # Placeholder: open tickets_ui for cierre sid (ventana por implementar)
            logging.info('Ver Tickets solicitado para cierre id=%s', sid)
        except Exception:
            logging.exception('Error en _on_ver_tickets CierreHistoricoUI')

    def show(self) -> None:
        try:
            super().show()
        except Exception:
            logging.exception('Error mostrando CierreHistoricoUI via super().show')

        # Always enable vis mode for this overlay
        try:
            if getattr(self, 'visor_helper', None) is not None:
                try:
                    self.visor_helper.configure_vis_mode()
                except Exception:
                    logging.exception('Error configurando vis mode en CierreHistoricoUI')
        except Exception:
            logging.exception('Error invocando visor_helper en CierreHistoricoUI.show')

        # Restore title
        try:
            self.title_text = 'HISTÓRICO DE CIERRES'
            if hasattr(self, 'header_label') and self.header_label is not None:
                try:
                    self.header_label.configure(text=self.title_text)
                except Exception:
                    pass
        except Exception:
            pass
*** End of File
