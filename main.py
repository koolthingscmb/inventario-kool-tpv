import customtkinter as ctk
import sys
import logging
import os
from kool_tpv.base_datos.db_wrapper import Database

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
        self.base_font = ("Arial", 18)
        self.button_font = ("Arial", 24, "bold")
        self.tpv_font = ("Arial", 60, "bold")

        # Configuración de la ventana principal
        self.title("Kool TPV")
        # Tamaño dinámico según pantalla
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        self.geometry(f"{width}x{height}")
        self.minsize(1024, 768)
        try:
            self.state('zoomed')
        except Exception:
            pass
        # Fondo oscuro
        try:
            self.configure(bg="#222831")
        except Exception:
            pass

        # Inicializar y conectar base de datos
        # Ruta al archivo kool_bd.db dentro del paquete `kool_tpv/base_datos`
        project_root = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(project_root, "kool_tpv", "base_datos", "kool_bd.db")
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

        # Botón de apagar/volver atrás (más cuadrado y símbolo grande)
        power_btn_kwargs = dict(
            master=self.nav_frame,
            fg_color="#FF0000",
            hover_color=HOVER_COLOR,
            width=110,
            height=110,
            corner_radius=18,
            command=self.close_app,
        )

        # Intentar cargar imagen desde assets/power.png si existe (imagen más grande)
        power_image = None
        try:
            from PIL import Image
            icon_path = os.path.join("assets", "power.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).resize((96, 96))
                power_image = ctk.CTkImage(img)
        except Exception:
            power_image = None

        if power_image:
            self.power_button = ctk.CTkButton(image=power_image, **power_btn_kwargs)
        else:
            self.power_button = ctk.CTkButton(
                **power_btn_kwargs,
                text="⏻",
                font=("Arial", 75, "bold"),
                text_color="white",
            )

        self.power_button.pack(pady=(12, 20))

        # Preparar botón "PRINT ON" pero NO mostrarlo en la pantalla inicial.
        # Se mostrará únicamente cuando se cargue la vista TPV.
        try:
            self.print_on_button = ctk.CTkButton(
                master=self.nav_frame,
                text="PRINT ON",
                fg_color="#00BFFF",
                hover_color=HOVER_COLOR,
                text_color="black",
                font=("Arial", 12, "bold"),
                height=28,
            )
            # No hacer pack() aquí: se packeará al entrar en TPV
        except Exception:
            logging.exception("Error creando botón PRINT ON")

        # Botones de navegación (tamaño táctil y márgenes mayores)
        # TPV será más alto y con tipografía mayor
        self.create_nav_button("TPV", "#FF8C00", height=100, command=self.load_tpv, font=self.tpv_font)
        self.create_nav_button("ALMACÉN", "#32CD32", height=56)
        self.create_nav_button("CLIENTES", "#9ACD32", height=56)
        self.create_nav_button("INFORMES", "#FF1493", height=56)
        self.create_nav_button("SHOPIFY", "#1E90FF", height=56)
        self.create_nav_button("CONFIG", "#FF4500", height=56)

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
        btn_font = font or getattr(self, "button_font", ("Arial", 16, "bold"))
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
                    font=("Arial", 20),
                    text_color="white",
                )
                label.pack(expand=True)
        except Exception:
            logging.exception("Error cargando módulo TPV")
            # Fallback sencillo si hay algún error al importar/mostrar la vista
            label = ctk.CTkLabel(
                self.main_frame,
                text="Módulo TPV cargado correctamente",
                font=("Arial", 20),
                text_color="white",
            )
            label.pack(expand=True)

    def close_app(self):
        """Salir/volver atrás (actualmente solo cerrar).

        Si estamos dentro del módulo TPV, vuelve a la navegación principal
        en lugar de cerrar la app. En otro caso, cierra la aplicación.
        """

        # Si estamos en TPV, hacer teardown y volver a la navegación
        if getattr(self, "current_view", None) == "tpv":
            tpv = getattr(self, "tpv_view", None)
            if tpv is not None:
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
