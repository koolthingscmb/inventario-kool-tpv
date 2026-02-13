"""Interfaz de históricos de cierres.

Reusa el layout de `CierreUI` pero sustituye título, botones y columnas para
mostrar los últimos 25 cierres.
"""
from typing import Optional, List, Dict, Any
import logging

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

            # Ocultar checkboxes
            try:
                if hasattr(parent, '_header_checks_row'):
                    parent._header_checks_row.pack_forget()
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

            # Mostrar botones adicionales de histórico
            for btn in ['mostrar_btn', 'exportar_btn', 'ver_tickets_btn']:
                try:
                    if hasattr(parent, btn):
                        getattr(parent, btn).pack(side='left', padx=5)
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
                    if getattr(parent, '_visor_negro', None) is None:
                        try:
                            parent._visor_negro = VisorNegro(parent_widget)
                        except Exception:
                            logging.exception('Error creando VisorNegro (handler)')
                    try:
                        parent._visor_negro.set_text('')
                        parent._visor_negro.set_text_color('#00FF00')
                        parent._visor_negro.set_font_size(13)
                        parent._visor_negro.show()
                    except Exception:
                        pass
            except Exception:
                logging.exception('Error al configurar VisorNegro (handler)')

            # Bind doble clic en el tree para mostrar cierre (si existe)
            try:
                tree = getattr(parent, 'tree', None)
                if tree is not None:
                    try:
                        tree.bind('<Double-1>', lambda e: self.on_mostrar())
                    except Exception:
                        pass
            except Exception:
                pass

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

    def on_mostrar(self):
        """Mostrar el `cierre_text` del cierre seleccionado en el VisorNegro.

        Reglas:
        - Si no hay selección: no hace nada.
        - Si hay más de 1 selección: mostrar diálogo de error (solo 1 permitido).
        - Si hay 1 selección: obtener cierre por id y mostrar `cierre_text`.
        """
        try:
            parent = self.parent
            tree = getattr(parent, 'tree', None)
            sel = list(tree.selection() or []) if tree is not None else []

            if not sel:
                logging.info('No hay selección para Mostrar (Historico handler)')
                return

            # Si hay más de uno -> error modal
            if len(sel) > 1:
                try:
                    from kool_tpv.utils.custom_dialog import show_error
                    root = parent.overlay.winfo_toplevel() if getattr(parent, 'overlay', None) is not None else None
                    show_error(root, 'Error', 'Solamente se puede Mostrar un cierre a la vez')
                except Exception:
                    logging.exception('Error mostrando diálogo de selección múltiple en Mostrar')
                return

            # Mostrar cierre único
            try:
                cid = int(sel[0])
            except Exception:
                logging.info('ID seleccionado inválido para Mostrar')
                return

            try:
                cierre = self.cierre_svc.obtener_cierre_por_id(cid) if self.cierre_svc is not None else None
                cierre_text = cierre.get('cierre_text') if cierre is not None else ''
            except Exception:
                logging.exception('Error recuperando cierre para Mostrar')
                cierre_text = ''

            try:
                view = getattr(parent, 'view', None)
                parent_widget = None
                if view is not None and getattr(view, 'cart_view', None) is not None:
                    parent_widget = view.cart_view
                else:
                    parent_widget = getattr(parent, 'overlay', None)

                if parent_widget is not None:
                    if getattr(parent, '_visor_negro', None) is None:
                        try:
                            parent._visor_negro = VisorNegro(parent_widget)
                        except Exception:
                            logging.exception('Error creando VisorNegro (mostrar)')
                    try:
                        parent._visor_negro.set_text_color('#00FF00')
                    except Exception:
                        pass
                    try:
                        parent._visor_negro.set_font_size(13)
                    except Exception:
                        pass
                    try:
                        parent._visor_negro.set_text(cierre_text or '')
                        parent._visor_negro.show()
                    except Exception:
                        logging.exception('Error mostrando cierre_text en VisorNegro')
            except Exception:
                logging.exception('Error configurando VisorNegro para Mostrar')

        except Exception:
            logging.exception('Error en on_mostrar (handler)')


# Only HistoricoHandler is needed for mode integration; older
# CierreHistoricoUI class removed to avoid duplicate UIs.
