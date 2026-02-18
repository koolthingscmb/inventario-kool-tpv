"""UI de Albaranes - entrada manual con scanner EAN.
"""
import logging
import customtkinter as ctk

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL
from kool_tpv.modulos.almacen.ui.albaranes.entrada_manual import EntradaManualUI
from kool_tpv.modulos.almacen.ui.albaranes.consultar_albaran import ConsultarAlbaranUI
from kool_tpv.modulos.almacen.ui.albaranes.detalle_albaran import DetalleAlbaranUI



class AlbaranesUI:
    def __init__(self, parent, db=None):
        self.parent = parent
        self.db = db
        self.albaran_service = AlbaranService(db)
        self.proveedor_service = ProveedorService(db)

        self.container = ctk.CTkFrame(self.parent, fg_color=COLOR_BG_TERMINAL)

        # Botones superiores
        btn_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        btn_frame.pack(fill='x', padx=12, pady=8)
        btn_frame.pack_propagate(False)

        botones = [
            ('ENTRADA MANUAL', '#2ecc71', self.show_entrada_manual),
            ('IMPORTAR ALBARÁN', '#3498db', self._placeholder),
            ('CONSULTAR', '#9b59b6', self.show_consultar),
            ('EXPORTAR', '#e67e22', self._placeholder),
            ('SALIDA MANUAL', '#e74c3c', self._placeholder),
            ('DEVOLUCIÓN', '#95a5a6', self._placeholder)
        ]

        for texto, color, cmd in botones:
            btn = ctk.CTkButton(btn_frame, text=texto, fg_color=color, command=cmd)
            btn.pack(side='left', padx=6)

        # Área central (cambia según botón)
        self.central_area = ctk.CTkFrame(self.container, fg_color=COLOR_BG_TERMINAL)
        self.central_area.pack(fill='both', expand=True, padx=12, pady=6)

        # Estado inicial vacío
        self.current_view = None

    def get_widget(self):
        return self.container

    def show_entrada_manual(self):
        try:
            for w in list(self.central_area.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            entrada_ui = EntradaManualUI(self.central_area, db=self.db)
            entrada_ui.get_widget().pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error cargando EntradaManualUI')

    

    def _placeholder(self):
        logging.info('Función pendiente de implementar')

    def show_consultar(self):
        """Mostrar UI de consulta de albaranes con filtros."""
        try:
            # Limpiar central_area
            for w in list(self.central_area.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            # Instanciar y mostrar ConsultarAlbaranUI
            consultar_ui = ConsultarAlbaranUI(self.central_area, db=self.db, owner=self)
            try:
                consultar_ui.get_widget().pack(fill='both', expand=True)
            except Exception:
                # Fallback: if widget is the instance itself
                try:
                    consultar_ui.pack(fill='both', expand=True)
                except Exception:
                    pass
        except Exception:
            logging.exception('Error cargando ConsultarAlbaranUI')

    def show_detalle_albaran(self, albaran_id):
        """Mostrar detalle de albarán para consulta/edición."""
        try:
            # Limpiar central_area
            for w in list(self.central_area.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            # Instanciar y mostrar DetalleAlbaranUI
            detalle_ui = DetalleAlbaranUI(self.central_area, db=self.db, albaran_id=albaran_id, owner=self)
            try:
                detalle_ui.get_widget().pack(fill='both', expand=True)
            except Exception:
                try:
                    detalle_ui.pack(fill='both', expand=True)
                except Exception:
                    pass

            logging.info(f'Detalle albarán {albaran_id} cargado correctamente')
        except Exception:
            logging.exception(f'Error cargando DetalleAlbaranUI para albarán {albaran_id}')
