"""
EmergenciaProductoUI - Diálogo de alta rápida para productos no encontrados.
Permite ingresar Nombre y PVP de forma rápida para no detener la venta.
"""
import customtkinter as ctk
import logging
from decimal import Decimal
from kool_tpv.utils.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)

class EmergenciaProductoUI(BaseDialog):
    """Diálogo para creación rápida de productos (Alta Rápida)."""

    def __init__(self, parent, ean: str, callback=None):
        super().__init__(parent, tipo='info', titulo='ALTA RÁPIDA DE PRODUCTO', callback=callback)
        self.ean = ean
        self.result = None

        # Configuración de geometría específica para este diálogo
        self.geometry(f"500x450")

        self._crear_contenido()

        # Bindings
        self.bind('<Escape>', lambda e: self._on_cancel())
        # El primer campo (Nombre) pasa el foco al segundo (PVP) con Return
        self.entry_nombre.bind('<Return>', lambda e: self.entry_pvp.focus_set())
        # El segundo campo (PVP) acepta el diálogo
        self.entry_pvp.bind('<Return>', lambda e: self._on_accept())
        self.entry_pvp.bind('<KP_Enter>', lambda e: self._on_accept())

        # Foco inicial en el nombre (o en PVP si el nombre ya está bien)
        self.after(100, lambda: self.entry_nombre.focus_force())

    def _crear_contenido(self):
        """Construye la interfaz del diálogo."""
        # Barra de título (ya creada por BaseDialog si se llama a _crear_barra_titulo)
        # Pero super().__init__ ya hace gran parte del setup.
        
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True)

        # Barra de título con icono
        content_frame = self._crear_barra_titulo(main_frame, "ALTA RÁPIDA")

        # Contenedor con padding
        padding_x = 30
        padding_y = 20
        wrapper = ctk.CTkFrame(content_frame, fg_color='transparent')
        wrapper.pack(fill='both', expand=True, padx=padding_x, pady=padding_y)

        # 1. EAN (Solo lectura)
        ctk.CTkLabel(wrapper, text="EAN / CÓDIGO:", font=('Helvetica', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        self.lbl_ean = ctk.CTkLabel(wrapper, text=self.ean, font=('Helvetica', 16, 'bold'), text_color="#00FF00")
        self.lbl_ean.pack(anchor='w', pady=(0, 20))

        # 2. NOMBRE
        ctk.CTkLabel(wrapper, text="NOMBRE DEL PRODUCTO:", font=('Helvetica', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        self.entry_nombre = ctk.CTkEntry(wrapper, width=400, height=40, font=('Helvetica', 14), placeholder_text="Nombre descriptivo...")
        self.entry_nombre.pack(fill='x', pady=(0, 20))
        self.entry_nombre.insert(0, f"PRODUCTO PENDIENTE {self.ean}")
        self.entry_nombre.select_range(0, 'end')

        # 3. PVP
        ctk.CTkLabel(wrapper, text="PVP (€):", font=('Helvetica', 12, 'bold')).pack(anchor='w', pady=(0, 5))
        self.entry_pvp = ctk.CTkEntry(wrapper, width=150, height=45, font=('Helvetica', 24, 'bold'), justify='center', placeholder_text="0.00")
        self.entry_pvp.pack(anchor='w', pady=(0, 20))

        # Botones (Confirmar/Cancelar)
        self._crear_botones(content_frame, btn_text='GUARDAR Y AÑADIR', confirm=True)

    def _on_accept(self):
        """Valida y guarda los datos."""
        nombre = self.entry_nombre.get().strip()
        pvp_str = self.entry_pvp.get().replace(',', '.').strip()

        if not pvp_str:
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self, "DEBES INTRODUCIR UN PRECIO", tipo='error')
            self.entry_pvp.focus_set()
            return

        try:
            pvp = Decimal(pvp_str)
            if pvp < 0:
                raise ValueError()
        except Exception:
            from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
            ToastWidget.show(self, "PRECIO INVÁLIDO", tipo='error')
            self.entry_pvp.focus_set()
            return

        # Resultado para el callback
        self.result = {
            'nombre': nombre if nombre else f"PRODUCTO PENDIENTE {self.ean}",
            'pvp': pvp,
            'ean': self.ean
        }

        self._ejecutar_callback(self.result)
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self._ejecutar_callback(None)
        self.destroy()

    def _ejecutar_callback(self, result):
        if self.callback and callable(self.callback):
            self.callback(result)
