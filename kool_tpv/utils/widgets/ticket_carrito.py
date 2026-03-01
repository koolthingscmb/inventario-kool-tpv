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
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def load_config(config_name: str) -> dict:
    """Cargar archivo de configuración."""
    try:
        base = Path(__file__).resolve().parents[3]
        config_path = base / "config" / config_name
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception(f"Error cargando {config_name}")
        return {}


class TicketCarrito(ctk.CTkFrame):
    """Widget completo del Ticket Carrito con Header/Cuerpo/Footer."""

    def __init__(self, parent, **kwargs):
        # Cargar configs
        self.colors = load_config("colors_config.json")
        self.fonts = load_config("font_config.json")
        self.layout = load_config("layout_config.json")

        # Extraer configuraciones específicas
        self.ticket_colors = self.colors.get("tpv", {}).get("ticket_carrito", {})
        self.ticket_fonts = self.fonts.get("modules", {}).get("tpv", {}).get("ticket_carrito", {})
        self.ticket_layout = self.layout.get("modules", {}).get("tpv", {}).get("ticket_carrito", {})

        # Configurar frame principal
        width = self.ticket_layout.get("width", 420)
        bg = self.ticket_colors.get("body", {}).get("bg", "#000000")

        super().__init__(parent, width=width, fg_color=bg, **kwargs)
        self.pack_propagate(False)

        # Crear estructura
        self._create_header()
        self._create_body()
        self._create_footer()

        logger.info("TicketCarrito inicializado")

    def _create_header(self):
        """Crear zona de header (info general + cliente)."""
        header_cfg = self.ticket_colors.get("header", {})
        header_height = self.ticket_layout.get("header_height", 120)

        self.header_frame = ctk.CTkFrame(
            self,
            height=header_height,
            fg_color=header_cfg.get("bg", "#000000")
        )
        self.header_frame.pack(fill="x", padx=12, pady=(12, 0))
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

        info_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        info_container.pack(fill="x", pady=(8, 4))

        # Hora/Fecha (se actualizará dinámicamente)
        self.hora_label = ctk.CTkLabel(
            info_container,
            text="--:--:--",
            font=info_font,
            text_color=text_color,
            anchor="w"
        )
        self.hora_label.pack(side="left", padx=(12, 0))

        # Cajero
        self.cajero_label = ctk.CTkLabel(
            info_container,
            text="Cajero: ---",
            font=info_font,
            text_color=text_color,
            anchor="e"
        )
        self.cajero_label.pack(side="right", padx=(0, 12))

    def _create_cliente_section(self):
        """Crear sección de cliente (nombre + nivel + tesoro + varita)."""
        cliente_font_cfg = self.ticket_fonts.get("header_cliente", {})
        cliente_font = (
            cliente_font_cfg.get("family", "Courier New"),
            cliente_font_cfg.get("size", 16),
            cliente_font_cfg.get("weight", "bold")
        )
        text_color = self.ticket_colors.get("header", {}).get("text_cliente", "#FFD700")

        self.cliente_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.cliente_container.pack(fill="x", pady=(4, 8))

        # Línea 1: Nombre + Nivel
        self.cliente_nombre_label = ctk.CTkLabel(
            self.cliente_container,
            text="SELECCIONAR CLIENTE...",
            font=cliente_font,
            text_color=text_color,
            anchor="w"
        )
        self.cliente_nombre_label.pack(side="left", padx=(12, 0))

        # Línea 2: Tesoro + Varita (placeholder por ahora)
        tesoro_container = ctk.CTkFrame(self.cliente_container, fg_color="transparent")
        tesoro_container.pack(side="right", padx=(0, 12))

        self.tesoro_label = ctk.CTkLabel(
            tesoro_container,
            text="0 pts",
            font=cliente_font,
            text_color=self.ticket_colors.get("header", {}).get("text_tesoro", "#FFD700")
        )
        self.tesoro_label.pack(side="right")

    def _create_body(self):
        """Crear zona del cuerpo (carrito_nav_list)."""
        body_cfg = self.ticket_colors.get("body", {})

        self.body_frame = ctk.CTkFrame(
            self,
            fg_color=body_cfg.get("bg", "#000000")
        )
        self.body_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Placeholder: aquí irá carrito_nav_list
        placeholder = ctk.CTkLabel(
            self.body_frame,
            text="[ Carrito NavList - Placeholder ]",
            text_color=body_cfg.get("header_text", "#00FF00")
        )
        placeholder.pack(expand=True)

    def _create_footer(self):
        """Crear zona de footer (totales + formas de pago)."""
        footer_cfg = self.ticket_colors.get("footer", {})
        footer_height = self.ticket_layout.get("footer_height", 140)

        self.footer_frame = ctk.CTkFrame(
            self,
            height=footer_height,
            fg_color=footer_cfg.get("bg", "#1a1a1a")
        )
        self.footer_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.footer_frame.pack_propagate(False)

        # Labels de totales (placeholder simple)
        footer_font_cfg = self.ticket_fonts.get("footer_labels", {})
        footer_font = (
            footer_font_cfg.get("family", "Courier New"),
            footer_font_cfg.get("size", 14),
            footer_font_cfg.get("weight", "bold")
        )

        totales_container = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        totales_container.pack(fill="x", pady=12)

        self.subtotal_label = ctk.CTkLabel(
            totales_container,
            text="SUBTOTAL: 0.00€",
            font=footer_font,
            text_color=footer_cfg.get("text", "#FFFFFF")
        )
        self.subtotal_label.pack(anchor="w", padx=12)

        self.total_label = ctk.CTkLabel(
            totales_container,
            text="TOTAL: 0.00€",
            font=footer_font,
            text_color=footer_cfg.get("text_totales", "#00FF00")
        )
        self.total_label.pack(anchor="e", padx=12)

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

    def update_totales(self, subtotal: float, total: float):
        """Actualizar totales del footer."""
        try:
            self.subtotal_label.configure(text=f"SUBTOTAL: {subtotal:.2f}€")
            self.total_label.configure(text=f"TOTAL: {total:.2f}€")
        except Exception:
            pass
