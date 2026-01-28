import customtkinter as ctk
import os
import sys
import logging
import tkinter.messagebox as messagebox

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

LOG_FILE = os.path.join(os.getcwd(), "kool_tpv.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s: %(message)s")
logging.info("Arrancando KOOL_TPV - PID: %s", os.getpid())
print("Arrancando KOOL_TPV - PID:", os.getpid())

from modulos.inicio.ui_inicio import PantallaInicio
from modulos.tpv.ui_ventas import CajaVentas
from modulos.almacen.ui_almacen import PantallaGestionArticulos
from modulos.almacen.articulos.ui_crear_producto import PantallaCrearProducto
from modulos.almacen.articulos.todos_articulos import TodosArticulos
from modulos.clientes.ui_gestion_clientes import GestionClientesView
from modulos.configuracion.ui_config_fidelizacion import UIConfigFidelizacion as ConfigFidelizacionView
# Gestión de usuarios
from modulos.configuracion.ui_gestion_usuarios import GestionUsuariosView as UIGestionUsuarios

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppTPV(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KOOL THINGS - Sistema Modular")
        self.geometry("1024x768")
        self.imprimir_tickets_enabled = True
        # current authenticated user (set after login)
        self.usuario_actual = None
        # Flag de sesión: si True, permitir acceso al menú CONFIG sin pedir clave otra vez
        self.config_desbloqueado = False

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)

        self.mostrar_inicio()

    def limpiar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _get_current_user(self):
        """Return the currently identified user (prefer `usuario_actual` then `cajero_activo`)."""
        try:
            user = getattr(self, 'usuario_actual', None)
            if user:
                return user
        except Exception:
            pass
        try:
            return getattr(self, 'cajero_activo', None)
        except Exception:
            return None

    def verificar_permiso(self, permiso_necesario: str) -> bool:
        """Central permission check.

        If no `self.usuario_actual`, opens `LoginCajero` modal and waits.
        Returns True when the (possibly newly) authenticated user is allowed,
        otherwise shows an error/info and returns False.
        """
        try:
            # 1) If we already know who the user is, don't ask for password
            user = getattr(self, 'usuario_actual', None)

            # 2) If we don't know, prompt for login (blocking)
            if not user:
                try:
                    from modulos.configuracion.ui_login_cajero import LoginCajero
                    dlg = LoginCajero(self)
                    try:
                        self.wait_window(dlg)
                    except Exception:
                        pass
                    user = getattr(dlg, 'result', None)
                    if not user:
                        # login cancelled or failed
                        return False
                    # store session user (use DB-record dict returned by the dialog/service)
                    self.usuario_actual = user
                except Exception:
                    return False

            # 3) Permission check: admin always allowed
            try:
                is_admin = int(user.get('es_admin') or 0)
            except Exception:
                is_admin = 0
            if is_admin == 1:
                return True

            # 4) Non-admin: check requested permission flag on user record
            try:
                permiso = int(user.get(permiso_necesario) or 0)
            except Exception:
                permiso = 0
            if permiso == 1:
                return True

            # 5) Deny
            try:
                messagebox.showerror('Acceso Denegado', 'Tu usuario no tiene permiso para entrar aquí.')
            except Exception:
                pass
            return False
        except Exception:
            return False

    def mostrar_inicio(self):
        # Al navegar fuera de Configuración, volver a bloquear el acceso CONFIG
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
        self.limpiar_container()
        PantallaInicio(self.container, self)

    def mostrar_ventas(self):
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
        self.limpiar_container()
        CajaVentas(self.container, self)

    def mostrar_crear_producto(self, producto_id=None):
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
        self.limpiar_container()
        PantallaCrearProducto(self.container, self, producto_id)

    def mostrar_todos_articulos(self, categoria=None):
        self.ultima_categoria_seleccionada = categoria
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
        self.limpiar_container()
        TodosArticulos(self.container, self, categoria)

    def mostrar_tickets(self, fecha=None, retorno_historico=False):
        try:
            try:
                self.config_desbloqueado = False
            except Exception:
                pass
            from modulos.tpv.ui_tickets import TicketsView
            self.limpiar_container()
            TicketsView(self.container, self, fecha, retorno_historico)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_gestion_clientes(self):
        try:
            try:
                self.config_desbloqueado = False
            except Exception:
                pass
            print('DEBUG: Intentando mostrar clientes')
            self.limpiar_container()
            view = GestionClientesView(self.container, self)
            view.pack(fill="both", expand=True)
        except Exception:
            logging.exception("Error mostrando la vista de Gestión de Clientes")
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_gestion_usuarios(self):
        try:
            self.limpiar_container()
            view = UIGestionUsuarios(self.container, self)
            view.pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error mostrando la vista de Gestión de Usuarios')
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_config_fidelizacion(self):
        try:
            self.limpiar_container()
            view = ConfigFidelizacionView(self.container, self)
            view.pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error mostrando la vista de Configuración de Fidelización')
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_mantenimiento(self):
        try:
            self.limpiar_container()
            from modulos.configuracion.reiniciar.ui_mantenimiento import UIMantenimiento
            view = UIMantenimiento(self.container, self)
            view.pack(fill='both', expand=True)
        except Exception:
            logging.exception('Error mostrando la vista de Mantenimiento')
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def restaurar_inicio_submenu(self):
        """Called after mostrar_inicio to restore previous submenu if available."""
        try:
            prev = getattr(self, '_prev_inicio_submenu', None)
            hijos = self.container.winfo_children()
            if not hijos:
                return
            first = hijos[0]
            # only proceed if it's PantallaInicio
            try:
                from modulos.inicio.ui_inicio import PantallaInicio
                if not isinstance(first, PantallaInicio):
                    return
            except Exception:
                return

            if prev == 'almacen':
                try:
                    first.mostrar_submenu_almacen()
                except Exception:
                    pass
            elif prev == 'clientes':
                try:
                    first.mostrar_submenu_clientes()
                except Exception:
                    pass
            elif prev == 'shopify':
                try:
                    first.mostrar_submenu_shopify()
                except Exception:
                    pass
            elif prev == 'config':
                try:
                    first.mostrar_submenu_config()
                except Exception:
                    pass
            else:
                # no prev submenu recorded
                pass
        except Exception:
            pass

    def mostrar_clientes(self):
        try:
            try:
                self.config_desbloqueado = False
            except Exception:
                pass
            self.mostrar_gestion_clientes()
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_cierre_caja(self):
        try:
            try:
                self.config_desbloqueado = False
            except Exception:
                pass
            from modulos.tpv.ui_cierre_caja import CierreCajaView
            self.limpiar_container()
            CierreCajaView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def mostrar_historico_cierres(self):
        try:
            try:
                self.config_desbloqueado = False
            except Exception:
                pass
            from modulos.tpv.ui_historico_cierres import HistoricoCierresView
            self.limpiar_container()
            HistoricoCierresView(self.container, self)
        except Exception:
            try:
                self.mostrar_inicio()
            except Exception:
                pass

    def toggle_imprimir_tickets(self):
        try:
            self.imprimir_tickets_enabled = not getattr(self, 'imprimir_tickets_enabled', False)
            logging.info("Imprimir tickets: %s", self.imprimir_tickets_enabled)
        except Exception:
            pass

    def mostrar_almacen_antiguo(self):
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
        self.limpiar_container()
        PantallaGestionArticulos(self.container, self)

    def mostrar_submenu_almacen(self):
        try:
            self.config_desbloqueado = False
        except Exception:
            pass
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

    def volver_a_configuracion(self):
        """Muestra la pantalla de inicio y abre el submenú de CONFIGURACIÓN sin pedir la clave.

        Asume que `self.config_desbloqueado` ya está establecida en True por algún flujo previo
        (por ejemplo, tras validar el DialogoPassConfig). No pide contraseña aquí.
        """
        try:
            # Mostrar la pantalla de inicio
            self.mostrar_inicio()
        except Exception:
            pass

        # Buscar la instancia de PantallaInicio en el container y pedirle que muestre el submenu
        try:
            hijos = self.container.winfo_children()
            if not hijos:
                return
            first = hijos[0]
            try:
                from modulos.inicio.ui_inicio import PantallaInicio
                if isinstance(first, PantallaInicio):
                    try:
                        first.mostrar_submenu_config()
                    except Exception:
                        pass
            except Exception:
                # si no se puede importar o no coincide, no hacemos nada
                pass
        except Exception:
            pass


if __name__ == "__main__":
    app = AppTPV()
    app.mainloop()