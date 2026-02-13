"""Interfaz de históricos de cierres.

Reusa el layout de `CierreUI` pero sustituye título, botones y columnas para
mostrar los últimos 25 cierres.
"""
from typing import Optional, List, Dict, Any
import logging

import customtkinter as ctk

from .cierre_base_ui import CierreBaseUI
from kool_tpv.base_datos.cierre_service import CierreService

from kool_tpv.modulos.tpv.ui.visor_negro import VisorNegro


class HistoricoHandler:
    """Handler ligero para integrar el modo 'historico' en `CierreUI`.

    Provee carga, render y configuración de modo sin requerir crear
    otra ventana completa. Está pensado para ser instanciado con
    `HistoricoHandler(parent)` donde `parent` es la instancia de `CierreUI`.
    """
    def __init__(self, parent):
        self.parent = parent
        self.db = getattr(parent, 'db', None)
        self.cierre_svc = CierreService(self.db) if self.db is not None else None

    def load_historico(self, termino: str = ''):
        """Return a list of historico items (dicts) to render."""
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
            return items
        except Exception:
            logging.exception('Error cargando historico (handler)')
            return []

    def render_historico(self, items: List[Dict[str, Any]]):
        """Render items into parent's treeview using parent's columns_config."""
        try:
            tree = getattr(self.parent, 'tree', None)
            if tree is None:
                return
            # clear
            for iid in list(tree.get_children()):
                try:
                    tree.delete(iid)
                except Exception:
                    pass
            # insert
            for it in items:
                try:
                    iid = str(it.get('cierre_id') or '')
                    vals = tuple(it.get(col[0]) for col in getattr(self.parent, 'columns_config', []))
                    tree.insert('', 'end', iid=iid, values=vals)
                except Exception:
                    logging.exception('Error insertando fila historico (handler)')
        except Exception:
            logging.exception('Error render_historico (handler)')

    def configurar_modo_historico(self):
        """Configurar la UI parent para mostrarse en modo histórico.

        Oculta botones de modo 'cierres', muestra el botón `imprimir` y
        crea/activa el `VisorNegro` inmediatamente.
        """
        try:
            parent = self.parent
            # Cambiar título
            try:
                parent.title_text = 'HISTÓRICOS'
                if hasattr(parent, 'header_label') and parent.header_label is not None:
                    parent.header_label.configure(text=parent.title_text)
            except Exception:
                pass

            # Aplicar columnas de historico
            try:
                parent._aplicar_config_columnas(parent.columns_config_historico)
            except Exception:
                pass

            # Ocultar controles de modo cierres si existen
            for attr in ('tickets_cierre_btn', 'historico_btn', 'cierre_z_btn', 'mostrar_btn'):
                try:
                    btn = getattr(parent, attr, None)
                    if btn is not None:
                        try:
                            btn.pack_forget()
                        except Exception:
                            pass
                except Exception:
                    pass

            # Mostrar botón imprimir
            try:
                if hasattr(parent, 'imprimir_btn'):
                    try:
                        parent.imprimir_btn.pack(side='left', padx=5)
                    except Exception:
                        pass
            except Exception:
                pass

            # Crear y mostrar VisorNegro inmediatamente
            try:
                view = getattr(parent, 'view', None)
                parent_widget = None
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    parent_widget = view.cart_view
                else:
                    parent_widget = getattr(parent, 'overlay', None)

                if parent_widget is not None:
                    try:
                        parent._visor_negro = VisorNegro(parent_widget)
                        parent._visor_negro.set_text('')
                        parent._visor_negro.show()
                    except Exception:
                        logging.exception('Error creando/mostrando VisorNegro (handler)')
            except Exception:
                logging.exception('Error al configurar VisorNegro (handler)')

        except Exception:
            logging.exception('Error configurando modo historico (handler)')

    def on_imprimir(self):
        """Imprimir el cierre seleccionado desde el handler."""
        try:
            parent = self.parent
            sel = list(getattr(parent, 'tree', None).selection() or [])
            if not sel:
                logging.info('No selection to print in Historico (handler)')
                return
            cid = int(sel[0])
            try:
                cierre = self.cierre_svc.obtener_cierre_por_id(cid)
                if cierre:
                    print(f"Cierre {cierre.get('cierre_num')} - {cierre.get('fecha_hora')} - {cierre.get('cajero')}")
                    print(f"Total ingresos: {cierre.get('total_ingresos')}")
            except Exception:
                logging.exception('Error generando impresión de cierre (handler)')
        except Exception:
            logging.exception('Error en on_imprimir (handler)')


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
