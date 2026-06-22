"""Tab de configuración del Menú de producción."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList


class ConfigTabMenu:
    """Pestaña MENÚ: 50% nav_list de menús | 50% chips de tipos."""

    _CHIP_NORMAL = "#34495e"
    _CHIP_SELECTED = "#27ae60"

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
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- IZQUIERDA: nav_list de menús (50%) ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        columns = [
            ("nombre", 160, "NOMBRE"),
            ("sistema", 100, "SISTEMA"),
            ("orden", 50, "ORDEN"),
            ("ntipos", 50, "TIPOS"),
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
        ctk.CTkButton(frame_btns_left, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar).pack(side=tk.LEFT, padx=(0, 4), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns_left, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar).pack(side=tk.LEFT, padx=(4, 0), expand=True, fill=tk.X)

        # --- DERECHA: formulario compacto + chips de tipos (50%) ---
        frame_right = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # Formulario compacto arriba
        form_top = tk.Frame(frame_right, bg="#34495e")
        form_top.pack(fill="x", padx=10, pady=(8, 4))

        self._entry_nombre = ctk.CTkEntry(form_top, placeholder_text="Nombre del menú...", width=200)
        self._entry_nombre.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        self._entry_orden = ctk.CTkEntry(form_top, placeholder_text="Orden", width=60)
        self._entry_orden.pack(side=tk.LEFT, padx=(0, 4))

        self._var_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(form_top, text="Activo", variable=self._var_activo,
                        fg_color="#27ae60", text_color=self._text).pack(side=tk.LEFT, padx=(0, 4))

        ctk.CTkButton(form_top, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      width=90, command=self._guardar).pack(side=tk.LEFT)

        # Entry de sistema (segunda fila)
        form_row2 = tk.Frame(frame_right, bg="#34495e")
        form_row2.pack(fill="x", padx=10, pady=(0, 4))
        self._entry_sistema = ctk.CTkEntry(form_row2, placeholder_text="Sistema (DTG, Sublimación...) opcional", width=300)
        self._entry_sistema.pack(fill=tk.X)

        # Separador
        sep = tk.Frame(frame_right, bg="#1a252f", height=2)
        sep.pack(fill="x", padx=10, pady=4)

        # Label de tipos
        tk.Label(frame_right, text="TIPOS ASOCIADOS (click para toggle):",
                 font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(padx=10, pady=(4, 2), anchor="w")

        # Chips de tipos — scrollable, ocupa el resto
        self._tipos_scroll = ctk.CTkScrollableFrame(frame_right, fg_color="#2c3e50")
        self._tipos_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # Cargar todos los tipos activos
        self._all_tipos = self.service.tipos_repo.get_activos()
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
                "sistema": m.sistema_produccion or "",
                "orden": str(m.orden),
                "ntipos": str(len(tipos_ids)),
                "estado": "✓" if m.activo else "✗",
                "_sistema": m.sistema_produccion,
                "_activo": m.activo,
            })
        self._nav.set_items(items)

    def _on_selected(self, data):
        self._menu_id_edit = data.get("id")
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, data.get("nombre", ""))
        self._entry_sistema.delete(0, tk.END)
        self._entry_sistema.insert(0, data.get("_sistema") or "")
        self._entry_orden.delete(0, tk.END)
        self._entry_orden.insert(0, data.get("orden", "0"))
        self._var_activo.set(data.get("_activo", 1))

        # Cargar tipos asignados a este menú
        self._tipos_selected = self.service.obtener_tipos_id_por_menu(self._menu_id_edit)
        self._refresh_tipos_chips()

    def _rebuild_tipos_chips(self):
        for child in self._tipos_scroll.winfo_children():
            child.destroy()
        self._tipos_chips = {}

        cols = 3
        for idx, tipo in enumerate(self._all_tipos):
            chip = tk.Label(
                self._tipos_scroll, text=tipo.nombre,
                font=get_font(self.config, "label"),
                fg=self._text,
                bg=self._CHIP_NORMAL,
                padx=10, pady=5, cursor="hand2"
            )
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            chip.bind("<Button-1>", lambda e, tid=tipo.id: self._toggle_tipo(tid))
            self._tipos_chips[tipo.id] = chip

        self._refresh_tipos_chips()

    def _refresh_tipos_chips(self):
        for tid, chip in self._tipos_chips.items():
            chip.configure(bg=self._CHIP_SELECTED if tid in self._tipos_selected else self._CHIP_NORMAL)

    def _toggle_tipo(self, tipo_id):
        if tipo_id in self._tipos_selected:
            self._tipos_selected.discard(tipo_id)
        else:
            self._tipos_selected.add(tipo_id)
        chip = self._tipos_chips.get(tipo_id)
        if chip:
            chip.configure(bg=self._CHIP_SELECTED if tipo_id in self._tipos_selected else self._CHIP_NORMAL)

    def _guardar(self):
        nombre = self._entry_nombre.get().strip()
        if not nombre:
            return
        sistema = self._entry_sistema.get().strip()
        try:
            orden = int(self._entry_orden.get().strip() or "0")
        except ValueError:
            orden = 0
        activo = self._var_activo.get()

        ok = self.service.guardar_menu(nombre, sistema, orden, activo, 0, self._menu_id_edit)
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
        self._entry_sistema.delete(0, tk.END)
        self._entry_orden.delete(0, tk.END)
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
