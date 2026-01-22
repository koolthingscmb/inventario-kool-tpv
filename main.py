import customtkinter as ctk
import os
import sys
import logging

# ensure working directory is project root so relative DB paths work consistently
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

LOG_FILE = os.path.join(os.getcwd(), "kool_tpv.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s: %(message)s")
logging.info("Arrancando KOOL_TPV - PID: %s", os.getpid())
print("Arrancando KOOL_TPV - PID:", os.getpid())

# --- IMPORTACIONES ACTUALIZADAS (NUEVA ESTRUCTURA) ---
from modulos.inicio.ui_inicio import PantallaInicio
from modulos.tpv.ui_ventas import CajaVentas
from modulos.almacen.ui_almacen import PantallaGestionArticulos
from modulos.almacen.articulos.ui_crear_producto import PantallaCrearProducto 
from modulos.almacen.articulos.todos_articulos import TodosArticulos

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppTPV(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KOOL THINGS - Sistema Modular")
        self.geometry("1024x768")
        # flag: imprimir ticket al finalizar venta (por defecto activado)
        self.imprimir_tickets_enabled = True

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)

        self.mostrar_inicio()

    def limpiar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- NAVEGACIÓN ---
    def mostrar_inicio(self):
        self.limpiar_container()
        PantallaInicio(self.container, self)

    def mostrar_ventas(self):
        self.limpiar_container()
        CajaVentas(self.container, self) 
    
    def mostrar_crear_producto(self, producto_id=None):
        self.limpiar_container()
        PantallaCrearProducto(self.container, self, producto_id)

    def mostrar_todos_articulos(self, categoria=None):
        # Guardar última categoría solicitada para que el inicio pueda restaurar estado
        self.ultima_categoria_seleccionada = categoria
        self.limpiar_container()
        TodosArticulos(self.container, self, categoria)

    def mostrar_tickets(self, fecha=None):
        """
        Mostrar pantalla de tickets. Si `fecha` proporcionada -> abrir página de ese día.
        """
        try:
            from modulos.tpv.ui_tickets import TicketsView
            self.limpiar_container()
            TicketsView(self.container, self, fecha)
        except Exception:
            # si falla la importación o la vista, volver al inicio suavemente
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_clientes(self):
        """Mostrar la vista de gestión de clientes (esquelética)."""
        try:
            from modulos.clientes.ui_gestion_clientes import GestionClientesView
            self.limpiar_container()
            GestionClientesView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_gestion_clientes(self):
        """Mostrar la vista de gestión de clientes (invocado desde el submenú)."""
        try:
            from modulos.clientes.ui_gestion_clientes import GestionClientesView
            self.limpiar_container()
            GestionClientesView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_cierre_caja(self):
        """Mostrar la vista de cierre de caja (admin)."""
        try:
            from modulos.tpv.ui_cierre_caja import CierreCajaView
            self.limpiar_container()
            CierreCajaView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_historico_cierres(self):
        """Mostrar la vista de histórico de cierres."""
        try:
            from modulos.tpv.ui_historico_cierres import HistoricoCierresView
            self.limpiar_container()
            HistoricoCierresView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def toggle_imprimir_tickets(self):
        """
        Alterna la opción de imprimir tickets al finalizar venta.
        """
        try:
            self.imprimir_tickets_enabled = not getattr(self, 'imprimir_tickets_enabled', False)
            logging.info("Imprimir tickets: %s", self.imprimir_tickets_enabled)
        except Exception:
            pass

    def mostrar_almacen_antiguo(self):
        self.limpiar_container()
        PantallaGestionArticulos(self.container, self)

    def mostrar_submenu_almacen(self):
        # Lógica para volver al submenú específico
        # Volver al inicio y llamar a los hooks si existen, de forma segura
        self.mostrar_inicio()
        hijos = self.container.winfo_children()
        if not hijos:
            return
        pantalla_actual = hijos[0]
        if hasattr(pantalla_actual, 'mostrar_submenu_almacen'):
            try:
                pantalla_actual.mostrar_submenu_almacen()
            except Exception:
                pass
        if hasattr(pantalla_actual, 'mostrar_opciones_articulos'):
            try:
                pantalla_actual.mostrar_opciones_articulos()
            except Exception:
                pass

if __name__ == "__main__":
    app = AppTPV()
    app.mainloop()