"""
Widget Ticket Carrito - Interfaz visual del carrito TPV
Compuesto por Header (info + cliente), Cuerpo (NavList), Footer (totales + pago)
"""
import logging
from pathlib import Path
import json
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

from kool_tpv.utils.widgets.carrito_nav_list import CarritoNavList
from kool_tpv.utils.widgets.payment_controllers.payment_controller_simple import PaymentControllerSimple
from kool_tpv.utils.widgets.payment_controllers.payment_controller_efectivo import PaymentControllerEfectivo
from kool_tpv.utils.widgets.payment_controllers.payment_controller_multi import PaymentControllerMulti
from kool_tpv.utils.factories.button_factory import ButtonFactory

def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        base = Path(__file__).resolve().parents[2]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


class TicketCarrito(ctk.CTkFrame):
    """Widget completo del Ticket Carrito con Header/Cuerpo/Footer."""

    def __init__(
        self, 
        parent, 
        carrito_service=None,
        keyboard_manager=None,
        db=None,
        **kwargs
    ):
        # Cargar configs
        self.colors = load_config("colors_config.json")
        self.fonts = load_config("font_config.json")
        self.layout = load_config("layout_config.json")

        # Extraer configuraciones específicas
        self.ticket_colors = self.colors.get("tpv", {}).get("ticket_carrito", {})
        self.ticket_fonts = self.fonts.get("modules", {}).get("tpv", {}).get("ticket_carrito", {})
        self.ticket_layout = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {})

        # (debug prints removed)

        # Configurar frame principal
        width = self.ticket_layout.get("width", 420)
        bg = self.ticket_colors.get("body", {}).get("bg", "#000000")

        super().__init__(parent, width=width, fg_color=bg, **kwargs)
        self.pack_propagate(False)

        # Guardar referencias externas
        self.carrito_service = carrito_service
        # Exponer formatter local para uso en vistas (usa el del carrito_service si existe)
        try:
            self.formatter = getattr(self.carrito_service, 'formatter', None) if self.carrito_service is not None else None
            if self.formatter is None:
                from kool_tpv.utils.formatter_service import FormatterService
                self.formatter = FormatterService()
        except Exception:
            self.formatter = None
        self.keyboard_manager = keyboard_manager
        self.db = db
        # Payment controller activo
        self.active_payment_controller = None
        self.active_payment_type = None

        # Crear estructura
        self._create_header()
        self._create_body()
        self._create_footer()
        self._start_clock()

        logger.info("TicketCarrito inicializado")

    def _calculate_header_height(self):
        """Calcular altura dinámica del header basada en config."""
        try:
            header_cfg = self.ticket_layout.get("header", {})

            # Paddings verticales
            pad_top = header_cfg.get("padding_vertical_top", 8)
            pad_bottom = header_cfg.get("padding_vertical_bottom", 4)

            # Info section
            info_cfg = header_cfg.get("info_section", {})
            info_height = info_cfg.get("label_height", 20)
            info_spacing = info_cfg.get("spacing_top", 4) + info_cfg.get("spacing_bottom", 4)

            # Cliente section
            cliente_cfg = header_cfg.get("cliente_section", {})
            cliente_height = cliente_cfg.get("label_height", 24)
            cliente_spacing = cliente_cfg.get("spacing_top", 4) + cliente_cfg.get("spacing_bottom", 6)

            # Ahora hay DOS líneas de cliente
            cliente_total_height = (cliente_height * 2) + cliente_spacing

            # Calcular total
            total_height = (
                pad_top +
                info_spacing + info_height +
                cliente_total_height +
                pad_bottom
            )

            return total_height

        except Exception:
            logger.exception("Error calculando altura header")
            return 120

    def _create_header(self):
        """Crear zona de header (info general + cliente)."""
        header_cfg = self.ticket_colors.get("header", {})
        header_cfg_layout = self.ticket_layout.get("header", {})

        header_height = self._calculate_header_height()

        self.header_frame = ctk.CTkFrame(
            self,
            height=header_height,
            fg_color=header_cfg.get("bg", "#000000")
        )
        self.header_frame.pack(
            fill="x",
            padx=header_cfg_layout.get("padding_horizontal", 12),
            pady=(
                header_cfg_layout.get("padding_vertical_top", 12),
                header_cfg_layout.get("padding_vertical_bottom", 0)
            )
        )
        self.header_frame.pack_propagate(False)

        # Zona 1: Info general (hora/fecha + cajero)
        self._create_info_section()

        # Zona 2: Cliente (se mostrará cuando haya cliente)
        self._create_cliente_section()

    def _create_info_section(self):
        """Crear sección de información general (hora/cajero)."""
        info_font_cfg = self.ticket_fonts.get("header_info", {})
        info_font = (
            info_font_cfg.get("family", "Courier New"),
            info_font_cfg.get("size", 14),
            info_font_cfg.get("weight", "normal")
        )
        text_color = self.ticket_colors.get("header", {}).get("text_info", "#00FF00")

        header_layout = self.ticket_layout.get("header", {})
        info_cfg = header_layout.get("info_section", {})

        spacing_top = info_cfg.get("spacing_top", 4)
        spacing_bottom = info_cfg.get("spacing_bottom", 4)
        label_height = info_cfg.get("label_height", 20)
        pad_h = header_layout.get("padding_horizontal", 12)

        info_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        info_container.pack(
            fill="x",
            pady=(spacing_top, spacing_bottom)
        )

        # Hora/Fecha (se actualizará dinámicamente)
        self.hora_label = ctk.CTkLabel(
            info_container,
            text="--:--:--",
            font=info_font,
            text_color=text_color,
            anchor="w",
            height=label_height
        )
        self.hora_label.pack(side="left", padx=(pad_h, 0))

        # Cajero
        self.cajero_label = ctk.CTkLabel(
            info_container,
            text="Cajero: ---",
            font=info_font,
            text_color=text_color,
            anchor="e",
            height=label_height
        )
        self.cajero_label.pack(side="right", padx=(0, pad_h))

    def _create_cliente_section(self):
        """Crear sección de cliente (nombre + nivel + tesoro + varita)."""
        cliente_font_cfg = self.ticket_fonts.get("header_cliente", {})
        cliente_font = (
            cliente_font_cfg.get("family", "Courier New"),
            cliente_font_cfg.get("size", 16),
            cliente_font_cfg.get("weight", "bold")
        )
        text_color = self.ticket_colors.get("header", {}).get("text_cliente", "#FFD700")
        header_layout = self.ticket_layout.get("header", {})
        cliente_cfg = header_layout.get("cliente_section", {})

        spacing_top = cliente_cfg.get("spacing_top", 4)
        spacing_bottom = cliente_cfg.get("spacing_bottom", 6)
        label_height = cliente_cfg.get("label_height", 24)
        pad_h = header_layout.get("padding_horizontal", 12)

        # Cargar iconos desde assets (si están disponibles)
        from PIL import Image
        base_assets = Path(__file__).resolve().parents[2] / "assets"

        try:
            user_img = Image.open(base_assets / "user_icon.png").resize((20, 20), Image.LANCZOS)
            self._user_icon = ctk.CTkImage(user_img, size=(20, 20))
        except Exception:
            self._user_icon = None

        try:
            tesoro_img = Image.open(base_assets / "tesoro_icon.png").resize((20, 20), Image.LANCZOS)
            self._tesoro_icon = ctk.CTkImage(tesoro_img, size=(20, 20))
        except Exception:
            self._tesoro_icon = None

        try:
            varita_img = Image.open(base_assets / "varita_icon.png").resize((20, 20), Image.LANCZOS)
            self._varita_icon = ctk.CTkImage(varita_img, size=(20, 20))
        except Exception:
            self._varita_icon = None

        self.cliente_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.cliente_container.pack(
            fill="x",
            pady=(spacing_top, spacing_bottom)
        )

        # Crear dos líneas separadas dentro del cliente_container
        self.linea1 = ctk.CTkFrame(self.cliente_container, fg_color="transparent")
        self.linea1.pack(fill="x", pady=(0, 4))

        self.linea2 = ctk.CTkFrame(self.cliente_container, fg_color="transparent")
        self.linea2.pack(fill="x")

        # Línea 1: Nombre (izquierda) y Nivel (derecha)
        if self._user_icon:
            self.user_icon_label = ctk.CTkLabel(
                self.linea1,
                image=self._user_icon,
                text=""
            )
            self.user_icon_label.pack(side="left", padx=(pad_h, 6))
            self.user_icon_label.configure(cursor="hand2")
            self.user_icon_label.bind("<Button-1>", self._on_remove_cliente)

        self.cliente_nombre_label = ctk.CTkLabel(
            self.linea1,
            text="SELECCIONAR CLIENTE...",
            font=cliente_font,
            text_color=text_color,
            anchor="w",
            height=label_height
        )
        self.cliente_nombre_label.pack(side="left", padx=(pad_h if not getattr(self, '_user_icon', None) else 0, 0))

        self.cliente_nivel_label = ctk.CTkLabel(
            self.linea1,
            text="",
            font=cliente_font,
            text_color=text_color,
            anchor="e",
            height=label_height
        )
        self.cliente_nivel_label.pack(side="right", padx=(0, pad_h))

        # Línea 2: Tesoro (izquierda) + Varita (derecha)
        # Línea 2 contenedor izquierdo
        self.linea2_left = ctk.CTkFrame(self.linea2, fg_color="transparent")
        self.linea2_left.pack(side="left", padx=(pad_h, 0))

        # Línea 2 contenedor derecho
        self.linea2_right = ctk.CTkFrame(self.linea2, fg_color="transparent")
        self.linea2_right.pack(side="right", padx=(0, pad_h))

        # Icono tesoro (usar imagen si está disponible, sino fallback emoji)
        if self._tesoro_icon:
            self.tesoro_icon_label = ctk.CTkLabel(
                self.linea2_left,
                image=self._tesoro_icon,
                text=""
            )
            self.tesoro_icon_label.pack(side="left")
        else:
            self.tesoro_icon_label = ctk.CTkLabel(
                self.linea2_left,
                text="💰",
                font=cliente_font
            )
            self.tesoro_icon_label.pack(side="left")

        # Tesoro label a la izquierda
        self.tesoro_label = ctk.CTkLabel(
            self.linea2_left,
            text="0 pts",
            font=cliente_font,
            text_color=self.ticket_colors.get("header", {}).get("text_tesoro", "#FFD700"),
            height=label_height
        )
        self.tesoro_label.pack(side="left", padx=(6, 0))

        # Botón varita (placeholder) usando ButtonFactory
        try:
            self.varita_button = ButtonFactory.create_button(
                parent=self.linea2_right,
                image=self._varita_icon,
                text="",
                style_key="mini_outline_clientes",
                command=self._on_varita_click
            )
            self.varita_button.pack()
        except Exception:
            # No bloquear si ButtonFactory no funciona
            pass

    def _create_body(self):
        """Crear zona del cuerpo con CarritoNavList."""
        body_cfg = self.ticket_colors.get("body", {})
        body_layout = self.ticket_layout.get("body", {})

        # Determinar altura fija para el body desde config (por defecto 250)
        body_height = body_layout.get("height", 250)

        self.body_frame = ctk.CTkFrame(
            self,
            height=body_height,
            fg_color=body_cfg.get("bg", "#000000")
        )

        # Empaquetar como caja fija en vertical: no expandir, ocupar solo el ancho
        self.body_frame.pack(
            fill="x",
            expand=False,
            padx=body_layout.get("padding_horizontal", 12),
            pady=(
                body_layout.get("padding_vertical_top", 4),
                body_layout.get("padding_vertical_bottom", 8)
            )
        )

        # Asegurar que el tamaño no sea modificado por el contenido
        self.body_frame.pack_propagate(False)

        # CarritoNavList (rellena el interior fijo)
        try:
            self.carrito_nav_list = CarritoNavList(
                parent=self.body_frame,
                on_item_change=self._on_item_change,
                keyboard_manager=self.keyboard_manager
            )
            self.carrito_nav_list.pack(fill="both", expand=True)
        except Exception:
            logger.exception("Error creando CarritoNavList")

    # NavList crea sus propios headers; método eliminado

    def _create_footer(self):
        """Crear zona de footer (totales + formas de pago)."""
        footer_cfg = self.ticket_colors.get("footer", {})

        # Footer SIN altura fija - se expande según contenido (payment controllers)
        self.footer_frame = ctk.CTkFrame(
            self,
            fg_color=footer_cfg.get("bg", "#1a1a1a")
        )
        footer_layout = self.ticket_layout.get("footer", {})
        self.footer_frame.pack(
            fill="x",
            padx=footer_layout.get("padding_horizontal", 12),
            pady=(
                footer_layout.get("padding_vertical_top", 0),
                footer_layout.get("padding_vertical_bottom", 12)
            )
        )

        # Container para totales (leer estructura anidada desde config)
        totales_cfg = footer_layout.get("totales_section", {})

        self.totales_container = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        tot_pad_top = totales_cfg.get("padding_top", 8)
        self.totales_container.pack(fill="x", pady=(tot_pad_top, 0))

        # Separador visual
        separator = ctk.CTkFrame(
            self.totales_container,
            height=2,
            fg_color=footer_cfg.get("text", "#FFFFFF")
        )
        pad_h = footer_layout.get("padding_horizontal", 12)
        sep_pad = totales_cfg.get("separator_padding", 8)
        separator.pack(fill="x", padx=pad_h, pady=(0, sep_pad))

        # Grid para totales (3 columnas)
        self._create_totales_grid()

        # Área para payment controllers (se llenará dinámicamente)
        payment_cfg = footer_layout.get("payment_area", {})
        self.payment_area = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        self.payment_area.pack(
            fill="both",
            expand=True,
            pady=(
                payment_cfg.get("padding_top", 8),
                payment_cfg.get("padding_bottom", 12)
            )
        )

    def _create_totales_grid(self):
        """Crear zona de totales usando columnas Pack para estabilidad visual."""
        footer_cfg = self.ticket_colors.get("footer", {})

        # Fuentes (reutilizando las del config si existen, o defaults seguros)
        labels_font_cfg = self.ticket_fonts.get("footer_labels", {})
        labels_font = (
            labels_font_cfg.get("family", "Courier New"),
            labels_font_cfg.get("size", 14),
            labels_font_cfg.get("weight", "bold")
        )

        totales_font_cfg = self.ticket_fonts.get("footer_totales", {})
        totales_font = (
            totales_font_cfg.get("family", "Courier New"),
            totales_font_cfg.get("size", 16),
            totales_font_cfg.get("weight", "bold")
        )

        footer_layout = self.ticket_layout.get("footer", {})

        # 1. Contenedor "Caja Fuerte" (Altura fija compacta)
        # Altura suficiente para Título + Valor (aprox 20+25 = 45px) + márgenes
        grid_frame = ctk.CTkFrame(self.totales_container, fg_color="transparent", height=100)
        grid_frame.pack_propagate(False)  # <--- CLAVE: Impide estiramiento

        pad_h = footer_layout.get("padding_horizontal", 12)
        grid_frame.pack(fill="x", padx=pad_h)

        # 2. Columnas (Izquierda, Centro, Derecha)

        # Columna 1: SUBTOTAL (Alineada izquierda)
        col_sub = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_sub.pack(side="left", fill="y", anchor="w")

        ctk.CTkLabel(col_sub, text="SUBTOTAL", font=labels_font, text_color=footer_cfg.get("text", "#FFFFFF")).pack(anchor="w")
        self.subtotal_label = ctk.CTkLabel(col_sub, text="0.00€", font=totales_font, text_color=footer_cfg.get("text", "#FFFFFF"))
        self.subtotal_label.pack(anchor="w")

        # Columna 3: TOTAL (Alineada derecha - La creamos antes para que se pegue al borde derecho)
        col_tot = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_tot.pack(side="right", fill="y", anchor="e")

        ctk.CTkLabel(col_tot, text="TOTAL", font=labels_font, text_color=footer_cfg.get("text_totales", "#00FF00")).pack(anchor="e")
        self.total_label = ctk.CTkLabel(col_tot, text="0.00€", font=totales_font, text_color=footer_cfg.get("text_totales", "#00FF00"))
        self.total_label.pack(anchor="e")

        # Columna 2: IVA (Centro - Ocupa el espacio restante)
        col_iva = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_iva.pack(side="left", fill="both", expand=True) # Rellena hueco central

        ctk.CTkLabel(col_iva, text="DESGLOSE IVA", font=labels_font, text_color=footer_cfg.get("text", "#FFFFFF")).pack(anchor="center")
        self.iva_container = ctk.CTkFrame(col_iva, fg_color="transparent")
        self.iva_container.pack(anchor="center")

    def _clear_payment_area(self):
        """Limpiar el área de payment controllers."""
        try:
            if getattr(self, 'active_payment_controller', None):
                try:
                    self.active_payment_controller.destroy()
                except Exception:
                    pass
                self.active_payment_controller = None
                self.active_payment_type = None

            # Limpiar cualquier widget residual (ocultar, NO destruir para preservar controllers pre-creados)
            if hasattr(self, 'payment_area'):
                for widget in self.payment_area.winfo_children():
                    try:
                        widget.pack_forget()
                    except Exception:
                        pass

        except Exception:
            logger.exception("Error limpiando payment area")

    def activar_pago_efectivo(self, on_finalizar: Optional[Callable] = None):
        """Activar forma de pago EFECTIVO."""
        try:
            self._clear_payment_area()

            resumen = self.carrito_service.get_resumen_financiero() if self.carrito_service else {}
            total = resumen.get("total", 0.0)

            self.active_payment_controller = PaymentControllerEfectivo(
                parent=self.payment_area,
                total=total,
                on_finalizar=on_finalizar
            )
            self.active_payment_controller.pack(fill="both", expand=True)
            self.active_payment_type = "efectivo"

            logger.info("Pago efectivo activado")

        except Exception:
            logger.exception("Error activando pago efectivo")

    def activar_pago_tarjeta(self, on_finalizar: Optional[Callable] = None):
        """Activar forma de pago TARJETA."""
        try:
            self._clear_payment_area()

            resumen = self.carrito_service.get_resumen_financiero() if self.carrito_service else {}
            total = resumen.get("total", 0.0)

            self.active_payment_controller = PaymentControllerSimple(
                parent=self.payment_area,
                tipo_pago="Tarjeta",
                total=total,
                on_finalizar=on_finalizar
            )
            self.active_payment_controller.pack(fill="both", expand=True)
            self.active_payment_type = "tarjeta"

            logger.info("Pago tarjeta activado")

        except Exception:
            logger.exception("Error activando pago tarjeta")

    def activar_pago_web(self, on_finalizar: Optional[Callable] = None):
        """Activar forma de pago WEB."""
        try:
            self._clear_payment_area()

            resumen = self.carrito_service.get_resumen_financiero() if self.carrito_service else {}
            total = resumen.get("total", 0.0)

            self.active_payment_controller = PaymentControllerSimple(
                parent=self.payment_area,
                tipo_pago="Web",
                total=total,
                on_finalizar=on_finalizar
            )
            self.active_payment_controller.pack(fill="both", expand=True)
            self.active_payment_type = "web"

            logger.info("Pago web activado")

        except Exception:
            logger.exception("Error activando pago web")

    def activar_pago_multi(self, on_finalizar: Optional[Callable] = None):
        """Activar forma de pago MULTI (efectivo + tarjeta)."""
        try:
            self._clear_payment_area()

            resumen = self.carrito_service.get_resumen_financiero() if self.carrito_service else {}
            total = resumen.get("total", 0.0)

            self.active_payment_controller = PaymentControllerMulti(
                parent=self.payment_area,
                total=total,
                on_finalizar=on_finalizar
            )
            self.active_payment_controller.pack(fill="both", expand=True)
            self.active_payment_type = "multi"

            logger.info("Pago multi activado")

        except Exception:
            logger.exception("Error activando pago multi")

    def desactivar_pago(self):
        """Desactivar forma de pago activa (volver footer a estado neutral)."""
        self._clear_payment_area()
        logger.info("Forma de pago desactivada")

    # Métodos públicos para actualizar desde el controller

    def _start_clock(self):
        """Actualizar reloj interno cada segundo."""
        from datetime import datetime
        try:
            now = datetime.now()
            hora_str = now.strftime("%H:%M:%S - %d/%m/%Y")
            self.hora_label.configure(text=hora_str)
            self.after(1000, self._start_clock)  # Repetir en 1s
        except Exception:
            pass
    
    def update_hora(self, hora_str: str):
        """Actualizar hora en tiempo real."""
        try:
            self.hora_label.configure(text=hora_str)
        except Exception:
            pass

    def update_cajero(self, nombre: str):
        """Actualizar nombre del cajero."""
        try:
            self.cajero_label.configure(text=f"Cajero: {nombre}")
        except Exception:
            pass

    def update_cliente(self, cliente_data: Optional[Dict[str, Any]]):
        """Actualizar información del cliente."""
        try:
            if cliente_data:
                    nombre = cliente_data.get("nombre", "---")
                    nivel = cliente_data.get("nivel_level")
                    nivel_nombre = cliente_data.get("nivel_nombre")
                    grafismo = cliente_data.get("nivel_grafismo", "")

                    self.cliente_nombre_label.configure(text=nombre)

                    if nivel and nivel_nombre:
                        nivel_texto = f"Lv {nivel} - {nivel_nombre} {grafismo}"
                    else:
                        nivel_texto = ""

                    # Actualizar label de nivel separado
                    try:
                        self.cliente_nivel_label.configure(text=nivel_texto)
                    except Exception:
                        # En caso de que el label no exista aún, ignorar
                        pass

                    tesoro = cliente_data.get("tesoro_total", 0)
                    self.tesoro_label.configure(text=f"{tesoro} pts")
            else:
                self.cliente_nombre_label.configure(text="SELECCIONAR CLIENTE...")
                self.tesoro_label.configure(text="0 pts")
        except Exception:
            logger.exception("Error actualizando cliente")

    def _on_remove_cliente(self, event=None):
        try:
            if self.carrito_service:
                self.carrito_service.set_cliente(None)
            self.update_cliente(None)
        except Exception:
            logger.exception("Error quitando cliente del carrito")

    def _on_varita_click(self):
        try:
            from kool_tpv.modulos.tpv.actions.canjear_tesoro import CanjearTesoroAction
            from kool_tpv.modulos.fidelizacion.fidelizacion_service import FidelizacionService

            fidelizacion_service = FidelizacionService(self.db)

            action = CanjearTesoroAction(
                view=self,
                carrito_service=self.carrito_service,
                fidelizacion_service=fidelizacion_service
            )

            action.ejecutar()

        except Exception:
            import logging
            logging.exception("Error ejecutando CanjearTesoroAction")

    def _remove_tesoro_visual(self):
        """Eliminar visualmente el canje: limpiar puntos y refrescar UI."""
        try:
            from decimal import Decimal
            if self.carrito_service:
                try:
                    self.carrito_service.set_puntos_canjeados(Decimal('0.00'))
                except Exception:
                    self.carrito_service.set_puntos_canjeados(0)
            try:
                self.update_carrito()
            except Exception:
                pass
        except Exception:
            logger.exception("Error en _remove_tesoro_visual")

    def _remove_descuento_visual(self):
        """Eliminar visualmente el descuento: delegar al servicio y refrescar UI."""
        try:
            if self.carrito_service:
                try:
                    self.carrito_service.eliminar_descuento()
                except Exception:
                    # Fallback: asignar None directamente
                    try:
                        self.carrito_service._descuento = None
                    except Exception:
                        pass
            try:
                self.update_carrito()
            except Exception:
                pass
        except Exception:
            logger.exception("Error en _remove_descuento_visual")

    def update_totales(self, subtotal: float, total: float, desglose_iva: list = None):
        """Actualizar totales del footer con desglose de IVA.

        Args:
            subtotal: Subtotal sin IVA
            total: Total con IVA
            desglose_iva: Lista de dicts con {"tipo": 21, "base": 100, "iva": 21}
        """
        try:
            # Actualizar subtotal
            try:
                self.subtotal_label.configure(text=self.formatter.format_precio(subtotal))
            except Exception:
                try:
                    self.subtotal_label.configure(text=f"{float(subtotal):.2f} €")
                except Exception:
                    self.subtotal_label.configure(text="0.00 €")

            # Actualizar total
            try:
                self.total_label.configure(text=self.formatter.format_precio(total))
            except Exception:
                try:
                    self.total_label.configure(text=f"{float(total):.2f} €")
                except Exception:
                    self.total_label.configure(text="0.00 €")

            # Limpiar desglose IVA anterior
            for widget in getattr(self, 'iva_container', []).winfo_children() if hasattr(self, 'iva_container') else []:
                try:
                    widget.destroy()
                except Exception:
                    pass

            # Añadir desglose IVA dinámico
            if desglose_iva:
                footer_cfg = self.ticket_colors.get("footer", {})
                iva_font_cfg = self.ticket_fonts.get("footer_labels", {})
                iva_font = (
                    iva_font_cfg.get("family", "Courier New"),
                    iva_font_cfg.get("size", 11),
                    iva_font_cfg.get("weight", "normal")
                )

                # CORRECCIÓN: Manejar tanto lista como diccionario
                if isinstance(desglose_iva, dict):
                    # Si es dict {21: 1.50}, lo convertimos a iterador
                    items_iva = desglose_iva.items()
                else:
                    # Si es lista [{'tipo': 21, 'iva': 1.50}], extraemos valores
                    items_iva = [(item.get('tipo'), item.get('iva')) for item in desglose_iva]

                for tipo, iva_amount in items_iva:
                    # Asegurar tipos numéricos
                    try:
                        tipo = int(tipo)
                        iva_amount = float(iva_amount)
                    except:
                        continue

                    if iva_amount > 0:
                        try:
                            iva_text = self.formatter.format_precio(iva_amount) if getattr(self, 'formatter', None) is not None else f"{iva_amount:.2f} €"
                        except Exception:
                            try:
                                iva_text = f"{float(iva_amount):.2f} €"
                            except Exception:
                                iva_text = "0.00 €"
                        label = ctk.CTkLabel(
                            self.iva_container,
                            text=f"IVA {tipo}%: {iva_text}",
                            font=iva_font,
                            text_color=footer_cfg.get("text", "#FFFFFF"),
                            anchor="center"
                        )
                        label.pack()

        except Exception:
            logger.exception("Error actualizando totales")

    def _on_item_change(self, item_data: dict, action: str):
        """Handler cuando se modifica un item desde el NavList."""
        try:
            if not self.carrito_service:
                return

            if action == "add":
                _line_tipo = str(item_data.get('line_tipo', 'venta')).lower()
                if _line_tipo == 'devolucion':
                    # Modo devolucion: item_data ya tiene line_tipo='devolucion',
                    # add_item encuentra el item existente (mismo id + line_tipo) y suma +1
                    item_delta = item_data.copy()
                    item_delta['cantidad'] = 1
                    self.carrito_service.add_item(item_delta)
                else:
                    # Modo venta normal: añadir +1 unidad
                    try:
                        if getattr(self, 'db', None) is not None:
                            from kool_tpv.base_datos.producto_service import ProductoService
                            ps = ProductoService(self.db)
                            producto_para_carrito = ps.get_producto_para_carrito(item_data.get('id'), cantidad=1)
                            self.carrito_service.add_item(producto_para_carrito)
                        else:
                            item_delta = item_data.copy()
                            item_delta['cantidad'] = 1
                            self.carrito_service.add_item(item_delta)
                    except Exception:
                        try:
                            item_delta = item_data.copy()
                            item_delta['cantidad'] = 1
                            self.carrito_service.add_item(item_delta)
                        except Exception:
                            logging.exception('Error añadiendo item via fallback')

            elif action == "remove":
                item_id = item_data.get("id")
                item_line_tipo = str(item_data.get('line_tipo', 'venta')).lower()
                items = self.carrito_service.get_items() or []

                for idx, item in enumerate(items):
                    if item.get("id") == item_id and str(item.get('line_tipo', 'venta')).lower() == item_line_tipo:
                        current_qty = int(item.get("cantidad", 0))
                        if current_qty > 1:
                            self.carrito_service.update_cantidad(idx, current_qty - 1)
                        else:
                            self.carrito_service.remove_item(idx)
                        break

            # Refrescar display
            self.update_carrito()

        except Exception:
            logger.exception("Error en _on_item_change")

    def update_display(self):
        """
        Método de compatibilidad con implementación antigua.
        Delegado al nuevo método update_carrito().
        """
        try:
            self.update_carrito()
        except Exception:
            logger.exception("Error delegando update_display a update_carrito")

    def update_carrito(self):
        """Actualizar display del carrito manteniendo scroll."""
        try:
            try:
                pass
            except Exception:
                pass
            if not self.carrito_service:
                return

            # Guardar posición scroll (donde estaba mirando el usuario)
            scroll_pos = 0.0
            try:
                if hasattr(self, 'carrito_nav_list'):
                    # El canvas es el panel interno del scroll
                    # Intentamos leer la posición Y actual (devuelve tupla, ej: (0.0, 0.4))
                    scroll_pos = self.carrito_nav_list._parent_canvas.yview()[0]
            except Exception:
                pass

            # Limpiar nav_list (borra todo)
            if hasattr(self, 'carrito_nav_list'):
                self.carrito_nav_list.clear_items()

                # Obtener items del servicio
                items = self.carrito_service.get_items() or []

                # Si el carrito queda vacío, ocultar el payment controller activo
                if not items:
                    try:
                        for widget in self.payment_area.winfo_children():
                            widget.pack_forget()
                    except Exception:
                        pass

                # Añadir items al nav_list
                for item in items:
                    total_linea = item.get('total_linea', 0.0)
                    if str(item.get('line_tipo', 'venta')).lower() == 'devolucion':
                        item['total'] = -total_linea  # negat el Decimal (no convertir a float: activaría rama cents→euros)
                    else:
                        item['total'] = total_linea
                    self.carrito_nav_list.add_item(item)

                # Sincronizar cliente visual con el servicio
                try:
                    cliente_actual = self.carrito_service.get_cliente()
                    self.update_cliente(cliente_actual)
                except Exception:
                    logger.exception("Error sincronizando cliente en update_carrito")

                try:
                    puntos = self.carrito_service.get_puntos_canjeados()
                    logger.info(f"[DEBUG TESORO] puntos={puntos!r}, type={type(puntos).__name__}")
                    # Añadir fila visual de canje SOLO si no hay una línea 'tesoro' real
                    try:
                        has_tesoro = any(str(it.get('line_tipo', '')).lower() == 'tesoro' for it in items)
                    except Exception:
                        has_tesoro = False
                    from decimal import Decimal
                    if not has_tesoro and puntos and Decimal(str(puntos)) > Decimal('0'):
                        # Convertir puntos (euros) a centavos para consistencia con sistema
                        puntos_centavos = int(Decimal(str(puntos)) * 100)
                        logger.info(f"[DEBUG TESORO] puntos_centavos={puntos_centavos!r}, -puntos_centavos={-puntos_centavos!r}")
                        self.carrito_nav_list.add_item({
                            "id": "__tesoro_visual__",
                            "nombre": ">> TESORO CANJEADO <<",
                            "cantidad": "",
                            "pvp": "",
                            "total": -puntos_centavos,  # Negativo en centavos
                            "line_tipo": "tesoro_visual",
                            "visual": True,
                            "on_remove": self._remove_tesoro_visual
                        })
                except Exception:
                    import logging
                    logging.exception("Error añadiendo línea visual de canje")

                # Añadir línea visual de descuento si aplica (similar a CarritoUI)
                try:
                    resumen_tmp = self.carrito_service.get_resumen_financiero() or {}
                except Exception:
                    resumen_tmp = {}

                try:
                    descuento_euros = resumen_tmp.get('descuento_euros', None)
                    descuento_tipo = resumen_tmp.get('descuento_tipo', None)
                    descuento_valor = resumen_tmp.get('descuento_valor', None)
                    from decimal import Decimal
                    logger.info(f"TicketCarrito.update_carrito: resumen_financiero={resumen_tmp}")
                    if descuento_euros and Decimal(str(descuento_euros)) > Decimal('0') and descuento_tipo is not None:
                        try:
                            logger.info(f"TicketCarrito.update_carrito: detectado descuento {descuento_tipo} -> {descuento_valor} ({descuento_euros}€)")
                            if descuento_tipo == 'directo':
                                texto_descuento = '>> Descuento Directo:'
                            elif descuento_tipo == 'porcentaje':
                                texto_descuento = f'>> Descuento -{descuento_valor}%:'
                            else:
                                texto_descuento = '>> Descuento:'

                            # Insert visual discount row
                            self.carrito_nav_list.add_item({
                                "id": "__descuento_visual__",
                                "nombre": texto_descuento,
                                "cantidad": "",
                                "pvp": "",
                                "total": -float(descuento_euros),
                                "line_tipo": "descuento",
                                "visual": True,
                                "on_remove": self._remove_descuento_visual if hasattr(self, '_remove_descuento_visual') else (lambda: None)
                            })
                            logger.info("TicketCarrito.update_carrito: línea de descuento añadida al NavList")
                        except Exception:
                            import logging
                            logging.exception('Error insertando línea visual de descuento')
                except Exception:
                    import logging
                    logging.exception("Error añadiendo línea visual de canje")

                # Restaurar scroll (volver a donde estaba)
                try:
                    self.carrito_nav_list._parent_canvas.yview_moveto(scroll_pos)
                except Exception:
                    pass

                # Actualizar totales
                resumen = self.carrito_service.get_resumen_financiero() or {}
                subtotal = resumen.get("subtotal", 0.0)
                total = resumen.get("total", 0.0)

                # Obtener desglose de IVA (si el servicio lo proporciona)
                desglose_iva = resumen.get("iva_desglose", [])

                self.update_totales(subtotal, total, desglose_iva)

                # Si hay un payment controller activo, actualizar su total
                if self.active_payment_controller and hasattr(self.active_payment_controller, 'set_total'):
                    try:
                        self.active_payment_controller.set_total(total)
                    except Exception:
                        logger.exception("Error actualizando total en payment controller")

            # --- Restaurar selección y teclado ---
            try:
                if hasattr(self, "carrito_nav_list") and self.carrito_nav_list.rows_data:
                    # Seleccionar primera fila
                    try:
                        self.carrito_nav_list._select_row(0)
                    except Exception:
                        pass

                    # Dar foco visual
                    try:
                        self.carrito_nav_list.focus_set()
                    except Exception:
                        pass

                    try:
                        pass
                    except Exception:
                        pass

                    # Registrar como lista activa en KeyboardManager
                    try:
                        if getattr(self.carrito_nav_list, "keyboard_manager", None):
                            self.carrito_nav_list.keyboard_manager.set_active_list(
                                self.carrito_nav_list
                            )
                            try:
                                pass
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                import logging
                logging.exception("Error restaurando foco y navegación del carrito")

            # Forzar pintado inmediato para evitar negro
            self.update_idletasks()

        except Exception:
            logger.exception("Error actualizando carrito")
