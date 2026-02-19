"""UI de Albaranes - entrada manual con scanner EAN.
"""
import logging
import customtkinter as ctk

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.utils import COLOR_BG_TERMINAL, COLOR_MATRIX, FONT_TERMINAL




class AlbaranesUI:
    def __init__(self, parent, db=None, owner=None):
        self.parent = parent
        self.db = db
        self.owner = owner
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
            ('SALIDA MANUAL', '#e74c3c', self.show_salida_manual),
            ('DEVOLUCIÓN', '#95a5a6', self.show_devolucion)
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
        """Mostrar entrada manual (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_entrada_manual'):
                self.owner.show_entrada_manual()
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_entrada_manual')
        except Exception:
            logging.exception('Error en show_entrada_manual')

    def show_salida_manual(self):
        """Mostrar salida manual (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_salida_manual'):
                self.owner.show_salida_manual()
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_salida_manual')
        except Exception:
            logging.exception('Error en show_salida_manual')

    def show_devolucion(self):
        """Mostrar devolución (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_devolucion'):
                self.owner.show_devolucion()
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_devolucion')
        except Exception:
            logging.exception('Error en show_devolucion')

    

    def _placeholder(self):
        logging.info('Función pendiente de implementar')

    def show_consultar(self):
        """Mostrar consulta de albaranes (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_consultar'):
                self.owner.show_consultar()
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_consultar')
        except Exception:
            logging.exception('Error en show_consultar')

    def show_detalle_albaran(self, albaran_id):
        """Mostrar detalle de albarán (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_detalle_albaran'):
                self.owner.show_detalle_albaran(albaran_id)
                logging.info(f'Detalle albarán {albaran_id} cargado correctamente')
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_detalle_albaran')
        except Exception:
            logging.exception(f'Error en show_detalle_albaran para albarán {albaran_id}')
