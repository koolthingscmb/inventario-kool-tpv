"""Módulo Clientes - orchestrator."""
import logging
from kool_tpv.utils.templates.base_module_view import BaseModuleView
from kool_tpv.modulos.clientes.clientes_tickets import ClientesTicketsUI


class ClientesView(BaseModuleView):
    """Vista principal del módulo Clientes."""

    def __init__(self, parent, db, keyboard_manager=None):
        super().__init__(parent, config_section='clientes')
        self.parent = parent
        self.db = db
        # Guardar referencia al KeyboardManager (opcional)
        try:
            self.keyboard_mgr = keyboard_manager
        except Exception:
            self.keyboard_mgr = None

        # Actualizar breadcrumb
        try:
            self.actualizar_ruta('CLIENTES')
        except Exception:
            pass

        # Breadcrumb callbacks
        self.breadcrumb_callbacks = {
            'CLIENTES': self.show_busqueda, # Breadcrumb vuelve a búsqueda
            'BÚSQUEDA': self.show_busqueda,
        }

        logging.info('ClientesView inicializado')

    # Placeholders para botones (se implementarán después)
    def show_busqueda(self):
        """Mostrar búsqueda de clientes."""
        try:
            from kool_tpv.modulos.clientes.busqueda_clientes_ui import BusquedaClientesUI

            try:
                busqueda_ui = BusquedaClientesUI(
                    self.central_area,
                    db=self.db,
                    owner=self,
                    module_name='clientes',
                    keyboard_manager=getattr(self, 'keyboard_mgr', None)
                )
                if self.set_central_content(busqueda_ui):
                    self.actualizar_ruta('CLIENTES / BÚSQUEDA', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo búsqueda clientes...')
            except Exception:
                logging.exception('Error instanciando BusquedaClientesUI')
        except Exception:
            logging.exception('Error abriendo búsqueda clientes')

    def show_tickets(self, cliente_id: int, cliente_nombre: str = ''):
        """Abrir vista de tickets de un cliente específico.

        Args:
            cliente_id: ID del cliente
            cliente_nombre: Nombre del cliente para breadcrumb
        """
        try:
            tickets_ui = ClientesTicketsUI(
                parent=self.central_area,
                db=self.db,
                cliente_id=cliente_id,
                cliente_nombre=cliente_nombre,
                keyboard_manager=getattr(self, 'keyboard_mgr', None)
            )

            # Usar set_central_content para gestión automática
            if self.set_central_content(tickets_ui):
                breadcrumb_text = f'CLIENTES / {cliente_nombre.upper()} / TICKETS'
                try:
                    # Ensure breadcrumb_callbacks exists and update it in-place (clean approach)
                    try:
                        if not hasattr(self, 'breadcrumb_callbacks') or self.breadcrumb_callbacks is None:
                            self.breadcrumb_callbacks = {}
                    except Exception:
                        self.breadcrumb_callbacks = {}

                    # Standard navigation: CLIENTES -> show_busqueda
                    self.breadcrumb_callbacks['CLIENTES'] = self.show_busqueda

                    # Make the client name clickable to edit that client
                    try:
                        self.breadcrumb_callbacks[cliente_nombre.upper()] = (lambda cid=cliente_id: self.show_editar_cliente(cid))
                    except Exception:
                        pass

                    # Update breadcrumb using the centralized callbacks map
                    self.actualizar_ruta(breadcrumb_text, callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info(f'Vista tickets abierta para cliente_id={cliente_id}')
            else:
                logging.error('No fue posible montar ClientesTicketsUI')

        except Exception:
            logging.exception('Error abriendo vista tickets')
            try:
                from kool_tpv.utils.custom_dialog import show_error
                show_error(self.central_area, 'Error', 'No se pudo abrir tickets del cliente')
            except Exception:
                pass

    def show_tops(self):
        try:
            from kool_tpv.modulos.clientes.clientes_tops_ui import ClientesTopsUI

            ui = ClientesTopsUI(
                parent=self.central_area,
                db=self.db,
                owner=self,
                keyboard_manager=getattr(self, 'keyboard_mgr', None),
            )

            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('CLIENTES / TOPS', callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info('Mostrando TOPS clientes (UI)')
            else:
                logging.error('No fue posible montar ClientesTopsUI')

        except Exception:
            logging.exception('Error en show_tops')

    def show_comunicacion(self):
        try:
            from kool_tpv.modulos.clientes.clientes_comunicacion import ClientesComunicacionView

            ui = ClientesComunicacionView(
                parent=self.central_area,
                db=self.db,
                owner=self,
                keyboard_manager=getattr(self, 'keyboard_mgr', None),
            )

            if self.set_central_content(ui):
                try:
                    self.actualizar_ruta('CLIENTES / COMUNICACIÓN', callbacks=self.breadcrumb_callbacks)
                except Exception:
                    pass
                logging.info('Mostrando COMUNICACIÓN clientes (UI)')
            else:
                logging.error('No fue posible montar ClientesComunicacionView')

        except Exception:
            logging.exception('Error en show_comunicacion')

    def show_config(self):
        logging.info('TODO: Implementar show_config')

    def show_crear_cliente(self):
        """Mostrar UI de creación de cliente."""
        try:
            from kool_tpv.modulos.clientes.crear_cliente_ui import CrearClienteUI

            try:
                crear_ui = CrearClienteUI(self.central_area, db=self.db, cliente_id=None, module_name='clientes')
                if self.set_central_content(crear_ui):
                    self.actualizar_ruta('CLIENTES / NUEVO', callbacks=self.breadcrumb_callbacks)
                logging.info('Abriendo crear cliente...')
            except Exception:
                logging.exception('Error instanciando CrearClienteUI')
        except Exception:
            logging.exception('Error abriendo crear cliente')

    def show_editar_cliente(self, cliente_id):
        """Mostrar ficha de cliente en modo edición.

        Args:
            cliente_id: ID del cliente a editar
        """
        try:
            from kool_tpv.modulos.clientes.crear_cliente_ui import CrearClienteUI

            try:
                editar_ui = CrearClienteUI(self.central_area, db=self.db, cliente_id=cliente_id, module_name='clientes')
                if self.set_central_content(editar_ui):
                    self.actualizar_ruta('CLIENTES / EDITAR', callbacks=self.breadcrumb_callbacks)
                logging.info(f'Abriendo edición cliente {cliente_id}...')
            except Exception:
                logging.exception(f'Error instanciando CrearClienteUI para edición {cliente_id}')
        except Exception:
            logging.exception('Error abriendo edición cliente')
