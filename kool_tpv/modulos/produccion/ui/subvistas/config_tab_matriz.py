"""Tab de configuración de la Matriz 3D (género → color → tallas)."""
import tkinter as tk
import customtkinter as ctk

from kool_tpv.modulos.produccion.ui.subvistas.config_helper import get_font


class ConfigTabMatriz:
    """Pestaña MATRIZ: gestiona relaciones género+color+talla."""

    _CHIP_NORMAL = "#34495e"
    _CHIP_SELECTED = "#27ae60"
    _CHIP_COLOR_SEL = "#3498db"
    _CHIP_NO_STOCK = "#2c2c2c"
    _CHIP_NO_STOCK_FG = "#666666"

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
        
        # Estado
        self._selected_id = None
        self._selected_variante_id = None
        self._selected_color = None
        self._chip_widgets = {}
        self._variante_widgets = {}
        self._color_rows = {}
        self._talla_chips = {}
        self._colores_asignados = set()
        self._tallas_state = set()
        self._tallas_dirty = False
        self._last_talla_idx = None
        self._stock_actual = {}

        # --- BARRA SUPERIOR: Chips ---
        self._header = tk.Frame(self.parent, bg=self._bg)
        self._header.pack(fill="x", pady=(5, 8))

        # Scroll de Chips
        self._chips_scroll = ctk.CTkScrollableFrame(
            self._header, fg_color=self._bg, height=45, orientation="horizontal"
        )
        self._chips_scroll.pack(side="left", fill="x", expand=True)

        # Barra de Variantes (se muestra solo en modo TIPOS y si hay variantes)
        self._variante_frame = tk.Frame(self.parent, bg=self._bg)
        # Se empaqueta inicialmente para reservar el sitio, luego se oculta si no hace falta
        self._variante_frame.pack(fill="x", padx=10, pady=(0, 5))
        self._variante_scroll = ctk.CTkScrollableFrame(
            self._variante_frame, fg_color=self._bg, height=40, orientation="horizontal"
        )
        self._variante_scroll.pack(fill="x", expand=True)
        self._variante_frame.pack_forget() 

        # Paneles lado a lado
        self._paneles_frame = tk.Frame(self.parent, bg=self._bg)
        self._paneles_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Izquierda: COLORES
        lp = tk.Frame(self._paneles_frame, bg="#34495e", bd=0, highlightthickness=0)
        lp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        lh = tk.Frame(lp, bg="#34495e")
        lh.pack(fill="x", padx=8, pady=(8, 3))
        self.lbl_colores_title = tk.Label(lh, text="COLORES", font=get_font(self.config, "label"),
                                         fg="#FFD700", bg="#34495e")
        self.lbl_colores_title.pack(side="left")
        
        ctk.CTkButton(lh, text="+ TODOS", width=70, height=26,
                      fg_color="#2980b9", hover_color="#3498db",
                      command=self._add_all_colores).pack(side="right", padx=(4, 0))
        ctk.CTkButton(lh, text="+ AÑADIR", width=80, height=26,
                      fg_color="#27ae60", hover_color="#2ecc71",
                      command=self._add_color_dialog).pack(side="right")
        self._colores_scroll = ctk.CTkScrollableFrame(lp, fg_color="#34495e")
        self._colores_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Derecha: TALLAS
        rp = tk.Frame(self._paneles_frame, bg="#34495e", bd=0, highlightthickness=0)
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

        # Cargar datos iniciales
        self._rebuild_chips()

    def _rebuild_chips(self):
        """Reconstruir los chips de tipos."""
        for child in self._chips_scroll.winfo_children():
            child.destroy()
        self._chip_widgets = {}

        items = self.service.obtener_tipos_para_matriz()

        for item in items:
            chip = tk.Label(
                self._chips_scroll, text=item.nombre, font=get_font(self.config, "label"),
                fg=self._text, bg=self._CHIP_NORMAL, padx=12, pady=4, cursor="hand2"
            )
            chip.pack(side="left", padx=(0, 4))
            chip.bind("<Button-1>", lambda e, i=item.id: self._select_item(i))
            self._chip_widgets[item.id] = chip

        if items:
            self._select_item(items[0].id)

    def _select_item(self, item_id):
        self._save_tallas_if_dirty()
        self._selected_id = item_id
        self._selected_variante_id = None
        self._selected_color = None
        
        for i_id, chip in self._chip_widgets.items():
            chip.configure(bg=self._CHIP_SELECTED if i_id == item_id else self._CHIP_NORMAL)
        
        # Cargar variantes
        self._rebuild_variante_chips(item_id)

        # Cargar colores asignados
        self._colores_asignados = self.service.obtener_colores_tipo_3d(item_id, self._selected_variante_id)
        self.lbl_colores_title.configure(text="COLORES DEL TIPO")
            
        self._rebuild_colores()
        self._clear_tallas()

    def _rebuild_variante_chips(self, tipo_id):
        """Reconstruir chips de variantes para el tipo seleccionado."""
        for child in self._variante_scroll.winfo_children():
            child.destroy()
        self._variante_widgets = {}

        # Obtener variantes que requieren matriz
        variantes = self.service.obtener_variantes_por_tipo(tipo_id, solo_matriz=True)
        
        if not variantes:
            self._variante_frame.pack_forget()
            return

        # IMPORTANTE: Asegurar que se empaqueta justo debajo de la cabecera
        self._variante_frame.pack(fill="x", padx=10, pady=(0, 5), after=self._header)
        
        # Chip para "SIN VARIANTE" o "GENERAL" si el tipo también lo requiere
        tipo = self.service.obtener_por_id(tipo_id)
        if tipo and (tipo.requiere_color == 1 or tipo.requiere_talla == 1):
            v_chip = tk.Label(
                self._variante_scroll, text="[ GENERAL ]", font=get_font(self.config, "label"),
                fg=self._text, bg=self._CHIP_SELECTED, padx=10, pady=2, cursor="hand2"
            )
            v_chip.pack(side="left", padx=(0, 4))
            v_chip.bind("<Button-1>", lambda e: self._select_variante(None))
            self._variante_widgets[None] = v_chip

        for v in variantes:
            v_chip = tk.Label(
                self._variante_scroll, text=v.nombre, font=get_font(self.config, "label"),
                fg=self._text, bg=self._CHIP_NORMAL, padx=10, pady=2, cursor="hand2"
            )
            v_chip.pack(side="left", padx=(0, 4))
            v_chip.bind("<Button-1>", lambda e, vid=v.id: self._select_variante(vid))
            self._variante_widgets[v.id] = v_chip
        
        # Si no hay ninguno seleccionado (por el GENERAL), seleccionar el primero
        if variantes and self._selected_variante_id is None and not self._variante_widgets.get(None):
            self._select_variante(variantes[0].id)

    def _select_variante(self, variante_id):
        """Seleccionar una variante específica para configurar su matriz."""
        self._save_tallas_if_dirty()
        self._selected_variante_id = variante_id
        self._selected_color = None
        
        for vid, chip in self._variante_widgets.items():
            chip.configure(bg=self._CHIP_SELECTED if vid == variante_id else self._CHIP_NORMAL)
            
        # Actualizar colores de la variante
        self._colores_asignados = self.service.obtener_colores_tipo_3d(self._selected_id, variante_id)
        
        vn = "GENERAL"
        if variante_id:
            # Buscar nombre de variante (un poco ineficiente pero seguro)
            vars = self.service.obtener_variantes_por_tipo(self._selected_id)
            v_obj = next((v for v in vars if v.id == variante_id), None)
            vn = v_obj.nombre if v_obj else "VARIANTE"
            
        self.lbl_colores_title.configure(text=f"COLORES — {vn}")
        self._rebuild_colores()
        self._clear_tallas()

    def _rebuild_colores(self):
        for child in self._colores_scroll.winfo_children():
            child.destroy()
        self._color_rows = {}
        
        # Si no hay nada seleccionado, salir
        if self._selected_id is None:
            return

        for cid in sorted(self._colores_asignados, key=lambda c: self._all_colores[c].nombre if c in self._all_colores else ""):
            if cid not in self._all_colores: continue
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
            
        # Cargar tallas
        self._tallas_state = self.service.obtener_tallas_tipo_color_3d(self._selected_id, color_id, self._selected_variante_id)
        
        # Cargar stock disponible para esta combinación
        from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
        stock_svc = ProduccionStockBaseService(self.service.db)
        self._stock_actual = stock_svc.obtener_stock_por_tipo_color(self._selected_id, color_id, self._selected_variante_id)
        
        tipo = self.service.obtener_por_id(self._selected_id)
        tn = tipo.nombre if tipo else "TIPO"
        
        vn = ""
        if self._selected_variante_id:
            vars = self.service.obtener_variantes_por_tipo(self._selected_id)
            v_obj = next((v for v in vars if v.id == self._selected_variante_id), None)
            vn = f" / {v_obj.nombre}" if v_obj else ""
        
        gn = f"{tn}{vn}"
            
        self._tallas_dirty = False
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
        self._stock_actual = {}

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
            talla = self._all_tallas[tid]
            stock = self._stock_actual.get(talla.nombre, 0)
            if tid in self._tallas_state:
                chip.configure(text=f"{talla.nombre} [{stock}]", bg=self._CHIP_SELECTED, fg=self._text)
            else:
                chip.configure(text=f"{talla.nombre} [{stock}]", bg=self._CHIP_NO_STOCK, fg=self._CHIP_NO_STOCK_FG)

    def _add_color_dialog(self):
        if not self._selected_id:
            return
        disponibles = [c for cid, c in self._all_colores.items()
                       if cid not in self._colores_asignados]
        if not disponibles:
            return
        win = tk.Toplevel(self.parent.winfo_toplevel())
        win.title("Añadir color al tipo")
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
        if not self._selected_id:
            return
        for cid in self._all_colores:
            if cid not in self._colores_asignados:
                self._colores_asignados.add(cid)
        self._rebuild_colores()

    def _do_add_color(self, color_id, win):
        win.destroy()
        self._colores_asignados.add(color_id)
        self._tallas_dirty = True # Marcar para guardar
        self._rebuild_colores()
        self._select_color(color_id)

    def _remove_color(self, color_id):
        if not self._selected_id:
            return
        
        self._colores_asignados.discard(color_id)
        self._tallas_dirty = True # Marcar para guardar
        
        if self._selected_color == color_id:
            self._selected_color = None
            self._clear_tallas()
        
        # Eliminar físicamente vía servicio si es necesario o esperar al save
        # En este caso, el save_tallas_if_dirty se encargará de sincronizar
        self._rebuild_colores()

    def _save_tallas_if_dirty(self):
        """Guarda los cambios si el estado es 'dirty'."""
        if not self._tallas_dirty or not self._selected_id:
            return

        # Si hay un color seleccionado, guardamos sus tallas
        if self._selected_color:
            self.service.guardar_tallas_tipo_color_3d(
                self._selected_id,
                self._selected_color,
                list(self._tallas_state),
                variante_id=self._selected_variante_id)
            
            # Además, nos aseguramos de que todos los colores en la lista existan en la BD
            # aunque no tengan tallas seleccionadas
            for cid in self._colores_asignados:
                # Obtenemos las tallas actuales para ese color en el estado (si es el seleccionado)
                # o desde la BD si no lo es (para no perder datos)
                if cid == self._selected_color:
                    tallas = list(self._tallas_state)
                else:
                    tallas = list(self.service.obtener_tallas_tipo_color_3d(
                        self._selected_id, cid, self._selected_variante_id))
                
                self.service.guardar_tallas_tipo_color_3d(
                    self._selected_id, cid, tallas, 
                    variante_id=self._selected_variante_id)

        self._tallas_dirty = False

    def _guardar(self):
        self._save_tallas_if_dirty()
        from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
        ToastWidget.show(self.parent.winfo_toplevel(), "Matriz guardada correctamente", tipo="success")

    def refresh_nav(self):
        pass

