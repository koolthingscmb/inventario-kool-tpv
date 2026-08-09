"""Subvista de selección de método de impresión."""
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, List, Optional
import customtkinter as ctk
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.tipos_variantes_metodos_service import TiposVariantesMetodosService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_chip_config, get_chip_style, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.keyboard_nav_mixin import KeyboardNavigableMixin

@dataclass
class MetodoSeleccion:
    id: int
    nombre: str

class NuevaProduccionMetodoView(ctk.CTkFrame, KeyboardNavigableMixin):
    def __init__(self, parent, db: Database, variante_id: int, on_siguiente=None, on_volver=None):
        # Cargar configuración
        self.config = cargar_config_produccion()
        c = self.config.get("colors", {})
        self._bg = c.get("background", "#2c3e50")

        # Inicializar como CTkFrame
        ctk.CTkFrame.__init__(self, parent, fg_color=self._bg)
        KeyboardNavigableMixin.__init_keyboard_mixin__(self)

        self.db, self.on_siguiente, self.on_volver = db, on_siguiente, on_volver
        self._variante_id, self.metodo_seleccionado, self._chip_buttons, self._selected_chip = variante_id, None, [], None
        self._service = TiposVariantesMetodosService(db)
        
        self._text, self._text_sec = c.get("text", "#ecf0f1"), c.get("text_secondary", "#95a5a6")
        self._chip_cfg = get_chip_config(self.config, "producto")
        
        self.pack(fill="both", expand=True)
        
        ctk.CTkLabel(self, text="SELECCIONA MÉTODO", font=get_font(self.config, "title"), text_color=self._text).pack(pady=20)
        self._crear_chips()
        self._crear_botones()
        self._setup_nav()

    def _crear_chips(self):
        self.chips_frame = ctk.CTkScrollableFrame(self, fg_color=self._bg, label_text="")
        self.chips_frame.pack(expand=True, fill="both", padx=40, pady=20)

        metodos = self._service.obtener_metodos_por_variante(self._variante_id)
        if not metodos:
            ctk.CTkLabel(self.chips_frame, text="Sin métodos configurados para esta variante",
                         font=get_font(self.config, "label"), text_color=self._text_sec).pack(pady=40)
            return

        # Obtener configuración de chips
        cols = self._chip_cfg.get("columns", 4)
        padx = self._chip_cfg.get("padx", 8)
        pady = self._chip_cfg.get("pady", 8)
        chip_height = self._chip_cfg.get("height", 48)
        corner_radius = self._chip_cfg.get("corner_radius", 16)
        
        default_style = get_chip_style(self._chip_cfg, "default")
        font_family = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        chip_font = (font_family[0], default_style.get("font_size", 14), font_family[2])

        for i, m in enumerate(metodos):
            btn = ctk.CTkButton(
                self.chips_frame,
                text=m["nombre"],
                fg_color=default_style.get("bg", "#1a1a2e"),
                text_color=default_style.get("text", "#e0e0e0"),
                border_color=default_style.get("border", "#552583"),
                hover_color=default_style.get("hover", "#C77BFF"),
                border_width=default_style.get("border_width", 1),
                corner_radius=corner_radius,
                height=chip_height,
                font=chip_font,
                cursor="hand2"
            )
            # Asignamos el command después para poder pasar el propio objeto btn
            btn.configure(command=lambda b=btn, d=m: self._on_chip_click(b, d))
            
            row = i // cols
            col = i % cols
            btn.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")
            
            # El click con ratón también lo manejamos explícitamente si es necesario, 
            # aunque el command ya cubre click izquierdo.
            # Pero para consistencia con el resto del flujo:
            btn.bind("<Button-1>", lambda e, b=btn, d=m: self._click(b, d))
            
            setattr(btn, "_metodo_data", m)
            self._chip_buttons.append(btn)

        for j in range(cols):
            self.chips_frame.columnconfigure(j, weight=1)
        for j in range((len(metodos)+cols-1)//cols):
            self.chips_frame.rowconfigure(j, weight=1)

    def _on_chip_click(self, btn, m):
        """Manejador para el command del botón (click o Enter)."""
        if self._selected_chip == btn:
            # Si ya está seleccionado, el Enter (o click) debería avanzar al siguiente paso
            # para dar una sensación de fluidez
            self._on_siguiente()
        else:
            self._click(btn, m)

    def _click(self, btn, m):
        if self._selected_chip:
            self._sty(self._selected_chip, "default")
        self._selected_chip, self.metodo_seleccionado = btn, MetodoSeleccion(id=m["id"], nombre=m["nombre"])
        self._sty(btn, "selected")

    def _sty(self, btn, st):
        style = get_chip_style(self._chip_cfg, st)
        ff = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        btn.configure(
            fg_color=style.get("bg", "#1a1a2e"),
            text_color=style.get("text", "#e0e0e0"),
            border_color=style.get("border", "#552583"),
            hover_color=style.get("hover", "#C77BFF"),
            border_width=style.get("border_width", 2 if st == "selected" else 1),
            font=(ff[0], style.get("font_size", 14), ff[2])
        )

    def _crear_botones(self):
        fn = ctk.CTkFrame(self, fg_color=self._bg)
        fn.pack(fill="x", padx=40, pady=20)
        nv, ns = get_nav_button_config(self.config, "volver"), get_nav_button_config(self.config, "siguiente")
        sv, ss = get_nav_button_style(self.config, nv.get("style_key", "volver")), get_nav_button_style(self.config, ns.get("style_key", "siguiente"))

        self.btn_volver = ctk.CTkButton(
            fn, text=nv.get("text", "VOLVER"),
            font=get_font(self.config, nv.get("font_key", "button")),
            fg_color=sv.get("bg", "#e74c3c"), text_color=sv.get("text", "#FFF"),
            hover_color=sv.get("hover", "#c0392b"),
            border_color=sv.get("border", "#e74c3c"),
            border_width=sv.get("focus_thickness", 0),
            width=nv.get("width", 15)*10,
            height=nv.get("height", 2)*20,
            cursor="hand2",
            command=self._on_volver
        )
        self.btn_volver.pack(side=tk.LEFT, padx=10)

        self.btn_siguiente = ctk.CTkButton(
            fn, text=ns.get("text", "SIGUIENTE"),
            font=get_font(self.config, ns.get("font_key", "button")),
            fg_color=ss.get("bg", "#27ae60"), text_color=ss.get("text", "#FFF"),
            hover_color=ss.get("hover", "#2ecc71"),
            border_color=ss.get("border", "#1C0629"),
            border_width=ss.get("focus_thickness", 0),
            width=ns.get("width", 15)*10,
            height=ns.get("height", 2)*20,
            cursor="hand2",
            command=self._on_siguiente
        )
        self.btn_siguiente.pack(side=tk.RIGHT, padx=10)

    def _on_volver(self):
        if self.on_volver: self.on_volver()

    def _on_siguiente_handler(self):
        if self.metodo_seleccionado and self.on_siguiente: self.on_siguiente(self.metodo_seleccionado)

    def _setup_nav(self):
        self._navigable_buttons = [(b, lambda b=b, m=getattr(b, '_metodo_data', None): self._nav_cb(b, m)) for b in self._chip_buttons]
        self._navigable_buttons.extend([(self.btn_volver, self._on_volver), (self.btn_siguiente, self._on_siguiente_handler)])
        
        # Usar el método del mixin para configurar todo
        self._setup_keyboard_navigation()
        
        # Foco inicial
        if self._chip_buttons:
            self.after(100, lambda: self._focus_nav_widget(0))

    def _nav_cb(self, btn, m):
        if self._selected_chip == btn:
            self._on_siguiente_handler()
        elif m:
            self._click(btn, m)

    def destruir(self):
        self.clear_keyboard_navigation(); self.destroy()
