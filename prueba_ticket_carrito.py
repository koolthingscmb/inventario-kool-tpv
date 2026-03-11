import customtkinter as ctk
from pathlib import Path
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.modulos.tpv.carrito.carrito_service import CarritoService
from kool_tpv.utils.widgets.ticket_carrito import TicketCarrito
from kool_tpv.utils.keyboard_manager import KeyboardManager  # <--- IMPORTAR

# --- CONFIGURACIÓN ---
DB_PATH = Path(__file__).parent / "kool_tpv" / "base_datos" / "kool_bd.db"

class TestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1600x960")
        self.title("Test Ticket Real + BD")

        # 1. Gestor de teclado (PARA LAS FLECHAS)
        self.keyboard_manager = KeyboardManager(self)

        # 2. Conexión BD y Servicios
        self.db = Database(str(DB_PATH))
        self.db.connect()

        self.producto_service = ProductoService(self.db)
        self.carrito_service = CarritoService()

        # 3. Panel Derecho (Ticket)
        self.right_panel = ctk.CTkFrame(self, width=520, fg_color="#1a1a1a")
        self.right_panel.pack(side="right", fill="y")
        self.right_panel.pack_propagate(False) 

        # 4. Ticket (Pasamos keyboard_manager)
        self.ticket = TicketCarrito(
            self.right_panel, 
            carrito_service=self.carrito_service,
            keyboard_manager=self.keyboard_manager # <--- CONECTAR
        )
        self.ticket.pack(fill="both", expand=True)

        # 5. Panel Izquierdo (Botones de prueba)
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.left_panel, text="PRODUCTOS DE PRUEBA", font=("Arial", 20, "bold")).pack(pady=20)

        self._cargar_botones_productos()
        self._crear_botones_pago()

    def _cargar_botones_productos(self):
        """Crea botones para los primeros 10 productos de la BD."""
        productos = self.producto_service.listar_productos()[:10]

        for prod in productos:
            btn = ctk.CTkButton(
                self.left_panel,
                text=f"{prod['nombre']} ({prod['pvp']}€)",
                width=300,
                height=50,
                command=lambda p=prod: self._add_producto(p)
            )
            btn.pack(pady=5)

    def _add_producto(self, producto_data):
        self.carrito_service.add_item(producto_data)
        self.ticket.update_carrito()

    def _crear_botones_pago(self):
        frame_pagos = ctk.CTkFrame(self.left_panel)
        frame_pagos.pack(pady=20, fill="x")

        ctk.CTkLabel(frame_pagos, text="FORMAS DE PAGO", font=("Arial", 16, "bold")).pack()

        # DEFINIR CALLBACK DE PAGO
        def on_pago(datos):
            print(f"PAGO RECIBIDO: {datos}")
            lbl = ctk.CTkLabel(self, text="VENTA FINALIZADA", font=("Arial", 40), text_color="green")
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            self.after(2000, lbl.destroy)
            self.ticket.desactivar_pago()

        # Botones con callback
        ctk.CTkButton(frame_pagos, text="EFECTIVO", 
            command=lambda: self.ticket.activar_pago_efectivo(on_finalizar=on_pago)).pack(pady=5)

        ctk.CTkButton(frame_pagos, text="TARJETA", 
            command=lambda: self.ticket.activar_pago_tarjeta(on_finalizar=on_pago)).pack(pady=5)

        ctk.CTkButton(frame_pagos, text="WEB", 
            command=lambda: self.ticket.activar_pago_web(on_finalizar=on_pago)).pack(pady=5)

        ctk.CTkButton(frame_pagos, text="MULTI", 
            command=lambda: self.ticket.activar_pago_multi(on_finalizar=on_pago)).pack(pady=5)

        ctk.CTkButton(frame_pagos, text="CANCELAR PAGO", fg_color="red", command=self.ticket.desactivar_pago).pack(pady=10)

if __name__ == "__main__":
    app = TestApp()
    app.mainloop()