"""Tab de configuración de tallas del taller."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList


class ConfigTabTallas:
    """Sub-pestaña TALLAS: lista + formulario CRUD."""

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        self._talla_id_edit = None
        self._nav = None
        self.build()

    def build(self):
        content = tk.Frame(self.parent, bg=self._bg)
        content.pack(fill=tk.BOTH, expand=True)

        # --- Lista (izquierda) ---
        frame_lista = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = [
            ("nombre", 260, "NOMBRE"),
            ("estado", 60, "ACT"),
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

        # --- Formulario (derecha) ---
        frame_form = tk.Frame(content, bg="#34495e", bd=0, highlightthickness=0, width=300)
        frame_form.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_form.pack_propagate(False)

        tk.Label(frame_form, text="Editar / Crear talla", font=get_font(self.config, "label"),
                 fg=self._text, bg="#34495e").pack(pady=(10, 5))

        self._entry_nombre = ctk.CTkEntry(frame_form, placeholder_text="Nombre (S, M, L, XL...)", width=250)
        self._entry_nombre.pack(pady=5, padx=20)

        self._var_activo = ctk.IntVar(value=1)
        ctk.CTkCheckBox(frame_form, text="Activo", variable=self._var_activo,
                        fg_color="#27ae60", text_color=self._text).pack(pady=5, padx=20, anchor="w")

        frame_reorder = tk.Frame(frame_form, bg="#34495e")
        frame_reorder.pack(pady=(5, 0), padx=20, fill=tk.X)
        ctk.CTkButton(frame_reorder, text="⬆ SUBIR", fg_color="#7f8c8d", hover_color="#95a5a6",
                      command=lambda: self._mover(-1)).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_reorder, text="⬇ BAJAR", fg_color="#7f8c8d", hover_color="#95a5a6",
                      command=lambda: self._mover(1)).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        frame_btns = tk.Frame(frame_form, bg="#34495e")
        frame_btns.pack(pady=15, padx=20, fill=tk.X)

        ctk.CTkButton(frame_btns, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._guardar).pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        ctk.CTkButton(frame_btns, text="NUEVO", fg_color="#2980b9", hover_color="#3498db",
                      command=self._limpiar).pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

        ctk.CTkButton(frame_form, text="ELIMINAR", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._eliminar, width=250).pack(pady=(0, 10), padx=20, fill=tk.X)

        # --- Añadir múltiples tallas ---
        tk.Label(frame_form, text="Añadir varias (separadas por coma):",
                 font=get_font(self.config, "small"), fg=self._text, bg="#34495e").pack(pady=(5, 2), padx=20, anchor="w")
        self._entry_bulk = ctk.CTkEntry(frame_form, placeholder_text="S, M, L, XL, XXL...", width=250)
        self._entry_bulk.pack(pady=2, padx=20, fill=tk.X)
        self._entry_bulk.bind('<Return>', lambda e: self._anadir_bulk())
        ctk.CTkButton(frame_form, text="AÑADIR VARIAS", fg_color="#8e44ad", hover_color="#9b59b6",
                      command=self._anadir_bulk, width=250).pack(pady=(2, 15), padx=20, fill=tk.X)

        self._cargar_lista()

    def _cargar_lista(self):
        tallas = self.service.obtener_todas_tallas()
        items = [{
            "id": t.id,
            "nombre": t.nombre,
            "estado": "✓" if t.activo else "✗",
            "_activo": t.activo,
        } for t in tallas]
        self._nav.set_items(items)

    def _on_selected(self, data):
        self._talla_id_edit = data.get("id")
        self._entry_nombre.delete(0, tk.END)
        self._entry_nombre.insert(0, data.get("nombre", ""))
        self._var_activo.set(data.get("_activo", 1))

    def _mover(self, direccion: int):
        if not self._talla_id_edit:
            return
        talla_id = self._talla_id_edit
        ok = self.service.mover_talla(talla_id, direccion)
        if ok:
            self._cargar_lista()
            for i, item in enumerate(self._nav._all_data):
                if item.get("id") == talla_id:
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
        ok = self.service.guardar_talla(nombre, 0, activo, self._talla_id_edit)
        if ok:
            self._limpiar()
            self._cargar_lista()

    def _limpiar(self):
        self._talla_id_edit = None
        self._entry_nombre.delete(0, tk.END)
        self._var_activo.set(1)

    def _anadir_bulk(self):
        texto = self._entry_bulk.get().strip()
        if not texto:
            return
        nombres = [n.strip().upper() for n in texto.split(",") if n.strip()]
        if not nombres:
            return
        for nombre in nombres:
            self.service.guardar_talla(nombre, 0, 1, None)
        self._entry_bulk.delete(0, tk.END)
        self._limpiar()
        self._cargar_lista()

    def _eliminar(self):
        if self._talla_id_edit:
            self.service.tallas_repo.eliminar(self._talla_id_edit)
            self._limpiar()
            self._cargar_lista()

    def refresh_nav(self):
        if self._nav and hasattr(self._nav, '_refresh_ui'):
            self._nav.update_idletasks()
            self._nav._refresh_ui()
