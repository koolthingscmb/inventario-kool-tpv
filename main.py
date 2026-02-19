import customtkinter as ctk
import sys
import logging
import os
import json
from pathlib import Path
from typing import List, Dict
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.actions.buscar_articulo import BuscarArticuloPanel
from PIL import Image

# Hover color used across the UI (matches TPV 'BUSCAR ARTÍCULO' hover)
HOVER_COLOR = "#00A4DF"

# Asegurar carpeta de logs
os.makedirs("logs", exist_ok=True)

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/application.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Apariencia
        try:
            ctk.set_appearance_mode("dark")
        except Exception:
            pass

        # Tipografías configurables (modifica aquí si quieres tamaños distintos)
        # Usamos las familias Roboto provistas en assets-fonts: Roboto-Regular y Roboto-SemiBold
        self.base_font = ("Roboto-Regular", 18)
        self.button_font = ("Roboto-SemiBold", 24)
        self.tpv_font = ("Roboto-SemiBold", 60)

        # Configuración de la ventana principal
        self.title("Kool TPV")
        # Tamaño fijo para TPV profesional (25% más grande)
        self.geometry("1600x960")
        # Forzar aplicación de la geometría antes de mostrar (evita tamaño inicial diminuto)
        try:
            self.update_idletasks()
        except Exception:
            pass
        # Asegurar que no pueda reducirse por debajo de este tamaño
        try:
            self.minsize(1600, 960)
        except Exception:
            pass
        # No redimensionable
        self.resizable(False, False)
        # Fondo oscuro: asegurar tanto el CTk como el Tk nativo
        try:
            self.configure(fg_color="#222831")
            # Forzar también el fondo a nivel nativo Tkinter para evitar flashes
            try:
                self.config(background="#222831")
            except Exception:
                pass
        except Exception:
            try:
                self.configure(bg="#222831")
            except Exception:
                pass

        # Inicializar y conectar base de datos
        # Ruta al archivo kool_bd.db dentro del paquete `kool_tpv/base_datos`
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "kool_tpv", "base_datos", "kool_bd.db")
        # Ensure DB schema exists before connecting
        try:
            from kool_tpv.base_datos.db_init import initialize_database
            try:
                initialize_database(db_path)
            except Exception:
                logging.exception('initialize_database fallo; se continuará e intentará conectar de todas formas')
        except Exception:
            logging.exception('No se pudo importar initialize_database')

        self.db = Database(db_path)
        try:
            self.db.connect()
            logging.info("Conexión a la base de datos establecida con éxito.")
        except Exception as e:
            logging.error(f"Error en la conexión a la base de datos: {e}")
            self.db = None

        # Inicializar UI
        # Contenedor para referencias a botones de navegación
        self.nav_buttons = {}
        self.current_view = None
        self.tpv_view = None

        self.create_navigation()

        # Log de inicialización exitosa
        logging.info("Aplicación iniciada correctamente.")

    def create_navigation(self):
        # Frame lateral (barra de navegación)
        # Barra lateral más ancha para botones táctiles
        self.nav_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#393E46")
        self.nav_frame.pack(side="left", fill="y")
        self.nav_frame.pack_propagate(False)

        # Importar función global para el botón power/close
        try:
            from kool_tpv.utils.global_buttons import create_global_close_button
            self.power_button = create_global_close_button(self.nav_frame, command=self.close_app)
            if self.power_button is not None:
                try:
                    self.power_button.pack(pady=(12, 20))
                except Exception:
                    pass
        except Exception:
            logging.exception("Error creando botón global power desde utils.global_buttons")

        # Preparar botón "PRINT ON" pero NO mostrarlo en la pantalla inicial.
        # Se mostrará únicamente cuando se cargue la vista TPV.
        try:
            self.print_on_button = ctk.CTkButton(
                master=self.nav_frame,
                text="PRINT ON",
                fg_color="#00BFFF",
                hover_color=HOVER_COLOR,
                text_color="black",
                font=("Roboto-SemiBold", 12),
                height=28,
            )
            # No hacer pack() aquí: se packeará al entrar en TPV
        except Exception:
            logging.exception("Error creando botón PRINT ON")

        # Cargar configuración de botones del menú principal desde JSON
        try:
            base = Path(__file__).resolve().parents[0]
            cfg_file = base / "kool_tpv" / "config" / "buttons_config.json"
            main_menu: List[Dict] = []
            if cfg_file.exists():
                with cfg_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                main_menu = data.get("main_menu") or []

            if not main_menu:
                # Fallback a la configuración hardcoded anterior
                main_menu = [
                    {"text": "TPV", "color": "#FF8C00", "command": "load_tpv", "hover_color": None},
                    {"text": "ALMACÉN", "color": "#32CD32", "command": "open_almacen", "hover_color": None},
                    {"text": "CLIENTES", "color": "#9ACD32", "command": "open_clientes", "hover_color": None},
                    {"text": "INFORMES", "color": "#FF1493", "command": "open_informes", "hover_color": None},
                    {"text": "SHOPIFY", "color": "#1E90FF", "command": "open_shopify", "hover_color": None},
                    {"text": "CONFIG", "color": "#FF4500", "command": "open_config", "hover_color": None},
                ]

            # Import ButtonFactory lazily to avoid circular imports on startup
            try:
                from kool_tpv.modulos.tpv.tpv_view import ButtonFactory
            except Exception:
                ButtonFactory = None

            for item in main_menu:
                text = item.get("text") or item.get("label") or ""
                color = item.get("color", "#CCCCCC")
                hover = item.get("hover_color")
                cmd_name = (item.get("command") or "").strip()

                # map known commands to methods
                if cmd_name.lower() in ("tpv", "load_tpv", "load_tpv()"):
                    cmd = self.load_tpv
                elif cmd_name.lower() in ("open_almacen", "almacen", "open_almacen()"):
                    cmd = self.open_almacen
                elif cmd_name.lower() in ("open_clientes", "clientes", "open_clientes()"):
                    cmd = self.open_clientes
                else:
                    # default: log action
                    cmd = (lambda name=cmd_name or text: logging.info(f"Nav action: {name}"))

                # use ButtonFactory when available for consistent style
                try:
                    if ButtonFactory is not None:
                        btn = ButtonFactory.create_button(
                            parent=self.nav_frame,
                            text=text,
                            color=color,
                            hover_color=hover,
                            command=cmd,
                            font=self.tpv_font if text.upper() == "TPV" else self.button_font,
                            height=100 if text.upper() == "TPV" else 56,
                        )
                    else:
                        btn = self.create_nav_button(text, color, height=(100 if text.upper() == "TPV" else 56), command=cmd, font=(self.tpv_font if text.upper() == "TPV" else self.button_font))
                    btn.pack(pady=14, padx=20, fill="x")
                    try:
                        self.nav_buttons[text] = btn
                    except Exception:
                        pass
                except Exception:
                    logging.exception("Error creando botón del menú desde JSON")

        except Exception:
            logging.exception("Error cargando main_menu desde JSON")

        # Footer con versión
        footer = ctk.CTkLabel(self.nav_frame, text="KOOL TPV V1.0", text_color="white", font=self.base_font)
        footer.pack(side="bottom", pady=10)

        # Frame principal para cargar contenido dinámico (fondo oscuro)
        self.main_frame = ctk.CTkFrame(self, fg_color="#222831")
        self.main_frame.pack(side="right", fill="both", expand=True)

    def create_nav_button(self, text, color, height=56, command=None, font=None):
        """Función para crear botones de la navegación lateral.

        Args:
            text: Texto del botón.
            color: Color de fondo del botón.
            height: Altura del botón en píxeles (útil para pantallas táctiles).
            command: Función a ejecutar al pulsar.
        """
        btn_font = font or getattr(self, "button_font", ("Roboto-SemiBold", 16))
        btn = ctk.CTkButton(
            self.nav_frame,
            text=(text or "").upper(),
            fg_color=color,
            hover_color=HOVER_COLOR,
            text_color="black",
            font=btn_font,
            command=command,
            height=height,
        )
        btn.pack(pady=14, padx=20, fill="x")
        # Guardar referencia para poder ocultar/mostrar desde otras vistas
        try:
            self.nav_buttons[text] = btn
        except Exception:
            pass
        return btn

    def load_tpv(self):
        """Carga TPV en el main_frame (placeholder).

        Importa el módulo de vista `kool_tpv.modulos.tpv.tpv_view` sin crear
        elementos gráficos; muestra un placeholder indicando que el módulo
        se ha cargado correctamente.
        """
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        try:
            from kool_tpv.modulos.tpv.tpv_view import TpvView

            # Ocultar botones de navegación (mantener visible el power_button)
            try:
                for k, btn in list(self.nav_buttons.items()):
                    btn.pack_forget()
            except Exception:
                pass

            # Mostrar el botón PRINT ON solamente dentro de TPV
            try:
                if getattr(self, "print_on_button", None) is not None:
                    self.print_on_button.pack(pady=(0, 12))
            except Exception:
                logging.exception("Error mostrando PRINT ON en TPV")

            view = TpvView(self.main_frame, db=getattr(self, "db", None))
            # Guardar referencia para poder gestionar el teardown del reloj
            self.tpv_view = view
            self.current_view = "tpv"
            try:
                view.show()
            except Exception:
                logging.exception("Error mostrando TpvView")
                # fallback label below
                label = ctk.CTkLabel(
                    self.main_frame,
                    text="Módulo TPV cargado correctamente",
                    font=("Roboto-Regular", 20),
                    text_color="white",
                )
                label.pack(expand=True)
        except Exception:
            logging.exception("Error cargando módulo TPV")
            # Fallback sencillo si hay algún error al importar/mostrar la vista
            label = ctk.CTkLabel(
                self.main_frame,
                text="Módulo TPV cargado correctamente",
                font=("Roboto-Regular", 20),
                text_color="white",
            )
            label.pack(expand=True)

    def close_app(self):
        """Salir/volver atrás (actualmente solo cerrar).

        Si estamos dentro del módulo TPV, vuelve a la navegación principal
        en lugar de cerrar la app. En otro caso, cierra la aplicación.
        """

        # Si estamos en TPV, comprobar carrito antes de hacer teardown y volver a la navegación
        if getattr(self, "current_view", None) == "tpv":
            tpv = getattr(self, "tpv_view", None)
            # Si hay un TPV activo, revisar si el carrito contiene artículos
            if tpv is not None:
                try:
                    carrito = getattr(tpv, 'carrito_service', None)
                    if carrito is not None:
                        try:
                            # Preferir método is_empty si existe
                            if getattr(carrito, 'is_empty', None) and callable(carrito.is_empty):
                                empty = carrito.is_empty()
                            else:
                                try:
                                    empty = (carrito.get_item_count() == 0)
                                except Exception:
                                    empty = (len(carrito.get_items() or []) == 0)
                        except Exception:
                            empty = True

                        if not empty:
                            try:
                                from kool_tpv.utils.custom_dialog import show_error
                                show_error(self, 'Carrito no vacío', 'No se puede salir del TPV con artículos en el carrito. Finaliza la tarea.')
                            except Exception:
                                logging.exception('Error mostrando diálogo carrito no vacío')
                            return
                except Exception:
                    logging.exception('Error comprobando estado del carrito antes de cerrar TPV')

                try:
                    tpv.teardown()
                except Exception:
                    pass
                try:
                    del self.tpv_view
                except Exception:
                    pass

            try:
                for w in list(self.main_frame.winfo_children()):
                    try:
                        w.destroy()
                    except Exception:
                        pass
            except Exception:
                pass

            self.current_view = None

            # Restaurar botones de navegación
            try:
                # Ocultar el botón PRINT ON al salir del TPV
                try:
                    if getattr(self, "print_on_button", None) is not None:
                        self.print_on_button.pack_forget()
                except Exception:
                    pass

                for key, btn in list(self.nav_buttons.items()):
                    try:
                        btn.pack(pady=14, padx=20, fill="x")
                    except Exception:
                        pass
            except Exception:
                pass

            return

        # Si no estamos en TPV, cerrar conexión a BD y salir
        try:
            if getattr(self, "db", None):
                try:
                    self.db.close_connection()
                except Exception:
                    logging.exception("Error cerrando la conexión a la base de datos")
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

    def open_almacen(self):
        """Open Almacén module: hide main nav and main_frame, instantiate AlmacenView.

        The back callback destroys the almacen view and restores the original
        navigation and main frame packing.
        """
        try:
            # Hide existing navigation and main content
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            # Lazy import to avoid startup circular imports
            try:
                from kool_tpv.modulos.almacen.almacen_view import AlmacenView
            except Exception:
                logging.exception('Error importando AlmacenView')
                return

            # Instantiate almacen view attached to the root (self)
            try:
                self.almacen_view = AlmacenView(self, db=getattr(self, 'db', None))
            except Exception:
                logging.exception('Error instanciando AlmacenView')
                # restore UI
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            # Define back callback to destroy almacen view and restore frames
            def _on_back():
                try:
                    # Delegar a _on_power para verificar cambios sin guardar
                    if hasattr(self, 'almacen_view') and self.almacen_view:
                        try:
                            if not self.almacen_view._on_power():
                                return  # Usuario canceló, no proceder
                        except Exception:
                            logging.exception('Error llamando a almacen_view._on_power')
                            return

                    # Usuario aceptó o no hay cambios: limpiar referencias
                    try:
                        if getattr(self, 'almacen_view', None):
                            try:
                                del self.almacen_view
                            except Exception:
                                pass
                    except Exception:
                        logging.exception('Error limpiando almacen_view en _on_back')

                except Exception:
                    logging.exception('Error en callback de volver desde Almacen')

            # Bind power button in the almacen sidebar to act as 'back'
            try:
                if getattr(self, 'almacen_view', None) and getattr(self.almacen_view, 'power_button', None):
                    try:
                        self.almacen_view.power_button.configure(command=_on_back)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error en open_almacen')

    def open_clientes(self):
        """Open Clientes module: hide main nav and main_frame, instantiate ClientesView."""
        try:
            try:
                self.nav_frame.pack_forget()
            except Exception:
                pass
            try:
                self.main_frame.pack_forget()
            except Exception:
                pass

            try:
                from kool_tpv.modulos.clientes.clientes_view import ClientesView
            except Exception:
                logging.exception('Error importando ClientesView')
                return

            try:
                self.clientes_view = ClientesView(self, db=getattr(self, 'db', None))
            except Exception:
                logging.exception('Error instanciando ClientesView')
                try:
                    self.nav_frame.pack(side='left', fill='y')
                except Exception:
                    pass
                try:
                    self.main_frame.pack(side='right', fill='both', expand=True)
                except Exception:
                    pass
                return

            def _on_back_clientes():
                try:
                    if hasattr(self, 'clientes_view') and self.clientes_view:
                        if self.clientes_view._on_power():
                            try:
                                del self.clientes_view
                            except Exception:
                                pass
                except Exception:
                    logging.exception('Error en callback volver Clientes')

            try:
                if getattr(self, 'clientes_view', None) and getattr(self.clientes_view, 'power_button', None):
                    try:
                        self.clientes_view.power_button.configure(command=_on_back_clientes)
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logging.exception('Error abriendo clientes')


if __name__ == "__main__":
    app = App()
    app.mainloop()
