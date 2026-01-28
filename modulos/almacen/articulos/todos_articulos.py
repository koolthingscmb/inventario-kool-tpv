import os
import sqlite3
from database import connect
import csv
import time
import subprocess
import customtkinter as ctk
import threading
from tkinter import messagebox
from tkinter import ttk
from .dao_articulos import get_products_page


class TodosArticulos(ctk.CTkFrame):
    def __init__(self, parent, controller, categoria=None):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.controller = controller
        # Use central DB connection; do not construct DB path manually
        self.db_path = None
        self.sort_by = None
        self.sort_desc = False
        # pagination defaults
        self.page = 1
        self.page_size = 100

        # placeholder for columns header; rendered inside render_list so we can update arrows
        self.columns = [("nombre", "Nombre"), ("tipo", "Tipo"), ("proveedor", "Proveedor"), ("categoria", "Categoría")]
        self.cols_frame_parent = ctk.CTkFrame(self)
        self.cols_frame_parent.pack(fill="x", padx=10, pady=(8, 0))
        # ensure grid alignment columns for header buttons (+1 for selection checkbox col)
        for i in range(len(self.columns) + 1):
            try:
                self.cols_frame_parent.grid_columnconfigure(i, weight=1)
            except Exception:
                pass

        # Scrollable area where the list/tree will be placed
        self.scroll = ctk.CTkScrollableFrame(self, height=420)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(4, 0))

        # Bottom controls: search, Export, Volver
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=10, pady=10)
        bottom.grid_columnconfigure(0, weight=1)
        self.search_var = ctk.StringVar()
        self.entry_buscar = ctk.CTkEntry(bottom, textvariable=self.search_var, placeholder_text="Buscar por nombre o sku...")
        self.entry_buscar.grid(row=0, column=0, sticky='ew', padx=(0,8))
        self.entry_buscar.bind('<Return>', lambda e: self.refresh())
        self.btn_buscar = ctk.CTkButton(bottom, text="Buscar", width=120, command=self.refresh)
        self.btn_buscar.grid(row=0, column=1, padx=(0,8))
        self.btn_todos = ctk.CTkButton(bottom, text="Todos", fg_color="#6c6c6c", command=self._clear_filters)
        self.btn_todos.grid(row=0, column=2, padx=(0,8))
        self.btn_export = ctk.CTkButton(bottom, text="Exportar", fg_color="#1f538d", command=self.exportar_csv)
        self.btn_export.grid(row=0, column=3, padx=(0,8))
        self.btn_borrar_sel = ctk.CTkButton(bottom, text="Borrar seleccionados", fg_color="#AA3333", command=self.borrar_seleccionados_confirm)
        self.btn_borrar_sel.grid(row=0, column=4, padx=(0,8))
        self.btn_borrar = ctk.CTkButton(bottom, text="Borrar todos", fg_color="#AA3333", command=self.borrar_todos_confirm)
        self.btn_borrar.grid(row=0, column=5, padx=(0,8))
        self.btn_volver = ctk.CTkButton(bottom, text="Volver", fg_color="gray", command=self._volver_restaurar)
        self.btn_volver.grid(row=0, column=6)
        # selected ids
        self._selected_ids = set()
        # mapping item_id -> IntVar for checkboxes
        self._row_vars = {}
        # mapping item_id -> row frame for visual updates
        self._row_frames = {}
        # last clicked index for shift-selection
        self._last_clicked_index = None
        # pending single-click after id (to distinguish double-click)
        self._pending_click_after = None
        # select-all variable
        self._select_all_var = ctk.IntVar(value=0)
        # last rendered item ids (for select-all toggle)
        self._last_rendered_item_ids = []

        # detect tipo-like column name for later use
        prod_cols = self._table_columns('productos')
        self.tipo_col_name = None
        for tc in ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']:
            if tc in prod_cols:
                self.tipo_col_name = tc
                break
        # filter state variables (used when header selectors set them)
        self.filter_proveedor = ctk.StringVar(value='')
        self.filter_tipo = ctk.StringVar(value='')
        self.filter_categoria = ctk.StringVar(value='')

        # Load and show (restore state if exists)
        try:
            state = getattr(self.controller, 'todos_articulos_state', None)
            if state:
                self.page = state.get('page', 1)
                self.page_size = state.get('page_size', 100)
                self.sort_by = state.get('sort_by', None)
                self.sort_desc = state.get('sort_desc', False)
                self.search_var.set(state.get('search', ''))
                # restore filters if present
                try:
                    fc = state.get('filter_categoria')
                    if fc is not None:
                        self.filter_categoria.set(fc)
                except Exception:
                    pass
                try:
                    fp = state.get('filter_proveedor')
                    if fp is not None:
                        self.filter_proveedor.set(fp)
                except Exception:
                    pass
                try:
                    ft = state.get('filter_tipo')
                    if ft is not None:
                        self.filter_tipo.set(ft)
                except Exception:
                    pass
        except Exception:
            pass
        # If a category was passed into the constructor (e.g. from another view), apply it
        try:
            if categoria:
                try:
                    # always apply explicit category argument so external callers (buttons/views)
                    # can open the list filtered by that category immediately
                    self.filter_categoria.set(categoria)
                except Exception:
                    pass
        except Exception:
            pass
        self.refresh()

    # Small helpers
    def _connect(self):
        # Prefer default DB_PATH from database.connect()
        return connect()

    def _table_columns(self, table):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            rows = cur.fetchall()
            return [r[1] for r in rows]
        except Exception:
            return []
        finally:
            try:
                con.close()
            except Exception:
                pass

    def _distinct_values_from_product(self, col):
        if not col:
            return []
        con = self._connect()
        try:
            cur = con.cursor()
            cur.execute(f"SELECT DISTINCT {col} FROM productos WHERE {col} IS NOT NULL AND {col} != '' ORDER BY {col} COLLATE NOCASE")
            rows = [r[0] for r in cur.fetchall() if r and r[0] is not None]
            return rows
        except Exception:
            return []
        finally:
            try:
                con.close()
            except Exception:
                pass

    def _on_header_combo_change(self, col_key, value):
        # map display '[Todos]' to empty string
        try:
            # remove debug prints
            pass
        except Exception:
            pass
        if value == '[Todos]':
            val = ''
        else:
            val = value
        if col_key == 'proveedor':
            self.filter_proveedor.set(val)
        elif col_key == 'categoria':
            self.filter_categoria.set(val)
        elif col_key == 'tipo':
            self.filter_tipo.set(val)
        self.refresh()

    def _update_row_visual(self, item_id):
        try:
            widgets = self._row_frames.get(item_id)
            var = self._row_vars.get(item_id)
            if widgets is None or var is None:
                return
            # apply highlight color to each widget in the row when selected
            if var.get():
                for w in widgets:
                    try:
                        w.configure(fg_color="#2b2b2b")
                    except Exception:
                        try:
                            w.configure(bg="#2b2b2b")
                        except Exception:
                            pass
            else:
                for w in widgets:
                    try:
                        w.configure(fg_color=None)
                    except Exception:
                        try:
                            w.configure(bg=self.scroll.cget('fg_color'))
                        except Exception:
                            pass
        except Exception:
            pass

    def _on_row_double_click(self, event, item_id):
        # legacy handler kept for compatibility; forward to tree handler if applicable
        try:
            if getattr(self, 'tree', None):
                # ignore: tree double-click will handle via _on_tree_double_click
                return
        except Exception:
            pass
        try:
            self.controller.mostrar_crear_producto(item_id)
        except Exception:
            pass

    def _on_row_click(self, event, item_id):
        # legacy click handler; when using treeview we rely on its selection model
        try:
            if getattr(self, 'tree', None):
                return
        except Exception:
            pass
        try:
            # schedule single-click action shortly to allow double-click to cancel it
            if getattr(self, '_pending_click_after', None):
                try:
                    self.after_cancel(self._pending_click_after)
                except Exception:
                    pass
                self._pending_click_after = None
            self._pending_click_after = self.after(180, lambda: self._handle_row_single_click(event, item_id))
        except Exception:
            pass

    def _handle_row_single_click(self, event, item_id):
        try:
            self._pending_click_after = None
            # modifier detection: Shift and Control
            state = getattr(event, 'state', 0)
            is_shift = bool(state & 0x1)
            is_ctrl = bool(state & 0x4)

            # get current index in rendered list
            try:
                idx = self._last_rendered_item_ids.index(item_id)
            except Exception:
                idx = None

            if is_shift and idx is not None and self._last_clicked_index is not None:
                # select range between last_clicked_index and idx
                try:
                    a = min(self._last_clicked_index, idx)
                    b = max(self._last_clicked_index, idx)
                    for i in range(a, b+1):
                        iid = self._last_rendered_item_ids[i]
                        self._selected_ids.add(iid)
                        if iid in self._row_vars:
                            try:
                                self._row_vars[iid].set(1)
                            except Exception:
                                pass
                except Exception:
                    pass
            else:
                # toggle single item selection (ctrl behaves same as plain click for toggle)
                if item_id in self._selected_ids:
                    try:
                        self._selected_ids.remove(item_id)
                    except Exception:
                        pass
                    if item_id in self._row_vars:
                        try:
                            self._row_vars[item_id].set(0)
                        except Exception:
                            pass
                else:
                    try:
                        self._selected_ids.add(item_id)
                    except Exception:
                        pass
                    if item_id in self._row_vars:
                        try:
                            self._row_vars[item_id].set(1)
                        except Exception:
                            pass

            # update visuals for affected rows
            try:
                if idx is not None:
                    # update all in current rendered list for simplicity
                    for iid in self._last_rendered_item_ids:
                        self._update_row_visual(iid)
                else:
                    self._update_row_visual(item_id)
            except Exception:
                pass

            # remember last clicked index for shift selections
            try:
                if idx is not None:
                    self._last_clicked_index = idx
            except Exception:
                pass
        except Exception:
            pass

    def _on_tree_double_click(self, event):
        try:
            rowid = self.tree.identify_row(event.y)
            if not rowid:
                return
            try:
                # save current view/selection so we can restore when returning
                try:
                    top_frac = 0.0
                    try:
                        v = self.tree.yview()
                        if v and isinstance(v, tuple):
                            top_frac = float(v[0])
                    except Exception:
                        top_frac = 0.0
                    # save current filters + view so we can restore the exact filtered list later
                    try:
                        saved = {
                            'page': getattr(self, 'page', 1),
                            'page_size': getattr(self, 'page_size', 100),
                            'sort_by': getattr(self, 'sort_by', None),
                            'sort_desc': getattr(self, 'sort_desc', False),
                            'search': self.search_var.get() if hasattr(self, 'search_var') else '',
                            'selected_id': int(rowid),
                            'yview': top_frac,
                            'filter_categoria': self.filter_categoria.get() if getattr(self, 'filter_categoria', None) is not None else '',
                            'filter_proveedor': self.filter_proveedor.get() if getattr(self, 'filter_proveedor', None) is not None else '',
                            'filter_tipo': self.filter_tipo.get() if getattr(self, 'filter_tipo', None) is not None else ''
                        }
                        self.controller.todos_articulos_state = saved
                    except Exception:
                        # fallback to minimal state if anything goes wrong
                        self.controller.todos_articulos_state = {
                            'page': getattr(self, 'page', 1),
                            'page_size': getattr(self, 'page_size', 100),
                            'sort_by': getattr(self, 'sort_by', None),
                            'sort_desc': getattr(self, 'sort_desc', False),
                            'search': self.search_var.get() if hasattr(self, 'search_var') else '',
                            'selected_id': int(rowid),
                            'yview': top_frac
                        }
                except Exception:
                    pass
                self.controller.mostrar_crear_producto(int(rowid))
            except Exception:
                pass
        except Exception:
            pass

    def _clear_filters(self):
        try:
            self.filter_proveedor.set('')
            self.filter_categoria.set('')
            self.filter_tipo.set('')
            self.search_var.set('')
        except Exception:
            pass
        self.refresh()

    # -------------------------
    # Data load & render
    # -------------------------
    def load_items(self, page_size_override=None):
        # normalize incoming filter vars (comboboxes may hold '[Todos]')
        try:
            q = self.search_var.get().strip()
        except Exception:
            q = ''
        try:
            prov_val = getattr(self, 'filter_proveedor').get().strip()
        except Exception:
            prov_val = ''
        try:
            cat_val = getattr(self, 'filter_categoria').get().strip()
        except Exception:
            cat_val = ''
        try:
            tipo_val = getattr(self, 'filter_tipo').get().strip()
        except Exception:
            tipo_val = ''
        if prov_val == '[Todos]':
            prov_val = ''
        if cat_val == '[Todos]':
            cat_val = ''
        if tipo_val == '[Todos]':
            tipo_val = ''
        
        # Delegate DB access to DAO (keeps UI code simple and testable)
        try:
            ps = page_size_override if page_size_override is not None else getattr(self, 'page_size', 100)
            items = get_products_page(self.db_path,
                                      page=getattr(self, 'page', 1),
                                      page_size=ps,
                                      search=q,
                                      proveedor=prov_val,
                                      categoria=cat_val,
                                      tipo=tipo_val,
                                      sort_by=getattr(self, 'sort_by', None),
                                      sort_desc=getattr(self, 'sort_desc', False))
            return items
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Error leyendo productos: {e}")
            except Exception:
                pass
            return []

        

    def clear_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

    def render_list(self):
        # start background load to avoid blocking the UI
        try:
            # show quick loading label
            try:
                if getattr(self, '_loading_label', None):
                    self._loading_label.pack(fill='both', expand=True)
                else:
                    self._loading_label = ctk.CTkLabel(self.scroll, text='Cargando...', anchor='center')
                    self._loading_label.pack(fill='both', expand=True)
            except Exception:
                pass
            t = threading.Thread(target=self._bg_load_and_render, daemon=True)
            t.start()
        except Exception:
            # fallback to synchronous render
            items = self.load_items()
            try:
                self._render_list_with_items(items)
            except Exception:
                pass

    def _bg_load_and_render(self):
        # request one extra row to detect whether there is a next page
        try:
            items = self.load_items(page_size_override=(getattr(self, 'page_size', 100) + 1))
        except Exception:
            items = []
        try:
            if items and len(items) > getattr(self, 'page_size', 100):
                self._has_next = True
                items = items[:getattr(self, 'page_size', 100)]
            else:
                self._has_next = False
        except Exception:
            self._has_next = False
        try:
            self.after(0, lambda: self._render_list_with_items(items))
        except Exception:
            pass

    def _render_list_with_items(self, items):
        # remove loading label if present
        try:
            if getattr(self, '_loading_label', None):
                try:
                    self._loading_label.destroy()
                except Exception:
                    pass
                self._loading_label = None
        except Exception:
            pass
        self.clear_list()
        # header-like row for spreadsheet feel (recreate header each render so arrow updates)
        try:
            for w in self.cols_frame_parent.winfo_children():
                w.destroy()
        except Exception:
            pass
        header_ctrl = self.cols_frame_parent
        # ensure two rows: 0 -> small title, 1 -> control (combo/button)
        try:
            header_ctrl.grid_rowconfigure(0, weight=0)
            header_ctrl.grid_rowconfigure(1, weight=0)
        except Exception:
            pass
        # selection column UI removed (select-all hidden)
        for i, (col_key, col_label) in enumerate(self.columns):
            arrow = ''
            if self.sort_by == col_key:
                arrow = ' ▲' if not self.sort_desc else ' ▼'
            # For certain columns show a dropdown selector
            if col_key in ('proveedor', 'categoria', 'tipo'):
                if col_key == 'proveedor':
                    vals = ['[Todos]'] + self._distinct_values_from_product('proveedor')
                    var = self.filter_proveedor
                elif col_key == 'categoria':
                    vals = ['[Todos]'] + self._distinct_values_from_product('categoria')
                    var = self.filter_categoria
                else:
                    vals = ['[Todos]'] + (self._distinct_values_from_product(self.tipo_col_name) if self.tipo_col_name else [])
                    var = self.filter_tipo
                # ensure variable shows [Todos] when empty
                try:
                    display_value = var.get() if var.get() else '[Todos]'
                except Exception:
                    display_value = '[Todos]'
                # place a small title label above the combo
                try:
                    lbl = ctk.CTkLabel(header_ctrl, text=col_label, font=(None, 9))
                    lbl.grid(row=0, column=i+1, sticky='s', padx=2, pady=(2,0))
                except Exception:
                    pass
                try:
                    combo = ctk.CTkComboBox(header_ctrl, values=vals, variable=var, command=lambda v, k=col_key: self._on_header_combo_change(k, v))
                    combo.set(display_value)
                    combo.grid(row=1, column=i+1, sticky='nsew', padx=4, pady=6)
                except Exception:
                    # fallback to button if combobox not available
                    b = ctk.CTkButton(header_ctrl, text=col_label + arrow, fg_color="#1f538d", text_color="white", corner_radius=8, command=lambda k=col_key: self.toggle_sort(k))
                    b.grid(row=1, column=i+1, sticky='nsew', padx=4, pady=6)
            else:
                # non-filter columns: put a title label blank and the button below
                try:
                    lbl = ctk.CTkLabel(header_ctrl, text="", font=(None, 9))
                    lbl.grid(row=0, column=i+1, sticky='s', padx=2, pady=(2,0))
                except Exception:
                    pass
                # For the main 'Nombre' column we keep a neutral label instead of a blue button
                try:
                    # remove visible 'Nombre' text per request (leave area blank)
                    if col_key == 'nombre':
                        lbl2 = ctk.CTkLabel(header_ctrl, text="", font=("Arial", 11, "bold"))
                        lbl2.grid(row=1, column=i+1, sticky='nsew', padx=4, pady=6)
                    else:
                        b = ctk.CTkButton(header_ctrl, text=col_label + arrow, fg_color="#1f538d", text_color="white", corner_radius=8, command=lambda k=col_key: self.toggle_sort(k))
                        b.grid(row=1, column=i+1, sticky='nsew', padx=4, pady=6)
                except Exception:
                    pass

        # rows (render into a Treeview for stable columns)
        # record last rendered ids for select-all
        try:
            self._last_rendered_item_ids = [it['id'] for it in items]
        except Exception:
            self._last_rendered_item_ids = []
        # clear previous row mappings
        try:
            self._row_vars.clear()
        except Exception:
            self._row_vars = {}
        try:
            self._row_frames.clear()
        except Exception:
            self._row_frames = {}

        # Use a Treeview for rows to ensure columns align with header and resize consistently
        try:
            for w in self.scroll.winfo_children():
                w.destroy()
            tree_frame = ctk.CTkFrame(self.scroll)
            tree_frame.pack(fill='both', expand=True)
            cols = [c[0] for c in self.columns]
            self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='extended')
            # make headings bold for better readability
            try:
                style = ttk.Style()
                style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
            except Exception:
                pass
            # configure headings
            for col_key, col_label in self.columns:
                try:
                    # left-justify heading text and column content
                    self.tree.heading(col_key, text=col_label, anchor='w')
                    self.tree.column(col_key, anchor='w', stretch=True)
                except Exception:
                    pass
            # vertical scrollbar
            vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
            self.tree.configure(yscrollcommand=vsb.set)
            self.tree.pack(side='left', fill='both', expand=True)
            vsb.pack(side='right', fill='y')

            # populate rows
            for it in items:
                try:
                    vals = (it.get('nombre',''), it.get('tipo',''), it.get('proveedor',''), it.get('categoria',''))
                    self.tree.insert('', 'end', iid=str(it['id']), values=vals)
                except Exception:
                    pass

            # if there's saved state from before (selection + yview), restore it
            try:
                state = getattr(self.controller, 'todos_articulos_state', None)
                if state:
                    sel = state.get('selected_id')
                    yv = state.get('yview')
                    if isinstance(yv, (int, float)):
                        try:
                            self.tree.yview_moveto(float(yv))
                        except Exception:
                            pass
                    if sel is not None:
                        try:
                            sid = str(int(sel))
                            if sid in self.tree.get_children():
                                self.tree.selection_set(sid)
                                self.tree.see(sid)
                        except Exception:
                            pass
                    # clear saved selection so subsequent navigations don't stale
                    try:
                        delattr(self.controller, 'todos_articulos_state')
                    except Exception:
                        try:
                            self.controller.todos_articulos_state = None
                        except Exception:
                            pass
            except Exception:
                pass

            # bind double-click to edit
            try:
                self.tree.bind('<Double-1>', self._on_tree_double_click)
            except Exception:
                pass
        except Exception:
            pass

        # helper to refresh visuals based on selection
        try:
            for _id in list(self._row_frames.keys()):
                self._update_row_visual(_id)
        except Exception:
            pass
        # Pagination controls
        try:
            if getattr(self, '_pagination_frame', None):
                self._pagination_frame.destroy()
        except Exception:
            pass
        self._pagination_frame = ctk.CTkFrame(self)
        self._pagination_frame.pack(fill='x', padx=10, pady=(0,10))
        # create prev/label/next with references so we can enable/disable
        self._btn_prev = ctk.CTkButton(self._pagination_frame, text='◀ Anterior', command=self.prev_page)
        self._btn_prev.pack(side='left', padx=6)
        self._lbl_page = ctk.CTkLabel(self._pagination_frame, text=f'Página {self.page}')
        self._lbl_page.pack(side='left', padx=6)
        self._btn_next = ctk.CTkButton(self._pagination_frame, text='Siguiente ▶', command=self.next_page)
        self._btn_next.pack(side='left', padx=6)
        # configure state
        try:
            if getattr(self, 'page', 1) <= 1:
                self._btn_prev.configure(state='disabled')
            else:
                self._btn_prev.configure(state='normal')
        except Exception:
            pass
        try:
            if getattr(self, '_has_next', False):
                self._btn_next.configure(state='normal')
            else:
                self._btn_next.configure(state='disabled')
        except Exception:
            pass

    # -------------------------
    # Sorting & actions
    # -------------------------
    def toggle_sort(self, key):
        if self.sort_by == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_by = key
            self.sort_desc = False
        self.page = 1
        self.refresh()

    def refresh(self):
        self.render_list()

    def exportar_csv(self):
        # Determine which IDs to export: prefer Treeview selection, then internal selected set, otherwise current page
        try:
            ids = []
            if getattr(self, 'tree', None):
                sel = self.tree.selection()
                if sel:
                    ids = [int(s) for s in sel]
            if not ids and self._selected_ids:
                ids = list(self._selected_ids)
            # fallback to current loaded items
            if not ids:
                items = self.load_items()
                ids = [it['id'] for it in items]
        except Exception:
            items = self.load_items()
            ids = [it['id'] for it in items]

        if not ids:
            messagebox.showinfo("Exportar", "No hay artículos a exportar.")
            return

        try:
            from tkinter import filedialog
            default_name = f"tpv_export_articulos_{int(time.time())}.csv"
            path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile=default_name)
            if not path:
                return

            # Build columns from productos table (deduped) and add pvp/coste
            prod_cols = self._table_columns('productos')
            cols = []
            for c in (['id'] + prod_cols):
                if c not in cols:
                    cols.append(c)
            # ensure pvp and coste are present at the end
            if 'pvp' not in cols:
                cols.append('pvp')
            if 'coste' not in cols:
                cols.append('coste')

            # Remove redundant derived columns if present
            for redundant in ('categoria_nombre', 'proveedor_nombre', 'tipo_nombre', 'tipo_shop'):
                if redundant in cols:
                    cols.remove(redundant)

            con = self._connect()
            cur = con.cursor()

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()

                # fetch product rows for ids
                placeholders = ','.join(['?'] * len(ids))
                try:
                    cur.execute(f'SELECT * FROM productos WHERE id IN ({placeholders})', ids)
                    prods = cur.fetchall()
                except Exception:
                    prods = []

                # map pragma order
                pcols = self._table_columns('productos')
                prod_map = {}
                for prod in prods:
                    try:
                        pid = prod[0]
                        row = {c: '' for c in cols}
                        for i, pc in enumerate(pcols):
                            if pc in cols and i < len(prod):
                                row[pc] = prod[i]
                        prod_map[pid] = row
                    except Exception:
                        pass

                # For ids without fetched prod (shouldn't happen), try single fetch
                for _id in ids:
                    row = prod_map.get(_id)
                    if row is None:
                        row = {c: '' for c in cols}
                        try:
                            cur.execute('SELECT * FROM productos WHERE id=?', (_id,))
                            prod = cur.fetchone()
                            if prod:
                                for i, pc in enumerate(pcols):
                                    if pc in cols and i < len(prod):
                                        row[pc] = prod[i]
                        except Exception:
                            pass

                    # get active price (pvp/coste)
                    try:
                        cur.execute('SELECT pvp, coste FROM precios WHERE producto_id=? AND activo=1 LIMIT 1', (_id,))
                        pr = cur.fetchone()
                        if pr:
                            row['pvp'] = pr[0]
                            row['coste'] = pr[1]
                        else:
                            row['pvp'] = ''
                            row['coste'] = ''
                    except Exception:
                        row['pvp'] = ''
                        row['coste'] = ''

                    # ventas_totales is a column in productos - ensure it's present
                    if 'ventas_totales' in pcols and 'ventas_totales' in cols:
                        try:
                            # already populated from producto row
                            pass
                        except Exception:
                            pass

                    # If proveedor is numeric id, resolve to provider name
                    try:
                        prov_val = row.get('proveedor')
                        if prov_val is not None and prov_val != '':
                            try:
                                prov_id = int(prov_val)
                                cur.execute('SELECT nombre FROM proveedores WHERE id=? LIMIT 1', (prov_id,))
                                r = cur.fetchone()
                                if r and r[0]:
                                    row['proveedor'] = r[0]
                            except Exception:
                                # leave as-is if not numeric or lookup fails
                                pass
                    except Exception:
                        pass

                    # Reorder columns to place 'tipo' next to 'categoria' if both exist
                    try:
                        if 'categoria' in cols and 'tipo' in cols:
                            # build preferred order
                            ordered = []
                            for key in ('id', 'nombre', 'sku', 'categoria', 'tipo', 'proveedor'):
                                if key in cols and key not in ordered:
                                    ordered.append(key)
                            for key in cols:
                                if key not in ordered:
                                    ordered.append(key)
                            out_row = {k: row.get(k, '') for k in ordered}
                            writer.writerow(out_row)
                            continue
                    except Exception:
                        pass

                    writer.writerow(row)

                try:
                    con.close()
                except Exception:
                    pass

            messagebox.showinfo("Exportar", f"Exportado {len(ids)} artículos a:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar CSV: {e}")

    def borrar_todos_confirm(self):
        if not messagebox.askyesno("Confirmar borrado", "¿Borrar TODOS los artículos y datos relacionados? Esta acción no se puede deshacer."):
            return
        self.borrar_todos()

    def borrar_todos(self):
        try:
            con = self._connect()
            cur = con.cursor()
            # borrar datos relacionados (si existen)
            related_tables = [
                'precios',
                'codigos_barras',
                'product_images',
                'product_history'
            ]
            for t in related_tables:
                try:
                    cur.execute(f"DELETE FROM {t}")
                except Exception:
                    pass
            # borrar productos
            try:
                cur.execute('DELETE FROM productos')
            except Exception:
                pass
            con.commit()
            try:
                con.close()
            except Exception:
                pass
            messagebox.showinfo('Borrar', 'Se han borrado todos los artículos.')
            self._clear_filters()
            self.refresh()
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo borrar: {e}')

    def borrar_seleccionados_confirm(self):
        if not self._selected_ids:
            messagebox.showinfo('Borrar seleccionados', 'No hay artículos seleccionados.')
            return
        if not messagebox.askyesno('Confirmar borrado', f'¿Borrar {len(self._selected_ids)} artículos seleccionados? Esta acción no se puede deshacer.'):
            return
        self.borrar_seleccionados()

    def borrar_seleccionados(self):
        # determine selected ids from treeview if present, otherwise fallback to _selected_ids
        ids = []
        try:
            if getattr(self, 'tree', None):
                sel = self.tree.selection()
                ids = [int(s) for s in sel]
        except Exception:
            ids = []
        if not ids:
            ids = list(self._selected_ids)
        if not ids:
            return
        try:
            con = self._connect()
            cur = con.cursor()
            placeholders = ','.join(['?'] * len(ids))
            # delete from related tables by producto_id if column exists
            related_by_prod = ['precios', 'codigos_barras', 'product_images', 'product_history']
            for t in related_by_prod:
                try:
                    cur.execute(f"DELETE FROM {t} WHERE producto_id IN ({placeholders})", ids)
                except Exception:
                    try:
                        # try alternative column name
                        cur.execute(f"DELETE FROM {t} WHERE product_id IN ({placeholders})", ids)
                    except Exception:
                        pass
            # delete products
            try:
                cur.execute(f"DELETE FROM productos WHERE id IN ({placeholders})", ids)
            except Exception:
                pass
            con.commit()
            try:
                con.close()
            except Exception:
                pass
            self._selected_ids.clear()
            messagebox.showinfo('Borrar', f'Se han borrado {len(ids)} artículos seleccionados.')
            self._clear_filters()
            self.refresh()
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo borrar seleccionados: {e}')

    def _on_select_toggle(self, _id, var):
        try:
            if var.get():
                self._selected_ids.add(_id)
            else:
                self._selected_ids.discard(_id)
        except Exception:
            pass

    def _toggle_select_all(self):
        try:
            val = self._select_all_var.get()
        except Exception:
            val = 0
        try:
            if getattr(self, 'tree', None):
                if val:
                    self.tree.selection_set(self.tree.get_children())
                else:
                    self.tree.selection_remove(self.tree.get_children())
                return
        except Exception:
            pass
        if val:
            # select all currently rendered
            try:
                for _id in self._last_rendered_item_ids:
                    self._selected_ids.add(_id)
            except Exception:
                pass
        else:
            # deselect all currently rendered
            try:
                for _id in self._last_rendered_item_ids:
                    self._selected_ids.discard(_id)
            except Exception:
                pass
        # re-render to update checkboxes/highlight
        self.refresh()

    def _volver_restaurar(self):
        # save state and go back to submenu
        try:
            self.controller.todos_articulos_state = {
                'page': getattr(self, 'page', 1),
                'page_size': getattr(self, 'page_size', 100),
                'sort_by': getattr(self, 'sort_by', None),
                'sort_desc': getattr(self, 'sort_desc', False),
                'search': self.search_var.get() if hasattr(self, 'search_var') else ''
            }
        except Exception:
            pass
        try:
            self.controller.mostrar_submenu_almacen()
        except Exception:
            try:
                self.controller.mostrar_inicio()
            except Exception:
                pass

    def next_page(self):
        try:
            if not getattr(self, '_has_next', False):
                return
            self.page = getattr(self, 'page', 1) + 1
            self.refresh()
        except Exception:
            try:
                self.page = getattr(self, 'page', 1)
            except Exception:
                pass

    def prev_page(self):
        if getattr(self, 'page', 1) > 1:
            self.page -= 1
        self.refresh()

