"""UI de Albaranes - entrada manual con scanner EAN.
"""
import logging
import customtkinter as ctk

from kool_tpv.base_datos.albaran_service import AlbaranService
from kool_tpv.base_datos.proveedor_service import ProveedorService
from kool_tpv.utils.config_loader import load_colors
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.almacen.ui.albaranes.exportar_albaran import ExportarAlbaranUI




class AlbaranesUI:
    def __init__(self, parent, db=None, owner=None):
        self.parent = parent
        self.db = db
        self.owner = owner
        self.module_name = 'almacen'
        try:
            self.colors = load_colors(self.module_name)
        except Exception:
            self.colors = {'background': '#1a1a1a', 'text': '#00FF00'}
        self.albaran_service = AlbaranService(db)
        self.proveedor_service = ProveedorService(db)

        self.container = ctk.CTkFrame(self.parent, fg_color=self.colors.get('background', '#1a1a1a'))

        # Botones superiores
        btn_frame = ctk.CTkFrame(self.container, fg_color='transparent', height=50)
        btn_frame.pack(fill='x', padx=12, pady=8)
        btn_frame.pack_propagate(False)

        # Prefer creating buttons from config when available, fallback to CTkButton
        botones = [
            ('ENTRADA MANUAL', self.show_entrada_manual),
            ('IMPORTAR',       self.show_importar_albaran),
            ('CONSULTAR',      self.show_consultar),
            ('EXPORTAR',       self.show_exportar),
            ('SALIDA MANUAL',  self.show_salida_manual),
            ('DEVOLUCIÓN',     self.show_devolucion),
        ]

        for texto, cmd in botones:
            btn = ButtonFactory.create_button(
                parent=btn_frame,
                text=texto,
                command=cmd,
                style_key='action_primary'
            )
            btn.pack(side='left', padx=6)

        # Área central (cambia según botón)
        self.central_area = ctk.CTkFrame(self.container, fg_color=self.colors.get('background', '#1a1a1a'))
        self.central_area.pack(fill='both', expand=True, padx=12, pady=6)

        # Estado inicial vacío
        self.current_view = None

        # Comprobar borradores pendientes al arrancar
        self.container.after(300, self._comprobar_borradores)

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

    def show_importar_albaran(self, borrador=None):
        """Mostrar importar albarán desde CSV (delega a owner)."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_importar_albaran'):
                self.owner.show_importar_albaran(borrador=borrador)
            else:
                logging.warning('AlbaranesUI: owner no disponible para show_importar_albaran')
        except Exception:
            logging.exception('Error en show_importar_albaran')

    def show_exportar(self):
        """Mostrar interfaz de exportación de albaranes."""
        try:
            # Limpiar área central
            for widget in self.central_area.winfo_children():
                widget.destroy()

            # Crear UI de exportación en el área central
            self.current_view = ExportarAlbaranUI(
                parent=self.central_area,
                db=self.db,
                on_close_callback=lambda: self._limpiar_central_area()
            )
        except Exception:
            logging.exception('Error mostrando ExportarAlbaranUI')

    def _limpiar_central_area(self):
        """Limpiar área central."""
        for widget in self.central_area.winfo_children():
            widget.destroy()
        self.current_view = None

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

    def _comprobar_borradores(self):
        """Comprobar si hay borradores pendientes y avisar al usuario."""
        try:
            from kool_tpv.modulos.almacen.ui.albaranes.albaran_borrador import AlbaranBorradorService
            from kool_tpv.utils.dialogs import show_warning

            svc = AlbaranBorradorService()
            borrador = svc.mas_reciente()
            if not borrador:
                return

            num = borrador.get('num_albaran', '?')
            prov = borrador.get('proveedor_nombre', '?')
            ts = borrador.get('timestamp', '')[:16].replace('T', ' ')
            mensaje = f'Albarán nº {num} ({prov})\nGuardado: {ts}'

            resultado = show_warning(
                self.container,
                titulo='Borrador pendiente',
                mensaje=mensaje,
                confirm=True
            )
            if resultado:
                self._continuar_borrador(borrador)
        except Exception:
            logging.exception('Error comprobando borradores')

    def _continuar_borrador(self, borrador_info: dict):
        """Abrir ImportarAlbaranUI y cargar el borrador."""
        try:
            if getattr(self, 'owner', None) and hasattr(self.owner, 'show_importar_albaran'):
                self.owner.show_importar_albaran(borrador=borrador_info)
            else:
                logging.warning('AlbaranesUI: owner no disponible para continuar borrador')
        except Exception:
            logging.exception('Error continuando borrador')
