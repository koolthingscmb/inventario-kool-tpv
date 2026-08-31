"""Tab de configuración del Menú de producción."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font, get_chip_config, get_chip_style
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList


class ConfigTabMenu:
    """Pestaña MENÚ: 50% nav_list de menús | 50% chips de tipos."""

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        self._menu_id_edit = None
        self._nav = None
        self._tipos_chips = {}
        self._tipos_selected = set()
        self._all_tipos = []
        self._chip_cfg = get_chip_config(config, "producto")
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: nav_list de menús (50%) ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        columns = [
            ("nombre", 200, "NOMBRE"),
            ("ntipos", 60, "TIPOS"),
            ("estado", 40, "ACT"),
        ]
        self._nav = VirtualNavList(
            parent=frame_lista,
            columns=columns,
            on_select=self._on_selected,
            module_name="produccion",
            keyboard_manager=self._km,
            layout_config=self._layout_config,
        )
        self._nav.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Botones CRUD debajo de la lista
        frame_btns_left = tk.Frame(frame_lista, bg="#34495e")
        frame_btns_left.pack(fill="x", padx=6, pady=(0, 6))
        
        ButtonFactory.create_button(frame_btns_left, text="NUEVO", 
                                  module="produccion", palette_key="primary", style_key="action_confirm",
                                  command=self._limpiar).pack(side=tk.LEFT, padx=(0, 4), expand=True, fill=tk.X)
                                  
        ButtonFactory.create_button(frame_btns_left, text="ELIMINAR", 
                                  module="produccion", palette_key="accent", style_key="action_confirm",
                                  command=self._eliminar).pack(side=tk.LEFT, padx=(4, 0), expand=True, fill=tk.X)

        # --- DERECHA: formulario compacto + chips de tipos (50%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Formulario compacto arriba
        form_top = tk.Frame(frame_right, bg="#34495e")
        form_top.pack(fill="x", padx=10, pady=(8, 4))

        self._entry_nombre = ctk.CTkEntry(form_top, placeholder_text="Nombre del menú...", width=200)
        self._entry_nombre.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self._var_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(form_top, text="Activo", variable=self._var_activo,
                        fg_color="#552583", hover_color="#C77BFF", text_color="#FFFFFF").pack(side=tk.LEFT, padx=(0, 4))

        ButtonFactory.create_button(form_top, text="GUARDAR", 
                                  module="produccion", palette_key="primary", style_key="action_confirm",
                                  width=90, command=self._guardar).pack(side=tk.LEFT)

        # Botones de reordenación
        frame_reorder = tk.Frame(frame_right, bg="#34495e")
        frame_reorder.pack(fill="x", padx=10, pady=(0, 4))
        
        ButtonFactory.create_button(frame_reorder, text="⬆ SUBIR", 
                                  module="produccion", palette_key="secondary", style_key="action_confirm",
                                  command=lambda: self._mover(-1)).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
                                  
        ButtonFactory.create_button(frame_reorder, text="⬇ BAJAR", 
                                  module="produccion", palette_key="secondary", style_key="action_confirm",
                                  command=lambda: self._mover(1)).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        # Separador
        sep = tk.Frame(frame_right, bg="#1a252f", height=2)
        sep.pack(fill="x", padx=10, pady=4)

        # Label de tipos
        tk.Label(frame_right, text="TIPOS ASOCIADOS (click para toggle):",
                 font=get_font(self.config, "label"),
                 fg="#FFFFFF", bg="#34495e").pack(padx=10, pady=(4, 2), anchor="w")

        # Chips de tipos — scrollable, ocupa el resto
        self._tipos_scroll = ctk.CTkScrollableFrame(frame_right, fg_color="#2c3e50")
        self._tipos_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # Cargar todos los tipos activos, ordenados alfabéticamente
        self._all_tipos = sorted(self.service.tipos_repo.get_activos(), key=lambda t: t.nombre.lower())
        self._rebuild_tipos_chips()

        self._cargar_lista()

    def _cargar_lista(self):
        items_menu = self.service.obtener_todos_menu()
        items = []
        for m in items_menu:
            tipos_ids = self.service.obtener_tipos_id_por_menu(m.id)
            items.append({
                "id": m.id,
                "nombre": m.nombre,
                "ntipos": str(len(tipos_ids)),
                "estado": "✓" if m.activo else "✗",
                "_activo": m.activo,
            })
        self._nav.set_items(items)

    def _on_selected(self, data):
        self._menu_id_edit = data.get("id")
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, data.get("nombre", ""))
        self._var_activo.set(data.get("_activo", 1))

        # Cargar tipos asignados a este menú
        self._tipos_selected = self.service.obtener_tipos_id_por_menu(self._menu_id_edit)
        self._refresh_tipos_chips()

    def _rebuild_tipos_chips(self):
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipos_chips = {}

        cols = 5
        padx = 4
        pady = 4
        chip_height = 32
        corner_radius = 8

        default_style = get_chip_style(self._chip_cfg, "default")
        selected_style = get_chip_style(self._chip_cfg, "selected")
        font_family = get_font(self.config, self._chip_cfg.get("font_key", "label"))
        chip_font = (font_family[0], 12, font_family[2])

        grid_frame = tk.Frame(self._tipos_scroll, bg="#2c3e50")
        grid_frame.pack(fill="x", expand=True)

        for idx, tipo in enumerate(self._all_tipos):
            is_selected = tipo.id in self._tipos_selected
            chip = ctk.CTkButton(
                grid_frame,
                text=tipo.nombre,
                width=100,
                height=chip_height,
                corner_radius=corner_radius,
                font=chip_font,
                fg_color=selected_style.get("bg", "#552583") if is_selected else default_style.get("bg", "#1a1a2e"),
                text_color=selected_style.get("text", "#ffffff") if is_selected else default_style.get("text", "#e0e0e0"),
                border_color=selected_style.get("border", "#C77BFF") if is_selected else default_style.get("border", "#552583"),
                border_width=2 if is_selected else 1,
                hover_color=selected_style.get("hover", "#8e44ad") if is_selected else default_style.get("hover", "#C77BFF"),
                command=lambda tid=tipo.id: self._toggle_tipo(tid)
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=padx, pady=pady, sticky="ew")
            self._tipos_chips[tipo.id] = chip

        for j in range(cols):
            grid_frame.columnconfigure(j, weight=1)

    def _refresh_tipos_chips(self):
        default_style = get_chip_style(self._chip_cfg, "default")
        selected_style = get_chip_style(self._chip_cfg, "selected")
        for tid, chip in self._tipos_chips.items():
            is_selected = tid in self._tipos_selected
            chip.configure(
                fg_color=selected_style.get("bg", "#552583") if is_selected else default_style.get("bg", "#1a1a2e"),
                text_color=selected_style.get("text", "#ffffff") if is_selected else default_style.get("text", "#e0e0e0"),
                border_color=selected_style.get("border", "#C77BFF") if is_selected else default_style.get("border", "#552583"),
                border_width=2 if is_selected else 1
            )

    def _toggle_tipo(self, tipo_id):
        if tipo_id in self._tipos_selected:
            self._tipos_selected.discard(tipo_id)
        else:
            self._tipos_selected.add(tipo_id)
        self._refresh_tipos_chips()

    def _mover(self, direccion: int):
        if not self._menu_id_edit:
            return
        menu_id = self._menu_id_edit
        ok = self.service.mover_menu(menu_id, direccion)
        if ok:
            self._cargar_lista()
            for i, item in enumerate(self._nav._all_data):
                if item.get("id") == menu_id:
                    self._nav.selected_index = i
                    self._nav._refresh_ui()
                    if hasattr(self._nav, '_scroll_to_index'):
                        self._nav._scroll_to_index(i)
                    break

    def _guardar(self):
        nombre = self._entry_nombre.get().strip()
        if not nombre:
            return
        activo = self._var_activo.get()

        ok = self.service.guardar_menu(nombre, None, 0, activo, 0, self._menu_id_edit)
        if ok:
            if not self._menu_id_edit:
                items = self.service.obtener_todos_menu()
                for m in items:
                    if m.nombre == nombre:
                        self._menu_id_edit = m.id
                        break

            if self._menu_id_edit:
                self.service.actualizar_tipos_menu(self._menu_id_edit, list(self._tipos_selected))

            self._limpiar()
            self._cargar_lista()

    def _limpiar(self):
        self._menu_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._var_activo.set(1)
        self._tipos_selected = set()
        self._refresh_tipos_chips()

    def _eliminar(self):
        if self._menu_id_edit:
            self.service.eliminar_menu(self._menu_id_edit)
            self._limpiar()
            self._cargar_lista()

    def refresh_nav(self):
        if self._nav and hasattr(self._nav, '_refresh_ui'):
            self._nav.update_idletasks()
            self._nav._refresh_ui()
