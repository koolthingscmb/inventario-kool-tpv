"""Interfaz de históricos de cierres.

Reusa el layout de `CierreUI` pero sustituye título, botones y columnas para
mostrar los últimos 25 cierres.
"""
from typing import Optional, List, Dict, Any
import logging

import customtkinter as ctk

from .cierre_base_ui import CierreBaseUI
from kool_tpv.base_datos.cierre_service import CierreService


class CierreHistoricoUI(CierreBaseUI):
    def __init__(self, view_or_action_panel, db, on_selection_callback: Optional[callable] = None):
        # Keep a page_size matching CierreUI so proportions are identical
        ui_cfg = { 'page_size': 25 }

        # Title specific for this UI
        self.title_text = 'HISTÓRICOS'

        # Initialize base layout
        super().__init__(view_or_action_panel, db=db, on_selection_callback=on_selection_callback, ui_config=ui_cfg)

        # Ensure header label shows HISTÓRICOS
        try:
            if hasattr(self, 'header_label') and self.header_label is not None:
                self.header_label.configure(text=self.title_text)
        except Exception:
            pass

        # Add a clean header with only the buttons needed for Histórico
        try:
            self._add_header_controls()
        except Exception:
            logging.exception('Error añadiendo header controls en CierreHistoricoUI')

        # Columns configured to match overall width/proportion of CierreUI
        try:
            self.columns_config = [
                ("cierre_id", "ID cierre", 100, "center"),
                ("fecha", "Fecha", 180, "center"),
                ("usuario", "Usuario", 80, "center"),
                ("num_tickets", "Total tickets", 80, "center"),
                ("total", "Total €", 80, "e"),
            ]
            try:
                self._aplicar_config_columnas(self.columns_config)
            except Exception:
                pass
        except Exception:
            logging.exception('Error aplicando columnas en CierreHistoricoUI')

        # Data service
        self.db = db
        self.cierre_svc = CierreService(db)

    def _add_header_controls(self):
        """Create the header buttons row for Histórico (clean, no pack_forget)."""
        try:
            container = getattr(self, 'top_buttons', None) or getattr(self, 'overlay', None)
            self._header_buttons_row = ctk.CTkFrame(self.top_buttons if hasattr(self, 'top_buttons') else container, fg_color='transparent')
            self._header_buttons_row.pack(side='top', fill='x', pady=(6, 4))

            self.imprimir_btn = ctk.CTkButton(self._header_buttons_row, text="IMPRIMIR", width=140, fg_color="#FFFFFF", text_color="#000000", command=self._on_imprimir)
            self.mostrar_btn = ctk.CTkButton(self._header_buttons_row, text="Mostrar", width=140, command=self._on_mostrar)
            self.exportar_btn = ctk.CTkButton(self._header_buttons_row, text="Exportar", width=140, command=self._on_exportar)
            self.ver_tickets_btn = ctk.CTkButton(self._header_buttons_row, text="Ver Tickets", width=140, command=self._on_ver_tickets)

            self.imprimir_btn.pack(side="left", padx=5)
            self.mostrar_btn.pack(side="left", padx=5)
            self.exportar_btn.pack(side="left", padx=5)
            self.ver_tickets_btn.pack(side="left", padx=5)
        except Exception:
            logging.exception('Error creando header buttons en CierreHistoricoUI')

    def _load_and_render(self, termino: str = ''):
        """Load last 25 closures ordered by fecha_hora desc and render into the tree."""
        try:
            sql = "SELECT id, fecha_hora, cajero, num_ventas, total_ingresos FROM cierres_caja ORDER BY fecha_hora DESC LIMIT 25"
            rows = self.db.fetch_all(sql)
            items: List[Dict[str, Any]] = []
            for r in rows or []:
                items.append({
                    'cierre_id': r[0],
                    'fecha': r[1],
                    'usuario': r[2],
                    'num_tickets': int(r[3] or 0),
                    'total': float(r[4] or 0.0),
                })

            # clear tree and insert items matching columns_config order
            try:
                for iid in list(self.tree.get_children()):
                    self.tree.delete(iid)
            except Exception:
                pass

            for it in items:
                try:
                    iid = str(it.get('cierre_id') or '')
                    vals = tuple(it.get(col[0]) for col in self.columns_config)
                    self.tree.insert('', 'end', iid=iid, values=vals)
                except Exception:
                    logging.exception('Error insertando fila historico en tree')

        except Exception:
            logging.exception('Error cargando historico de cierres')

    # Button callbacks (minimal, reuse CierreUI behavior where possible)
    def _on_imprimir(self):
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                logging.info('No selection to print in Historico')
                return
            cid = int(sel[0])
            cierre = self.cierre_svc.obtener_cierre_por_id(cid)
            if cierre:
                print(f"Cierre {cierre.get('cierre_num')} - {cierre.get('fecha_hora')} - {cierre.get('cajero')}")
                print(f"Total ingresos: {cierre.get('total_ingresos')}")
        except Exception:
            logging.exception('Error en _on_imprimir historico')

    def _on_mostrar(self):
        try:
            sel = list(self.tree.selection() or [])
            if not sel:
                return
            cid = int(sel[0])
            cierre = self.cierre_svc.obtener_cierre_por_id(cid)
            if cierre:
                txt = [f"CIERRE {cierre.get('cierre_num')}\n", f"Fecha: {cierre.get('fecha_hora')}", f"Cajero: {cierre.get('cajero')}", f"Total ingresos: {cierre.get('total_ingresos')}"]
                try:
                    if getattr(self, '_visor_negro', None) is None and getattr(self, 'view', None) is not None and getattr(self.view, 'cart_view', None) is not None:
                        from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro
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
            logging.exception('Error en _on_mostrar historico')

    def _on_exportar(self):
        logging.info('Exportar histórico: función no implementada')

    def _on_ver_tickets(self):
        logging.info('Ver Tickets: función no implementada')


def create_historico_ui(view_or_action_panel, db):
    return CierreHistoricoUI(view_or_action_panel, db)
