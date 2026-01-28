import os
import time
import logging
import tkinter as tk
from tkinter import filedialog
from modulos.exportar_importar.exportar_service import ExportarService
import customtkinter as ctk
import threading
from tkinter import messagebox
from tkinter import ttk
from modulos.almacen.producto_service import ProductoService


class DialogExportarArticulos(ctk.CTkToplevel):
    def __init__(self, parent, columnas, on_export_csv, on_export_pdf, preselected=None):
        super().__init__(parent)
        self.title('Exportar Artículos')
        self.geometry('420x420')
        self.columnas = columnas
        self.on_export_csv = on_export_csv
        self.on_export_pdf = on_export_pdf
        self.check_vars = []
        self.preselected = set(preselected or [])

        ctk.CTkLabel(self, text='Elige el formato de exportación y selecciona columnas', anchor='center').pack(pady=10)

        self.frame_cols = ctk.CTkFrame(self)
        self.frame_cols.pack(fill='both', expand=True, padx=8, pady=6)

        # create checkbuttons but do not pack/grid yet; we'll layout dynamically
        self.checkbox_widgets = []
        for col in columnas:
            var = tk.IntVar(value=1 if col in self.preselected else 0)
            cb = tk.Checkbutton(self.frame_cols, text=col, variable=var, anchor='w')
            self.checkbox_widgets.append((col, var, cb))

        # bind resize to relayout the checkboxes in a grid
        try:
            self.bind('<Configure>', lambda e: self._layout_checkboxes())
        except Exception:
            pass
        # initial layout
        self.after(50, self._layout_checkboxes)

        frame_btns = ctk.CTkFrame(self)
        frame_btns.pack(pady=10, fill='x')
        ctk.CTkButton(frame_btns, text='Exportar a CSV', command=self.export_csv).pack(side='left', padx=6)
        ctk.CTkButton(frame_btns, text='Exportar a PDF', command=self.export_pdf).pack(side='left', padx=6)
        ctk.CTkButton(frame_btns, text='Cancelar', command=self.destroy).pack(side='left', padx=6)

    def export_csv(self):
        sel = [col for col, var in zip(self.columnas, self.check_vars) if var.get()]
        if not sel:
            tk.messagebox.showinfo('Exportar', 'Seleccione al menos una columna para exportar.')
            return
        try:
            self.on_export_csv(sel)
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    def export_pdf(self):
        sel = [col for col, var in zip(self.columnas, self.check_vars) if var.get()]
        if not sel:
            tk.messagebox.showinfo('Exportar', 'Seleccione al menos una columna para exportar.')
            return
        try:
            self.on_export_pdf(sel)
        finally:
            try:
                self.destroy()
            except Exception:
                pass

    def _layout_checkboxes(self):
        try:
            # prefer frame width, fallback to toplevel width
            w = self.frame_cols.winfo_width() or self.winfo_width() or 420
            # target approximate width per column
            target_w = 180
            cols_per_row = max(1, int(max(1, w) // target_w))
        except Exception:
            cols_per_row = 4

        # clear grid
        for _, _, widget in self.checkbox_widgets:
            try:
                widget.grid_forget()
            except Exception:
                pass

        for i, (col, var, widget) in enumerate(self.checkbox_widgets):
            col_pos = i % cols_per_row
            row_pos = i // cols_per_row
            try:
                widget.grid(row=row_pos, column=col_pos, sticky='w', padx=6, pady=4)
            except Exception:
                try:
                    widget.pack(anchor='w', padx=6, pady=4)
                except Exception:
                    pass

        # configure equal weight columns
        try:
            for c in range(cols_per_row):
                try:
                    self.frame_cols.grid_columnconfigure(c, weight=1)
                except Exception:
                    pass
        except Exception:
            pass


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
        # Service layer
        self.service = ProductoService()

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
        # Exportación centralizada en `ExportarService`.
        self.btn_export = ctk.CTkButton(bottom, text="Exportar", fg_color="#1f538d", command=self._open_export_dialog)
        self.btn_export.grid(row=0, column=3, padx=(0,8))
        self.btn_borrar_sel = ctk.CTkButton(bottom, text="Borrar seleccionados", fg_color="#AA3333", command=self.borrar_seleccionados_confirm)
        self.btn_borrar_sel.grid(row=0, column=4, padx=(0,8))
        self.btn_volver = ctk.CTkButton(bottom, text="Volver", fg_color="gray", command=self._volver_restaurar)
        self.btn_volver.grid(row=0, column=6)
        # Treeview selection will be used; no manual selection state maintained

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
        # legacy compatibility kept; services use central DB
        from database import connect
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
        """Usa el servicio para obtener valores únicos para filtros."""
        try:
            if not col:
                return []
            return self.service.obtener_valores_unicos(col)
        except Exception:
            return []

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
        
        try:
            ps = page_size_override if page_size_override is not None else getattr(self, 'page_size', 100)
            filtros = {
                'page': getattr(self, 'page', 1),
                'page_size': ps,
                'search': q,
                'proveedor': prov_val,
                'categoria': cat_val,
                'tipo': tipo_val,
                'sort_by': getattr(self, 'sort_by', None),
                'sort_desc': getattr(self, 'sort_desc', False)
            }
            items = self.service.obtener_productos_paginados(filtros)
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
        # record last rendered ids for potential fallback uses
        try:
            self._last_rendered_item_ids = [it['id'] for it in items]
        except Exception:
            self._last_rendered_item_ids = []

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

            # no manual visual update required; Treeview handles selection visuals
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

    # Export logic removed: centralized in `ExportarService`.
    # TODO: Integrar con `modulos.exportar_importar.exportar_service.ExportarService.exportar_a_csv`.

    # Eliminar funcionalidad de 'Borrar todos' de esta pantalla (operación sensible)

    def borrar_seleccionados_confirm(self):
        # rely on Treeview selection
        try:
            sel = []
            if getattr(self, 'tree', None):
                sel = self.tree.selection()
            if not sel:
                messagebox.showinfo('Borrar seleccionados', 'No hay artículos seleccionados.')
                return
            if not messagebox.askyesno('Confirmar borrado', f'¿Borrar {len(sel)} artículos seleccionados? Esta acción no se puede deshacer.'):
                return
            self.borrar_seleccionados()
        except Exception:
            messagebox.showinfo('Borrar seleccionados', 'No hay artículos seleccionados.')

    def borrar_seleccionados(self):
        try:
            if not getattr(self, 'tree', None):
                messagebox.showinfo('Borrar seleccionados', 'No hay artículos seleccionados.')
                return
            sel = self.tree.selection()
            ids = [int(x) for x in sel] if sel else []
            if not ids:
                messagebox.showinfo('Borrar seleccionados', 'No hay artículos seleccionados.')
                return
            ok = self.service.eliminar_productos_por_id(ids)
            if ok:
                try:
                    # clear selection
                    self.tree.selection_remove(self.tree.selection())
                except Exception:
                    pass
                messagebox.showinfo('Borrar', f'Se han borrado {len(ids)} artículos seleccionados.')
                self._clear_filters()
                self.refresh()
            else:
                messagebox.showerror('Error', 'No se pudieron borrar los artículos seleccionados.')
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo borrar seleccionados: {e}')
    

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

    def exportar_csv(self):
        # Deprecated: use dialog-based export. Kept for API compatibility.
        try:
            self._open_export_dialog()
        except Exception:
            try:
                messagebox.showerror('Exportar', 'No se pudo abrir el diálogo de exportación')
            except Exception:
                pass

    def _open_export_dialog(self):
        # Obtener todas las columnas de la tabla productos desde el servicio
        try:
            cols = ProductoService().obtener_columnas_productos() or []
        except Exception:
            cols = []

        # Visible por defecto (posibles nombres de columnas visibles en UI):
        visible = ['ID', 'Nombre', 'Tipo', 'Proveedor', 'Categoría']

        # Normalizar nombres para emparejar visibilidad con nombres reales de BD
        def _normalize(s: str) -> str:
            if not s:
                return ''
            s = s.lower()
            for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
                s = s.replace(a,b)
            s = s.replace(' ', '')
            return s

        vis_norm = set(_normalize(v) for v in visible)
        preselected = [c for c in cols if _normalize(c) in vis_norm]

        dlg = DialogExportarArticulos(self, cols, on_export_csv=self._on_export_csv_selected, on_export_pdf=self._on_export_pdf_selected, preselected=preselected)
        try:
            dlg.grab_set()
        except Exception:
            pass

    def _collect_rows_for_export(self, selected_columns):
        # Delegate data retrieval to ProductoService which handles joins
        # (e.g. codigo_barras) and column validation.
        try:
            # determine ids to export: selection preferred, otherwise visible items
            ids = []
            try:
                if getattr(self, 'tree', None):
                    sel = self.tree.selection()
                    if sel:
                        ids = [int(x) for x in sel]
                    else:
                        ids = getattr(self, '_last_rendered_item_ids', [])
            except Exception:
                ids = getattr(self, '_last_rendered_item_ids', []) or []

            if not ids:
                items = self.load_items()
                ids = [it.get('id') for it in items]

            if not ids:
                return []

            svc = ProductoService()
            rows = svc.obtener_productos_por_ids_columnas(ids, selected_columns)
            return rows or []
        except Exception:
            return []

    def _on_export_csv_selected(self, selected_columns):
        logger = logging.getLogger(__name__)
        rows = self._collect_rows_for_export(selected_columns)
        if not rows:
            try:
                messagebox.showinfo('Exportar', 'No hay artículos a exportar.')
            except Exception:
                pass
            return
        default_name = f"articulos_export_{int(time.time())}.csv"
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile=default_name)
        if not path:
            return
        try:
            ok = ExportarService().exportar_a_csv(path, selected_columns, rows)
            if ok:
                messagebox.showinfo('Exportar', f'Exportado correctamente a:\n{path}')
            else:
                messagebox.showerror('Exportar', 'Error exportando archivo. Revisa logs para más detalles.')
        except Exception as e:
            logger.exception('Error exportando CSV: %s', e)
            try:
                messagebox.showerror('Exportar', f'Error exportando CSV: {e}')
            except Exception:
                pass

    def _on_export_pdf_selected(self, selected_columns):
        logger = logging.getLogger(__name__)
        rows = self._collect_rows_for_export(selected_columns)
        if not rows:
            try:
                messagebox.showinfo('Exportar', 'No hay artículos a exportar.')
            except Exception:
                pass
            return
        default_name = f"articulos_export_{int(time.time())}.pdf"
        path = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF','*.pdf')], initialfile=default_name)
        if not path:
            return
        try:
            ok = ExportarService().exportar_a_pdf(path, selected_columns, rows)
            if ok:
                messagebox.showinfo('Exportar', f'Exportado correctamente a:\n{path}')
            else:
                messagebox.showerror('Exportar', 'Error exportando archivo. Revisa logs para más detalles.')
        except Exception as e:
            logger.exception('Error exportando PDF: %s', e)
            try:
                messagebox.showerror('Exportar', f'Error exportando PDF: {e}')
            except Exception:
                pass

