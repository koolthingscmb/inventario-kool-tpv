"""Tab de configuración de la Matriz 3D (género → color → tallas)."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font


class ConfigTabMatriz:
    """Pestaña MATRIZ: gestiona relaciones género+color+talla."""

    _CHIP_NORMAL = "#34495e"
    _CHIP_SELECTED = "#9b59b6"
    _CHIP_COLOR_SEL = "#3498db"

    def __init__(self, parent, service, config, colors, km, layout_config):
        self.parent = parent
        self.service = service
        self.config = config
        self._colors = colors
        self._bg = colors.get("background", "#2c3e50")
        self._text = colors.get("text", "#ecf0f1")
        self._km = km
        self._layout_config = layout_config
        self.build()

    def build(self):
        self._all_colores = {c.id: c for c in self.service.obtener_todos_colores()}
        self._all_tallas = {t.id: t for t in self.service.obtener_todas_tallas()}
        generos = self.service.obtener_todos_generos()
        self._generos = {g.id: g for g in generos}
        self._selected_genero = None
        self._selected_color = None
        self._genero_chips = {}
        self._color_rows = {}
        self._talla_chips = {}
        self._colores_asignados = set()
        self._tallas_state = set()
        self._tallas_dirty = False
        self._last_talla_idx = None

        # Chips de géneros arriba
        top = tk.Frame(self.parent, bg=self._bg, height=40)
        top.pack(fill="x", pady=(5, 8))
        top.pack_propagate(False)
        tk.Label(top, text="GÉNEROS:", font=get_font(self.config, "label"),
                 fg=self._text, bg=self._bg).pack(side="left", padx=(0, 8))
        for g in generos:
            chip = tk.Label(top, text=g.nombre, font=get_font(self.config, "label"),
                            fg=self._text, bg=self._CHIP_NORMAL, padx=12, pady=4, cursor="hand2")
            chip.pack(side="left", padx=(0, 4))
            chip.bind("<Button-1>", lambda e, gid=g.id: self._select_genero(gid))
            self._genero_chips[g.id] = chip

        # Paneles lado a lado
        pf = tk.Frame(self.parent, bg=self._bg)
        pf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Izquierda: COLORES del género
        lp = tk.Frame(pf, bg="#34495e", bd=0, highlightthickness=0)
        lp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        lh = tk.Frame(lp, bg="#34495e")
        lh.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(lh, text="COLORES DEL GÉNERO", font=get_font(self.config, "label"),
                 fg="#FFD700", bg="#34495e").pack(side="left")
        ctk.CTkButton(lh, text="+ TODOS", width=70, height=26,
                      fg_color="#2980b9", hover_color="#3498db",
                      command=self._add_all_colores).pack(side="right", padx=(4, 0))
        ctk.CTkButton(lh, text="+ AÑADIR", width=80, height=26,
                      fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._add_color_dialog).pack(side="right")
        self._colores_scroll = ctk.CTkScrollableFrame(lp, fg_color="#34495e")
        self._colores_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Derecha: TALLAS del color seleccionado
        rp = tk.Frame(pf, bg="#34495e", bd=0, highlightthickness=0)
        rp.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self._tallas_label = tk.Label(rp, text="TALLAS", font=get_font(self.config, "label"),
                                      fg="#FFD700", bg="#34495e")
        self._tallas_label.pack(pady=(8, 3))
        self._tallas_scroll = ctk.CTkScrollableFrame(rp, fg_color="#34495e")
        self._tallas_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Botón guardar
        bf = tk.Frame(self.parent, bg=self._bg)
        bf.pack(pady=(5, 10))
        ctk.CTkButton(bf, text="GUARDAR", fg_color="#27ae60", hover_color="#2ecc71",
                      width=180, command=self._guardar).pack()

        if generos:
            self._select_genero(generos[0].id)

    def _select_genero(self, genero_id):
        self._save_tallas_if_dirty()
        self._selected_genero = genero_id
        self._selected_color = None
        for gid, chip in self._genero_chips.items():
            chip.configure(bg=self._CHIP_SELECTED if gid == genero_id else self._CHIP_NORMAL)
        self._colores_asignados = self.service.obtener_colores_genero_3d(genero_id)
        self._rebuild_colores()
        self._clear_tallas()

    def _rebuild_colores(self):
        for child in self._colores_scroll.winfo_children():
            child.destroy()
        self._color_rows = {}
        for cid in sorted(self._colores_asignados, key=lambda c: self._all_colores[c].nombre):
            color = self._all_colores[cid]
            row = tk.Frame(self._colores_scroll, bg="#34495e", height=32)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            hex_code = color.codigo_hex or "#888888"
            swatch = tk.Label(row, text="  ", bg=hex_code, width=3, relief="solid", bd=1)
            swatch.pack(side="left", padx=(4, 6), pady=4)
            lbl = tk.Label(row, text=color.nombre, font=get_font(self.config, "label"),
                           fg=self._text, bg="#34495e", cursor="hand2", padx=6)
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, c=cid: self._select_color(c))
            row.bind("<Button-1>", lambda e, c=cid: self._select_color(c))
            btn_x = tk.Label(row, text="✕", font=get_font(self.config, "label"),
                             fg="#e74c3c", bg="#34495e", cursor="hand2", padx=8)
            btn_x.pack(side="right")
            btn_x.bind("<Button-1>", lambda e, c=cid: self._remove_color(cid))
            self._color_rows[cid] = {"row": row, "lbl": lbl, "swatch": swatch}

    def _select_color(self, color_id):
        self._save_tallas_if_dirty()
        self._selected_color = color_id
        for cid, w in self._color_rows.items():
            bg = self._CHIP_COLOR_SEL if cid == color_id else "#34495e"
            w["row"].configure(bg=bg)
            w["lbl"].configure(bg=bg)
        self._tallas_state = self.service.obtener_tallas_genero_color_3d(
            self._selected_genero, color_id)
        self._tallas_dirty = False
        gn = self._generos[self._selected_genero].nombre
        cn = self._all_colores[color_id].nombre
        self._tallas_label.configure(text=f"TALLAS — {gn} / {cn}")
        self._rebuild_tallas()

    def _rebuild_tallas(self):
        for child in self._tallas_scroll.winfo_children():
            child.destroy()
        self._talla_chips = {}
        self._talla_order = []
        tallas_orden = sorted(self._all_tallas.keys(),
                              key=lambda t: self._all_tallas[t].orden)
        cols = 6
        for idx, tid in enumerate(tallas_orden):
            talla = self._all_tallas[tid]
            chip = tk.Label(self._tallas_scroll, text=talla.nombre,
                            font=get_font(self.config, "label"),
                            fg=self._text, bg=self._CHIP_NORMAL,
                            padx=12, pady=5, cursor="hand2")
            row = idx // cols
            col = idx % cols
            chip.grid(row=row, column=col, padx=4, pady=4, sticky="w")
            chip.bind("<Button-1>", lambda e, t=tid, i=idx: self._on_talla_click(e, t, i))
            self._talla_chips[tid] = chip
            self._talla_order.append(tid)
        self._refresh_tallas()

    def _clear_tallas(self):
        for child in self._tallas_scroll.winfo_children():
            child.destroy()
        self._talla_chips = {}
        self._tallas_label.configure(text="TALLAS")
        self._tallas_state = set()
        self._tallas_dirty = False

    def _on_talla_click(self, event, talla_id, idx):
        if not self._selected_color:
            return
        if event.state & 0x1 and self._last_talla_idx is not None:
            lo = min(self._last_talla_idx, idx)
            hi = max(self._last_talla_idx, idx)
            for i in range(lo, hi + 1):
                self._tallas_state.add(self._talla_order[i])
            self._tallas_dirty = True
            self._refresh_tallas()
        else:
            if talla_id in self._tallas_state:
                self._tallas_state.discard(talla_id)
            else:
                self._tallas_state.add(talla_id)
            self._tallas_dirty = True
            self._refresh_tallas()
        self._last_talla_idx = idx

    def _refresh_tallas(self):
        for tid, chip in self._talla_chips.items():
            chip.configure(bg=self._CHIP_SELECTED if tid in self._tallas_state else self._CHIP_NORMAL)

    def _add_color_dialog(self):
        if not self._selected_genero:
            return
        disponibles = [c for cid, c in self._all_colores.items()
                       if cid not in self._colores_asignados]
        if not disponibles:
            return
        win = tk.Toplevel(self.parent.winfo_toplevel())
        win.title("Añadir color al género")
        win.geometry("300x400")
        win.configure(bg=self._bg)
        win.transient(self.parent.winfo_toplevel())
        win.grab_set()
        tk.Label(win, text="Selecciona un color:", font=get_font(self.config, "label"),
                 fg=self._text, bg=self._bg).pack(pady=10)
        scroll = ctk.CTkScrollableFrame(win, fg_color=self._bg)
        scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for c in disponibles:
            row = tk.Frame(scroll, bg=self._bg, height=30)
            row.pack(fill="x", pady=2)
            swatch = tk.Label(row, text="  ", bg=c.codigo_hex or "#888", width=3, relief="solid", bd=1)
            swatch.pack(side="left", padx=(4, 8), pady=4)
            lbl = tk.Label(row, text=c.nombre, font=get_font(self.config, "label"),
                           fg=self._text, bg=self._bg, cursor="hand2", padx=6)
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, cid=c.id, w=win: self._do_add_color(cid, w))
            row.bind("<Button-1>", lambda e, cid=c.id, w=win: self._do_add_color(cid, w))

    def _add_all_colores(self):
        if not self._selected_genero:
            return
        for cid in self._all_colores:
            if cid not in self._colores_asignados:
                self._colores_asignados.add(cid)
        self._rebuild_colores()

    def _do_add_color(self, color_id, win):
        win.destroy()
        self._colores_asignados.add(color_id)
        self._rebuild_colores()
        self._select_color(color_id)

    def _remove_color(self, color_id):
        if not self._selected_genero:
            return
        self.service.eliminar_color_genero_3d(self._selected_genero, color_id)
        self._colores_asignados.discard(color_id)
        if self._selected_color == color_id:
            self._selected_color = None
            self._clear_tallas()
        self._rebuild_colores()

    def _save_tallas_if_dirty(self):
        if self._tallas_dirty and self._selected_genero and self._selected_color:
            self.service.guardar_tallas_genero_color_3d(
                self._selected_genero,
                self._selected_color,
                list(self._tallas_state))
            self._tallas_dirty = False

    def _guardar(self):
        self._save_tallas_if_dirty()
        from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
        ToastWidget.show(self.parent.winfo_toplevel(), "Matriz guardada correctamente", tipo="success")

    def refresh_nav(self):
        pass
