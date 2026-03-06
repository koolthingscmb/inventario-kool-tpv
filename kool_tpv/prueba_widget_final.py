import sys
import os
import customtkinter as ctk
from pathlib import Path
import logging

# --- CORRECCIÓN DE RUTAS (Para que Python encuentre tus carpetas) ---
# Esto soluciona el error "ModuleNotFoundError"
current_dir = os.path.dirname(os.path.abspath(__file__)) # Carpeta actual (kool_tpv)
parent_dir = os.path.dirname(current_dir) # Carpeta superior (KOOL_TPV_V2)
sys.path.append(parent_dir) # Añadimos la superior para poder importar 'kool_tpv'

# --- IMPORTS DEL PROYECTO ---
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
from kool_tpv.utils.keyboard_manager import KeyboardManager
from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito

# AQUÍ ESTÁ LA LÍNEA QUE ME PEDÍAS (Ruta correcta a 'actions')
from kool_tpv.modulos.tpv.actions.buscar_articulo_widget import BuscarArticuloWidget

# Configurar log básico
logging.basicConfig(level=logging.INFO)

class PruebaRealWidget(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de ventana
        self.geometry("1600x900")
        self.title("PRUEBA FINAL: Widget Buscador + Carrito")
        ctk.set_appearance_mode("Dark")

        # 1. BASE DE DATOS
        # Buscamos la BD dentro de kool_tpv/base_datos/
        db_path = Path(current_dir) / "base_datos" / "kool_bd.db"
        print(f"Conectando a BD en: {db_path}")

        self.db = Database(str(db_path))
        self.db.connect()

        # 2. SERVICIOS
        self.carrito_service = CarritoService()
        # El KeyboardManager necesita la ventana principal (self)
        self.keyboard_manager = KeyboardManager(self) 

        # 3. LAYOUT (Izquierda y Derecha)

        # Panel Derecho (Para el Ticket)
        self.right_panel = ctk.CTkFrame(self, width=520, fg_color="#1a1a1a")
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False) # Fijo

        # Panel Izquierdo (Para el Buscador)
        self.left_panel = ctk.CTkFrame(self, fg_color="#222831")
        self.left_panel.pack(side="left", fill="both", expand=True)

        # 4. COMPONENTES VISUALES

        # A) El Ticket (A la derecha)
        self.ticket = TicketCarrito(
            self.right_panel,
            carrito_service=self.carrito_service,
            keyboard_manager=self.keyboard_manager
        )
        self.ticket.pack(fill="both", expand=True)

        # B) Tu Nuevo Widget Buscador (A la izquierda)
        self.buscador = BuscarArticuloWidget(
            parent=self.left_panel,       
            db=self.db,                   
            carrito_service=self.carrito_service, 

            # Cuando se añada algo, actualizamos el ticket
            on_add_callback=self.ticket.update_carrito, 

            # Botón Volver (solo imprime mensaje)
            on_close_callback=self.cerrar_prueba
        )
        self.buscador.pack(fill="both", expand=True)

    def cerrar_prueba(self):
        print("Botón VOLVER pulsado")

if __name__ == "__main__":
    app = PruebaRealWidget()
    app.mainloop()