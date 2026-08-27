import customtkinter as ctk
import logging
from kool_tpv.utils.widgets.ticket_display import TicketDisplay
from kool_tpv.modulos.impresion.impresora_service import ImpresoraService

logger = logging.getLogger(__name__)

class TicketDisplayDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, ticket_id, module_name='almacen'):
        super().__init__(parent)
        self.title(f"TICKET #{ticket_id}")
        self.geometry("450x700")
        
        # Hacerla modal
        self.transient(parent)
        self.grab_set()
        
        self.db = db
        self.ticket_id = ticket_id
        
        # Contenedor
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Visor
        self.display = TicketDisplay(self.container, module_name=module_name)
        self.display.pack(fill="both", expand=True)
        
        # Botón cerrar
        self.btn_close = ctk.CTkButton(
            self.container, 
            text="CERRAR", 
            command=self.destroy,
            fg_color="#333333",
            hover_color="#444444"
        )
        self.btn_close.pack(fill="x", pady=(10, 0))
        
        # Cargar contenido
        self._load_ticket()

    def _load_ticket(self):
        try:
            imp = ImpresoraService(db=self.db)
            content = imp.generar_ticket_desde_id(self.ticket_id)
            self.display.set_content(content)
        except Exception:
            logger.exception(f"Error cargando ticket {self.ticket_id} en dialog")
            self.display.set_content("Error al cargar el ticket.")

def show_ticket_display_dialog(parent, db, ticket_id, module_name='almacen'):
    """Helper para mostrar el ticket en un popup."""
    try:
        dialog = TicketDisplayDialog(parent, db, ticket_id, module_name)
        # No bloqueamos con wait_window para que el usuario pueda seguir viendo el historial 
        # pero al ser modal (grab_set) evita clicks fuera.
        return dialog
    except Exception:
        logger.exception("Error mostrando TicketDisplayDialog")
        return None
