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
        self.keyboard_manager = keyboard_manager
        # Payment controller activo
        self.active_payment_controller = None
        self.active_payment_type = None

        # Crear estructura
        self._create_header()
        self._create_body()
        self._create_footer()

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

            # Calcular total
            total_height = (
                pad_top +
                info_spacing + info_height +
                cliente_spacing + cliente_height +
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

        self.cliente_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.cliente_container.pack(
            fill="x",
            pady=(spacing_top, spacing_bottom)
        )

        # Línea 1: Nombre + Nivel
        self.cliente_nombre_label = ctk.CTkLabel(
            self.cliente_container,
            text="SELECCIONAR CLIENTE...",
            font=cliente_font,
            text_color=text_color,
            anchor="w",
            height=label_height
        )
        self.cliente_nombre_label.pack(side="left", padx=(pad_h, 0))

        # Línea 2: Tesoro + Varita (placeholder por ahora)
        tesoro_container = ctk.CTkFrame(self.cliente_container, fg_color="transparent")
        tesoro_container.pack(side="right", padx=(0, pad_h))

        self.tesoro_label = ctk.CTkLabel(
            tesoro_container,
            text="0 pts",
            font=cliente_font,
            text_color=self.ticket_colors.get("header", {}).get("text_tesoro", "#FFD700")
            ,
            height=label_height
        )
        self.tesoro_label.pack(side="right")

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
        """Crear grid de totales con 3 columnas."""
        footer_cfg = self.ticket_colors.get("footer", {})

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
        # Frame para el grid
        grid_frame = ctk.CTkFrame(self.totales_container, fg_color="transparent")
        pad_h = footer_layout.get("padding_horizontal", 12)
        grid_frame.pack(fill="x", padx=pad_h)

        # Configurar 3 columnas
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)

        # Columna 1: SUBTOTAL
        ctk.CTkLabel(
            grid_frame,
            text="SUBTOTAL",
            font=labels_font,
            text_color=footer_cfg.get("text", "#FFFFFF"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.subtotal_label = ctk.CTkLabel(
            grid_frame,
            text="0.00€",
            font=totales_font,
            text_color=footer_cfg.get("text", "#FFFFFF"),
            anchor="w"
        )
        self.subtotal_label.grid(row=1, column=0, sticky="w", padx=(0, 8))

        # Columna 2: DESGLOSE IVA (contenedor dinámico)
        ctk.CTkLabel(
            grid_frame,
            text="DESGLOSE IVA",
            font=labels_font,
            text_color=footer_cfg.get("text", "#FFFFFF"),
            anchor="center"
        ).grid(row=0, column=1, sticky="ew", padx=8)

        self.iva_container = ctk.CTkFrame(grid_frame, fg_color="transparent")
        self.iva_container.grid(row=1, column=1, sticky="ew", padx=8)

        # Columna 3: TOTAL
        ctk.CTkLabel(
            grid_frame,
            text="TOTAL",
            font=labels_font,
            text_color=footer_cfg.get("text_totales", "#00FF00"),
            anchor="e"
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.total_label = ctk.CTkLabel(
            grid_frame,
            text="0.00€",
            font=totales_font,
            text_color=footer_cfg.get("text_totales", "#00FF00"),
            anchor="e"
        )
        self.total_label.grid(row=1, column=2, sticky="e", padx=(8, 0))

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

            # Limpiar cualquier widget residual
            if hasattr(self, 'payment_area'):
                for widget in self.payment_area.winfo_children():
                    try:
                        widget.destroy()
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
                self.cliente_nombre_label.configure(text=nombre)

                tesoro = cliente_data.get("tesoro_total", 0)
                self.tesoro_label.configure(text=f"{tesoro} pts")
            else:
                self.cliente_nombre_label.configure(text="SELECCIONAR CLIENTE...")
                self.tesoro_label.configure(text="0 pts")
        except Exception:
            logger.exception("Error actualizando cliente")

    def update_totales(self, subtotal: float, total: float, desglose_iva: list = None):
        """Actualizar totales del footer con desglose de IVA.

        Args:
            subtotal: Subtotal sin IVA
            total: Total con IVA
            desglose_iva: Lista de dicts con {"tipo": 21, "base": 100, "iva": 21}
        """
        try:
            # Actualizar subtotal
            self.subtotal_label.configure(text=f"{subtotal:.2f}€")

            # Actualizar total
            self.total_label.configure(text=f"{total:.2f}€")

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

                for idx, item in enumerate(desglose_iva):
                    tipo = item.get("tipo", 0)
                    iva_amount = item.get("iva", 0)

                    if iva_amount > 0:
                        label = ctk.CTkLabel(
                            self.iva_container,
                            text=f"IVA {tipo}%: {iva_amount:.2f}€",
                            font=iva_font,
                            text_color=footer_cfg.get("text", "#FFFFFF"),
                            anchor="center"
                        )
                        label.pack()

        except Exception:
            logger.exception("Error actualizando totales")

    def _on_item_change(self, item_data: dict, action: str):
        """Handler cuando se modifica un item desde el NavList.

        Args:
            item_data: Datos del item
            action: 'add' o 'remove'
        """
        try:
            if not self.carrito_service:
                return

            if action == "add":
                # Añadir +1 unidad
                self.carrito_service.add_item(item_data)
            elif action == "remove":
                # Reducir -1 unidad o eliminar
                # (el carrito_service ya tiene esta lógica)
                item_id = item_data.get("id")
                items = self.carrito_service.get_items() or []

                for idx, item in enumerate(items):
                    if item.get("id") == item_id:
                        current_qty = item.get("cantidad", 0)
                        if current_qty > 1:
                            self.carrito_service.update_cantidad(idx, current_qty - 1)
                        else:
                            self.carrito_service.remove_item(idx)
                        break

            # Refrescar display
            self.update_carrito()

        except Exception:
            logger.exception("Error en _on_item_change")

    def update_carrito(self):
        """Actualizar display del carrito desde carrito_service."""
        try:
            if not self.carrito_service:
                return

            # Limpiar nav_list
            if hasattr(self, 'carrito_nav_list'):
                self.carrito_nav_list.clear_items()

                # Obtener items del servicio
                items = self.carrito_service.get_items() or []

                # Añadir items al nav_list
                for item in items:
                    self.carrito_nav_list.add_item(item)

                # Actualizar totales
                resumen = self.carrito_service.get_resumen_financiero() or {}
                subtotal = resumen.get("subtotal", 0.0)
                total = resumen.get("total", 0.0)

                # Obtener desglose de IVA (si el servicio lo proporciona)
                desglose_iva = resumen.get("desglose_iva", [])

                self.update_totales(subtotal, total, desglose_iva)

                # Si hay un payment controller activo, actualizar su total
                if self.active_payment_controller and hasattr(self.active_payment_controller, 'set_total'):
                    try:
                        self.active_payment_controller.set_total(total)
                    except Exception:
                        logger.exception("Error actualizando total en payment controller")

        except Exception:
            logger.exception("Error actualizando carrito")
