"""
Custom Dialog helper para diálogos modales con branding corporativo.

Soporta 4 tipos: success, error, warning, info
con iconos temáticos D&D y colores apropiados.
"""
import customtkinter as ctk
from pathlib import Path
from PIL import Image
import logging


class CustomDialog(ctk.CTkToplevel):
    """Diálogo modal personalizado con iconos y colores por tipo."""

    # Colores por tipo
    COLORS = {
        'success': {'bg': '#2ecc71', 'hover': '#27ae60'},
        'error': {'bg': '#e74c3c', 'hover': '#c0392b'},
        'warning': {'bg': '#f39c12', 'hover': '#d68910'},
        'info': {'bg': '#3498db', 'hover': '#2980b9'}
    }

    def __init__(self, parent, tipo='info', titulo='', mensaje='', btn_text='Aceptar', callback=None):
        """
        Args:
            parent: Ventana padre
            tipo: 'success', 'error', 'warning', 'info'
            titulo: Título del diálogo
            mensaje: Mensaje a mostrar
            btn_text: Texto del botón
            callback: Función a ejecutar al cerrar (opcional)
        """
        super().__init__(parent)

        self.callback = callback
        self.tipo = tipo if tipo in self.COLORS else 'info'

        # Configurar ventana
        self.title(titulo)
        self.geometry("500x350")
        self.resizable(False, False)
        # Color de fondo según tipo
        colors = self.COLORS[self.tipo]
        try:
            self.configure(fg_color='#2b2b2b')
        except Exception:
            pass

        # Prepare window hidden so we can set geometry before mapping
        try:
            self.withdraw()
        except Exception:
            pass

        # Modal (set transient while hidden)
        try:
            self.transient(parent)
        except Exception:
            pass

        # Compute centered geometry relative to parent when possible, otherwise screen-center
        try:
            self.update_idletasks()
            w, h = 500, 350
            if parent is not None and getattr(parent, 'winfo_ismapped', None) and parent.winfo_ismapped():
                try:
                    parent.update_idletasks()
                    px = parent.winfo_rootx()
                    py = parent.winfo_rooty()
                    pw = parent.winfo_width() or parent.winfo_reqwidth()
                    ph = parent.winfo_height() or parent.winfo_reqheight()
                    x = px + max(0, (pw - w) // 2)
                    y = py + max(0, (ph - h) // 2)
                except Exception:
                    x = (self.winfo_screenwidth() // 2) - (w // 2)
                    y = (self.winfo_screenheight() // 2) - (h // 2)
            else:
                x = (self.winfo_screenwidth() // 2) - (w // 2)
                y = (self.winfo_screenheight() // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        # Show window immediately (no animation) and then grab focus
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

        self._crear_contenido(titulo, mensaje, btn_text)

        # Bind Escape y Enter
        self.bind('<Escape>', lambda e: self._on_close())
        self.bind('<Return>', lambda e: self._on_close())

        # Foco en el botón (sin delay)
        try:
            self.btn.focus_set()
        except Exception:
            pass

    def _cargar_icono(self):
        """Cargar icono según tipo."""
        try:
            base = Path(__file__).resolve().parents[1]  # kool_tpv/
            icons_dir = base / "assets" / "dialogs"
            preferred = icons_dir / f"dialog_{self.tipo}.png"

            tried = []
            # Try preferred
            tried.append(preferred)
            if not preferred.exists():
                # fallback to a generic warning/error icon
                fallback = icons_dir / "dialog_error.png"
                tried.append(fallback)

            for p in tried:
                try:
                    if p.exists():
                        logging.info(f'Loading dialog icon: {p}')
                        img = Image.open(p)
                        img = img.resize((96, 96), Image.LANCZOS)
                        return ctk.CTkImage(light_image=img, dark_image=img, size=(96, 96))
                except Exception:
                    logging.exception(f'Error cargando icono desde {p}')
        except Exception:
            logging.exception(f'Error cargando icono dialog_{self.tipo}.png')

        return None

    def _crear_contenido(self, titulo, mensaje, btn_text):
        """Crear widgets del diálogo."""
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(0, 10))

        # Título
        if titulo:
            titulo_label = ctk.CTkLabel(
                main_frame,
                text=titulo,
                font=('Roboto-Bold', 30),
                text_color='#FFFFFF'
            )
            titulo_label.pack(pady=(10, 15))

        # Mensaje
        mensaje_label = ctk.CTkLabel(
            main_frame,
            text=mensaje,
            font=('Roboto-Regular', 24),
            text_color='#DDDDDD',
            wraplength=450,
            justify='center'
        )
        mensaje_label.pack(pady=(0, 25))

        # Botón
        colors = self.COLORS[self.tipo]
        self.btn = ctk.CTkButton(
            main_frame,
            text=btn_text,
            command=self._on_close,
            fg_color=colors['bg'],
            hover_color=colors['hover'],
            font=('Roboto-SemiBold', 20),
            width=160,
            height=50,
            corner_radius=10
        )
        self.btn.pack()

    def _on_close(self):
        """Cerrar diálogo y ejecutar callback si existe."""
        try:
            if self.callback and callable(self.callback):
                self.callback()
        except Exception:
            logging.exception('Error ejecutando callback de CustomDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()


def show_success(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de éxito."""
    CustomDialog(parent, tipo='success', titulo=titulo, mensaje=mensaje, callback=callback)


def show_error(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de error."""
    CustomDialog(parent, tipo='error', titulo=titulo, mensaje=mensaje, callback=callback)


def show_warning(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de advertencia."""
    CustomDialog(parent, tipo='warning', titulo=titulo, mensaje=mensaje, callback=callback)


def show_info(parent, titulo, mensaje, callback=None):
    """Mostrar diálogo de información."""
    CustomDialog(parent, tipo='info', titulo=titulo, mensaje=mensaje, callback=callback)


class CustomInputDialog(ctk.CTkToplevel):
    """Diálogo de entrada personalizado con icono y validación."""

    def __init__(self, parent, tipo='success', titulo='', mensaje='', valor_defecto='', callback=None):
        """
        Args:
            parent: Ventana padre
            tipo: tipo de icono ('success' recomendado para tesoro)
            titulo: Título del diálogo
            mensaje: Mensaje/pregunta
            valor_defecto: Valor inicial del campo
            callback: Función a ejecutar al aceptar (recibe valor como arg)
        """
        super().__init__(parent)

        self.callback = callback
        self.tipo = tipo if tipo in CustomDialog.COLORS else 'success'
        self.result = None

        # Configurar ventana
        self.title(titulo)
        self.geometry("500x400")
        self.resizable(False, False)
        try:
            self.configure(fg_color='#2b2b2b')
        except Exception:
            pass

        # Prepare window hidden so we can set geometry before mapping
        try:
            self.withdraw()
        except Exception:
            pass
        try:
            self.transient(parent)
        except Exception:
            pass

        # Compute centered geometry relative to parent when possible
        try:
            self.update_idletasks()
            w, h = 500, 400
            if parent is not None and getattr(parent, 'winfo_ismapped', None) and parent.winfo_ismapped():
                try:
                    parent.update_idletasks()
                    px = parent.winfo_rootx()
                    py = parent.winfo_rooty()
                    pw = parent.winfo_width() or parent.winfo_reqwidth()
                    ph = parent.winfo_height() or parent.winfo_reqheight()
                    x = px + max(0, (pw - w) // 2)
                    y = py + max(0, (ph - h) // 2)
                except Exception:
                    x = (self.winfo_screenwidth() // 2) - (w // 2)
                    y = (self.winfo_screenheight() // 2) - (h // 2)
            else:
                x = (self.winfo_screenwidth() // 2) - (w // 2)
                y = (self.winfo_screenheight() // 2) - (h // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        # Show immediately and grab
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            self.update_idletasks()
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass

        self._crear_contenido(titulo, mensaje, valor_defecto)

        # Bind Escape (cancelar)
        self.bind('<Escape>', lambda e: self._on_cancel())
        # Bind Enter (aceptar)
        self.bind('<Return>', lambda e: self._on_accept())

        # Foco en el entry (sin delay)
        try:
            self.entry.focus_set()
        except Exception:
            pass

    def _cargar_icono(self):
        """Cargar icono según tipo."""
        try:
            base = Path(__file__).resolve().parents[1]  # kool_tpv/
            icon_path = base / "assets" / "dialogs" / f"dialog_{self.tipo}.png"

            if icon_path.exists():
                img = Image.open(icon_path)
                img = img.resize((96, 96), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(96, 96))
        except Exception:
            logging.exception(f'Error cargando icono dialog_{self.tipo}.png en InputDialog')

        return None

    def _crear_contenido(self, titulo, mensaje, valor_defecto):
        """Crear widgets del diálogo."""
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Icono
        icon = self._cargar_icono()
        if icon:
            icon_label = ctk.CTkLabel(main_frame, image=icon, text='')
            icon_label.pack(pady=(10, 15))

        # Título
        if titulo:
            titulo_label = ctk.CTkLabel(
                main_frame,
                text=titulo,
                font=('Roboto-Bold', 30),
                text_color='#FFFFFF'
            )
            titulo_label.pack(pady=(0, 15))

        # Mensaje
        if mensaje:
            mensaje_label = ctk.CTkLabel(
                main_frame,
                text=mensaje,
                font=('Roboto-Regular', 24),
                text_color='#DDDDDD',
                wraplength=450,
                justify='center'
            )
            mensaje_label.pack(pady=(0, 20))

        # Entry (campo de entrada)
        self.entry = ctk.CTkEntry(
            main_frame,
            width=300,
            height=50,
            font=('Roboto-Regular', 24),
            justify='center'
        )
        self.entry.pack(pady=(0, 25))
        if valor_defecto:
            self.entry.insert(0, str(valor_defecto))
            self.entry.select_range(0, 'end')

        # Frame para botones
        btn_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        btn_frame.pack()

        # Botón Cancelar
        colors_cancel = {'bg': '#7f8c8d', 'hover': '#95a5a6'}
        btn_cancel = ctk.CTkButton(
            btn_frame,
            text='Cancelar',
            command=self._on_cancel,
            fg_color=colors_cancel['bg'],
            hover_color=colors_cancel['hover'],
            font=('Roboto-SemiBold', 20),
            width=140,
            height=50,
            corner_radius=10
        )
        btn_cancel.pack(side='left', padx=(0, 10))

        # Botón Aceptar
        colors_accept = CustomDialog.COLORS[self.tipo]
        btn_accept = ctk.CTkButton(
            btn_frame,
            text='Aceptar',
            command=self._on_accept,
            fg_color=colors_accept['bg'],
            hover_color=colors_accept['hover'],
            font=('Roboto-SemiBold', 20),
            width=140,
            height=50,
            corner_radius=10
        )
        btn_accept.pack(side='left')
        self.btn = btn_accept  # guardar referencia para focus

    def _on_accept(self):
        """Aceptar: ejecutar callback con el valor ingresado."""
        valor = self.entry.get().strip()
        self.result = valor
        try:
            if self.callback and callable(self.callback):
                self.callback(valor)
        except Exception:
            logging.exception('Error ejecutando callback de CustomInputDialog')
        finally:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()

    def _on_cancel(self):
        """Cancelar: cerrar sin ejecutar callback."""
        self.result = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def get_input(self):
        """Esperar a que el diálogo se cierre y devolver el resultado.

        Usa wait_window para bloquear hasta que el usuario cierre.
        """
        self.wait_window()
        return self.result


def show_input_dialog(parent, titulo, mensaje, tipo='success', valor_defecto='', callback=None):
    """Mostrar diálogo de entrada y devolver valor ingresado o None si canceló."""
    dialog = CustomInputDialog(parent, tipo=tipo, titulo=titulo, mensaje=mensaje, valor_defecto=valor_defecto, callback=callback)
    return dialog.get_input()


def show_text_viewer(parent, titulo, texto, width=600, height=800, callback=None):
    """Helper que muestra TextViewDialog del módulo `textview_dialog`.

    Esto mantiene compatibilidad con llamadas previas a `show_text_viewer`
    importando desde `kool_tpv.utils.custom_dialog`.
    """
    try:
        from kool_tpv.utils.textview_dialog import show_text_viewer as _show
        _show(parent, titulo, texto, width=width, height=height, callback=callback)
    except Exception:
        logging.exception('Error delegando a textview_dialog.show_text_viewer')
