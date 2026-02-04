"""kool_tpv.modulos.tpv.tpv_view

Vista estática y receptiva del módulo TPV.

Características principales:
- `BUTTON_CONFIG` editable en la parte superior para texto y color.
- Botón de búsqueda (botón ancho, no entrada) con tamaño base ~1000x60 pero responsive.
- Grid de 4x3 botones grandes (texto en mayúsculas).
- Comportamiento responsive: los botones y las fuentes escalan al redimensionar.
- `show()` construye la vista, `teardown()` cancela tareas y unbinds.

Diseñado para ser legible y modificable; no incluye lógica de negocio.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict
import logging
import json
from pathlib import Path

import customtkinter as ctk


# --- Configuración editable de botones (texto y color). Modifica aquí. ---
BUTTON_CONFIG: List[Dict[str, str]] = [
    {"text": "COBRAR", "color": "#E27D60"},
    {"text": "PENDIENTE", "color": "#C38D9E"},
    {"text": "DESCUENTO", "color": "#41B3A3"},
    {"text": "CLIENTE", "color": "#6B5B95"},
    {"text": "PRODUCTOS", "color": "#FF6F61"},
    {"text": "CANCELAR", "color": "#F7CAC9"},
    {"text": "BUSCAR", "color": "#92A8D1"},
    {"text": "REIMPRIMIR", "color": "#034F84"},
    {"text": "RECARGO", "color": "#F7B32B"},
    {"text": "IMPRIMIR", "color": "#88B04B"},
    {"text": "CONFIG", "color": "#6C5B7B"},
    {"text": "OTROS", "color": "#2E8B57"},
]


def load_button_config_from_json() -> List[Dict]:
    """Attempt to read button definitions from kool_tpv/config/buttons_config.json.

    Returns a list of button config dicts. If the file is missing or invalid,
    returns the in-code BUTTON_CONFIG as fallback (mapped to same shape).
    """
    try:
        base = Path(__file__).resolve().parents[2]  # kool_tpv/
        cfg_file = base / "config" / "buttons_config.json"
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            buttons = data.get("buttons") or []
            parsed = []
            for b in buttons:
                parsed.append(
                    {
                        "text": b.get("label", ""),
                        "color": b.get("color", "#CCCCCC"),
                        "hover_color": b.get("hover_color"),
                        "font_size": b.get("font_size"),
                        "width": b.get("width"),
                        "height": b.get("height"),
                        "command": b.get("command"),
                    }
                )
            if parsed:
                return parsed
    except Exception:
        logging.exception("Error leyendo buttons_config.json")

    # Fallback: map BUTTON_CONFIG to expected shape
    fallback = []
    for b in BUTTON_CONFIG:
        fallback.append({
            "text": b.get("text"),
            "color": b.get("color"),
            "hover_color": None,
            "font_size": None,
            "width": None,
            "height": None,
            "command": None,
        })
    return fallback

# Tamaños base / constantes
RIGHT_WIDTH = 420
INFO_BAR_HEIGHT = 90
# Hover color shared with main navigation
HOVER_COLOR = "#00A4DF"


class ButtonFactory:
    """Factory simple para crear botones reutilizables en TPV.

    - Convierte `text` a mayúsculas automáticamente.
    - Todos los parámetros de estilo son modificables desde el llamador.
    """

    @staticmethod
    def create_button(
        parent,
        text: str,
        command=None,
        font=("Arial", 14),
        color="#FFFFFF",
        text_color="black",
        hover_color=None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        corner_radius: int = 12,
        **kwargs,
    ) -> ctk.CTkButton:
        # Use shared HOVER_COLOR when none provided
        _hover = hover_color if hover_color is not None else HOVER_COLOR
        return ctk.CTkButton(
            master=parent,
            text=(text or "").upper(),
            command=command,
            fg_color=color,
            hover_color=_hover,
            text_color=text_color,
            width=width,
            height=height,
            font=font,
            corner_radius=corner_radius,
            **kwargs,
        )


class TpvView:
    """Vista TPV responsiva y limpia.

    Uso:
        view = TpvView(parent_frame, db=optional_db)
        view.show()
        view.teardown()  # al cerrar la vista
    """

    def __init__(self, parent: ctk.CTkFrame, db: Optional[object] = None):
        self.parent = parent
        self.db = db
        self._clock_job = None
        self.info_label: Optional[ctk.CTkLabel] = None
        self._resize_bound = False

        # Referencias a widgets que necesitamos actualizar/teardown
        self.action_panel: Optional[ctk.CTkFrame] = None
        self.right_container: Optional[ctk.CTkFrame] = None
        self.grid_frame: Optional[ctk.CTkFrame] = None
        self.search_button: Optional[ctk.CTkButton] = None
        self.grid_buttons: List[ctk.CTkButton] = []

    # ---------------------- Reloj y teardown ----------------------
    def _update_clock(self, cashier_name: str) -> None:
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            info_text = f"KOOL TPV V1.0 - {now_str}\n{cashier_name}"
            if self.info_label:
                self.info_label.configure(text=info_text)
            # programar siguiente actualización
            if self.parent is not None:
                self._clock_job = self.parent.after(1000, lambda: self._update_clock(cashier_name))
        except Exception:
            logging.exception("Error actualizando reloj TPV")

    def teardown(self) -> None:
        # Cancelar after() y desbind si es necesario
        try:
            if self._clock_job and self.parent is not None:
                self.parent.after_cancel(self._clock_job)
                self._clock_job = None
        except Exception:
            logging.exception("Error cancelando reloj TPV")

        try:
            if self._resize_bound and self.parent is not None:
                self.parent.unbind("<Configure>")
                self._resize_bound = False
        except Exception:
            logging.exception("Error desbind resize TPV")

    # ---------------------- Responsive resizing ----------------------
    def _on_resize(self, event=None) -> None:
        """Recalcula tamaños y fuentes de los botones para comportamiento responsive."""
        try:
            total_w = max(1, self.parent.winfo_width())
            total_h = max(1, self.parent.winfo_height())

            # espacio reservado para la columna derecha fija
            right_w = RIGHT_WIDTH
            action_w = max(200, total_w - right_w)

            # grid: 4 columnas x 3 filas
            cols = 4
            rows = 3
            spacing = 12
            horizontal_padding = spacing * (cols + 1)
            vertical_padding = spacing * (rows + 1)

            # espacio disponible para botones
            available_w = max(100, action_w - horizontal_padding)
            available_h = max(100, total_h - INFO_BAR_HEIGHT - vertical_padding - 120)

            btn_w = int(available_w / cols)
            btn_h = int(available_h / rows)

            # elegir tamaño cuadrado para botones, limitado
            btn_size = max(80, min(btn_w, btn_h, 400))

            # Tamaño del search button: ancho completo del action panel menos márgenes
            search_h = int(max(40, min(80, total_h * 0.07)))
            search_w = max(300, action_w - 40)

            # Tamaños de fuente heurísticos
            btn_font_size = max(12, int(btn_size * 0.20))
            search_font_size = max(14, int(search_h * 0.45))

            # Aplicar al botón de búsqueda
            if self.search_button:
                try:
                    self.search_button.configure(width=search_w, height=search_h, font=("Impact", search_font_size))
                except Exception:
                    logging.exception("Error ajustando search_button")

            # Aplicar a botones de la grid
            for b in self.grid_buttons:
                try:
                    b.configure(width=btn_size, height=btn_size, font=("Impact", btn_font_size))
                except Exception:
                    logging.exception("Error ajustando grid button")
        except Exception:
            logging.exception("Error en _on_resize TPV")

    # ---------------------- Construcción de la vista ----------------------
    def show(self) -> None:
        # Limpiar contenedor
        for w in list(self.parent.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass

        # Left action panel
        self.action_panel = ctk.CTkFrame(self.parent, fg_color="#393E46")
        self.action_panel.pack(side="left", fill="both", expand=True)
        self.action_panel.pack_propagate(False)

        # Search button (ancho grande, comportamiento como botón)
        self.search_button = ButtonFactory.create_button(
            parent=self.action_panel,
            text="BUSCAR ARTÍCULO",
            command=lambda: logging.info("Acción: BUSCAR ARTÍCULO"),
            font=("Impact", 24),
            color="#00BFFF",
            text_color="#000000",
            hover_color="#00A4DF",
            width=1000,
            height=60,
            corner_radius=18,
        )
        self.search_button.pack(pady=(18, 8), padx=20)

        # Grid frame para 4x3 botones
        self.grid_frame = ctk.CTkFrame(self.action_panel, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Crear botones desde configuración JSON (o fallback interno)
        self.grid_buttons = []
        cfg_list = load_button_config_from_json()
        # ensure we have at least 12 entries by repeating if necessary
        if len(cfg_list) < 12:
            times = (12 + len(cfg_list) - 1) // max(1, len(cfg_list)) if cfg_list else 12
            cfg_list = (cfg_list * times)[:12]

        for idx in range(12):
            cfg = cfg_list[idx]
            row = idx // 4
            col = idx % 4
            # derive font tuple
            font_size = cfg.get("font_size") or 36
            font = ("Impact", int(font_size))
            btn_width = cfg.get("width") or 200
            btn_height = cfg.get("height") or 200
            hover = cfg.get("hover_color")
            btn = ButtonFactory.create_button(
                parent=self.grid_frame,
                text=cfg.get("text", f"BTN{idx+1}"),
                command=(lambda name=cfg.get("command", cfg.get("text")): logging.info(f"Acción '{name}' pulsada")),
                font=font,
                color=cfg.get("color", "#CCCCCC"),
                text_color="#000000",
                hover_color=hover,
                width=btn_width,
                height=btn_height,
                corner_radius=28,
            )
            btn.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
            self.grid_frame.grid_columnconfigure(col, weight=1)
            self.grid_frame.grid_rowconfigure(row, weight=1)
            self.grid_buttons.append(btn)

        # Right container (fijo en la derecha)
        self.right_container = ctk.CTkFrame(self.parent, fg_color="#222831", width=RIGHT_WIDTH)
        self.right_container.pack(side="right", fill="y")
        self.right_container.pack_propagate(False)

        # Info bar (blanca) encima del cart_view
        info_bar = ctk.CTkFrame(self.right_container, height=INFO_BAR_HEIGHT, fg_color="#FFFFFF")
        info_bar.pack(side="top", fill="x")
        info_bar.pack_propagate(False)

        # Recuperar nombre del cajero si está disponible
        cashier_name = "Nombre Cajero"
        try:
            if self.db is not None:
                getter = getattr(self.db, "get_active_cashier", None)
                if callable(getter):
                    result = getter()
                    if isinstance(result, str) and result:
                        cashier_name = result
                    elif isinstance(result, dict) and result.get("name"):
                        cashier_name = result.get("name")
        except Exception:
            logging.exception("Error recuperando nombre cajero")

        # Info label (actualizable)
        self.info_label = ctk.CTkLabel(
            info_bar,
            text="",
            font=("Arial", 18),
            text_color="#000000",
            anchor="center",
            justify="center",
        )
        self.info_label.pack(fill="both", expand=True)

        # Cart view (negra)
        cart_view = ctk.CTkFrame(self.right_container, fg_color="#000000")
        cart_view.pack(side="top", fill="both", expand=True)
        cart_view.pack_propagate(False)

        # Iniciar reloj
        try:
            self._update_clock(cashier_name)
        except Exception:
            logging.exception("Error iniciando reloj")

        # Bind resize para comportamiento responsive
        try:
            if not self._resize_bound:
                self.parent.bind("<Configure>", lambda e: self._on_resize(e))
                self._resize_bound = True
            # ajuste inicial
            self._on_resize()
        except Exception:
            logging.exception("Error bind resize TPV")


# Export limpio
__all__ = ["TpvView", "ButtonFactory", "BUTTON_CONFIG"]

