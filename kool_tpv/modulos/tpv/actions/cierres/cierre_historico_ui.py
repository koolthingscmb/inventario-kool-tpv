"""Interfaz de históricos de cierres.

Reutiliza `SelectionOverlayTemplate` para mostrar los últimos 25 cierres
con columnas específicas y botones: Imprimir, Mostrar, Exportar, Ver Tickets.
"""
from typing import Optional, List, Dict, Any
import logging

import customtkinter as ctk

from kool_tpv.utils.templates.template_selection_overlay import SelectionOverlayTemplate
from kool_tpv.utils.templates.selection_overlay_visor import SelectionOverlayVisor
from kool_tpv.base_datos.cierre_service import CierreService


class CierreHistoricoUI(SelectionOverlayTemplate):
    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        # configure UI defaults: show 25 items
        ui_cfg = {'page_size': 25, 'min_page_size': 25}
        # set title and columns before calling super so header is initialized with correct text
        self.title_text = 'HISTÓRICOS'
        # Columns keys must match the dict keys produced in loader
        self.columns_config = [
            ("cierre_id", "ID cierre", 100, "center"),
            ("fecha", "Fecha", 180, "center"),
            ("usuario", "Usuario", 140, "center"),
            ("num_tickets", "Total tickets", 120, "center"),
            ("total", "Total €", 120, "e"),
        ]

        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        # data access
        self.db = db
        self.cierre_svc = CierreService(db)

        # Replace default aceptar/anadir buttons with requested header buttons
        try:
            try:
                self.aceptar_btn.pack_forget()
            except Exception:
                pass
            try:
                self.anadir_btn.pack_forget()
            except Exception:
                pass

            # Imprimir (white bg, black text)
            self.imprimir_btn = ctk.CTkButton(self.header_actions_frame, text="IMPRIMIR", fg_color="#FFFFFF", text_color="#000000", command=self._on_imprimir, width=140)
            self.mostrar_btn = ctk.CTkButton(self.header_actions_frame, text="Mostrar", command=self._on_mostrar, width=140)
            self.exportar_btn = ctk.CTkButton(self.header_actions_frame, text="Exportar", command=self._on_exportar, width=140)
            self.ver_tickets_btn = ctk.CTkButton(self.header_actions_frame, text="Ver Tickets", command=self._on_ver_tickets, width=140)

            self.imprimir_btn.pack(side="left", padx=5)
            self.mostrar_btn.pack(side="left", padx=5)
            self.exportar_btn.pack(side="left", padx=5)
            self.ver_tickets_btn.pack(side="left", padx=5)
        except Exception:
            logging.exception('Error creando botones header en CierreHistoricoUI')

        # instantiate visor helper for rendering
        try:
            self.visor_helper = SelectionOverlayVisor(self)
        except Exception:
            logging.exception('Error instanciando SelectionOverlayVisor en CierreHistoricoUI')

    def _load_and_render(self, termino: str = ''):
        """Cargar los últimos 25 cierres ordenados por fecha descendente y renderizar."""
        try:
            sql = "SELECT id, fecha_hora, cajero, num_ventas, total_ingresos FROM cierres_caja ORDER BY fecha_hora DESC LIMIT 25"
            rows = []
            try:
                rows = self.db.fetch_all(sql)
            except Exception:
                logging.exception('Error consultando cierres en CierreHistoricoUI')
                rows = []

            items: List[Dict[str, Any]] = []
            for r in rows or []:
                try:
                    items.append({
                        'cierre_id': r[0],
                        'fecha': r[1],
                        'usuario': r[2],
                        'num_tickets': int(r[3] or 0),
                        'total': float(r[4] or 0.0),
                    })
                except Exception:
                    logging.exception('Error transformando fila de cierre a dict')

            # Use visor_helper to render items into the template tree
            try:
                if getattr(self, 'visor_helper', None) is not None:
                    self.visor_helper.render_items(items)
                else:
                    # fallback: try to insert directly
                    for iid in list(self.tree.get_children()):
                        self.tree.delete(iid)
                    for it in items:
                        iid = str(it.get('cierre_id') or '')
                        vals = tuple(it.get(k) for k, *_ in self.columns_config)
                        self.tree.insert('', 'end', iid=iid, values=vals)
            except Exception:
                logging.exception('Error renderizando items en CierreHistoricoUI')

        except Exception:
            logging.exception('Error en _load_and_render de CierreHistoricoUI')

    # Button callbacks (minimal implementations)
    def _on_imprimir(self):
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                logging.info('No selection to print in Historico')
                return
            cid = int(sel[0])
            # Try to get cierre text from DB via CierreService or generate minimal summary
            try:
                cierre = self.cierre_svc.obtener_cierre_por_id(cid)
                if cierre:
                    # print a compact summary to stdout for now
                    print(f"Cierre {cierre.get('cierre_num')} - {cierre.get('fecha_hora')} - {cierre.get('cajero')}")
                    print(f"Total ingresos: {cierre.get('total_ingresos')}")
                    return
            except Exception:
                logging.exception('Error generando impresión de cierre')
        except Exception:
            logging.exception('Error en _on_imprimir')

    def _on_mostrar(self):
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                return
            cid = int(sel[0])
            # Show detailed info in VisorNegro if present
            try:
                if getattr(self, '_visor_negro', None) is None and getattr(self, 'view', None) is not None and getattr(self.view, 'cart_view', None) is not None:
                    self._visor_negro = self.visor_helper and getattr(self.visor_helper, 'parent', None) and None
                # Use CierreService to fetch cierre and display basic text
                cierre = self.cierre_svc.obtener_cierre_por_id(cid)
                if cierre:
                    txt = []
                    txt.append(f"CIERRE {cierre.get('cierre_num')}\n")
                    txt.append(f"Fecha: {cierre.get('fecha_hora')}")
                    txt.append(f"Cajero: {cierre.get('cajero')}")
                    txt.append(f"Total ingresos: {cierre.get('total_ingresos')}")
                    try:
                        if getattr(self, '_visor_negro', None) is None and getattr(self, 'view', None) is not None and getattr(self.view, 'cart_view', None) is not None:
                            self._visor_negro = VisorNegro(self.view.cart_view)
                    except Exception:
                        pass
                    try:
                        if getattr(self, '_visor_negro', None):
                            self._visor_negro.set_text('\n'.join(txt))
                            self._visor_negro.show()
                    except Exception:
                        print('\n'.join(txt))
            except Exception:
                logging.exception('Error mostrando cierre en visor')
        except Exception:
            logging.exception('Error en _on_mostrar')

    def _on_exportar(self):
        logging.info('Exportar histórico: función no implementada')

    def _on_ver_tickets(self):
        logging.info('Ver Tickets: función no implementada')


# Expose simple factory for compatibility
def create_historico_ui(view_or_action_panel, db):
    return CierreHistoricoUI(view_or_action_panel, db)
