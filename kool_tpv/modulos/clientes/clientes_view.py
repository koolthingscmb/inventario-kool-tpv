"""Módulo Clientes - orchestrator."""
import logging
from kool_tpv.utils.templates.base_module_view import BaseModuleView


class ClientesView(BaseModuleView):
    """Vista principal del módulo Clientes."""

    def __init__(self, parent, db):
        super().__init__(parent, config_section='clientes')
        self.parent = parent
        self.db = db

        # Actualizar breadcrumb
        try:
            self.actualizar_ruta('CLIENTES')
        except Exception:
            pass

        logging.info('ClientesView inicializado')

    # Placeholders para botones (se implementarán después)
    def show_clientes(self):
        logging.info('TODO: Implementar show_clientes')

    def show_tops(self):
        logging.info('TODO: Implementar show_tops')

    def show_comunicacion(self):
        logging.info('TODO: Implementar show_comunicacion')

    def show_config(self):
        logging.info('TODO: Implementar show_config')

    def show_crear_cliente(self):
        logging.info('TODO: Implementar show_crear_cliente')
