import customtkinter as ctk
import sqlite3
from database import connect
import webbrowser
from tkinter import messagebox # <--- ESTO ES VITAL PARA QUE SALGAN LAS VENTANAS
from database import ensure_product_schema
from datetime import datetime

class PantallaCrearProducto(ctk.CTkFrame):
    def __init__(self, parent, controller, producto_id=None):
        super().__init__(parent)
        self.controller = controller
        self.producto_id = producto_id
        self.pack(fill="both", expand=True)
        # Ensure DB schema for product extras
        try:
            ensure_product_schema()
        except Exception:
            pass

        # --- CABECERA ---
        header = ctk.CTkFrame(self, height=60)
        header.pack(fill="x", side="top", padx=10, pady=10)
        titulo_text = "NUEVA FICHA DE PRODUCTO" if not self.producto_id else "EDITAR FICHA DE PRODUCTO"
        ctk.CTkLabel(header, text=titulo_text, font=("Arial", 24, "bold")).pack(side="left", padx=20)
        # SINCRONIZAR button (placeholder)
        self.btn_sync = ctk.CTkButton(header, text='SINCRONIZAR', fg_color='#2F8FCD', width=120, command=lambda: None)
        self.btn_sync.pack(side="right", padx=6)
        # ID label (numeric DB id) - updated when editing/saving
        self.lbl_id_bd = ctk.CTkLabel(header, text=f"ID: {self.producto_id if self.producto_id else '-'}", font=("Arial", 12))
        self.lbl_id_bd.pack(side="right", padx=10)
        ctk.CTkButton(header, text="❌ Cancelar", fg_color="red", width=100,
              command=self.volver).pack(side="right", padx=10)

        # --- ÁREA DE SCROLL ---
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Tab view: General / Shopify
        self.tabview = ctk.CTkTabview(self.scroll_frame)
        self.tabview.pack(fill="both", expand=True)
        self.tabview.add("General")
        self.tabview.add("Shopify")

        gen_frame = self.tabview.tab("General")
        shop_frame = self.tabview.tab("Shopify")

        # BLOQUE 1: DATOS GENERALES (en pestaña General)
        self.crear_titulo_seccion("1. DATOS GENERALES", parent=gen_frame)
        f1 = ctk.CTkFrame(gen_frame, fg_color="transparent")
        f1.pack(fill="x", pady=5)
        self.entry_nombre = self.crear_campo_in_row(f1, "Nombre Completo:", size='small')
        self.entry_nombre_boton = self.crear_campo_in_row(f1, "Nombre Botón (Corto):", size='large')

        f2 = ctk.CTkFrame(gen_frame, fg_color="transparent")
        f2.pack(fill="x", pady=5)
        self.entry_sku = self.crear_campo_in_row(f2, "SKU (Código Interno):", size='small')

        f3 = ctk.CTkFrame(gen_frame, fg_color="transparent")
        f3.pack(fill="x", pady=5)
        # Categoría selector (values loaded from productos distinct categories)
        frame_cat = ctk.CTkFrame(f3, fg_color='transparent')
        frame_cat.pack(side='left', fill='x', expand=True, padx=6)
        ctk.CTkLabel(frame_cat, text='Categoría:', anchor='w').pack(fill='x')
        self.combo_categoria = ctk.CTkComboBox(frame_cat, values=[])
        self.combo_categoria.pack(fill='x')

        # Tipo selector (from 'tipos' table)
        frame_tipo = ctk.CTkFrame(f3, fg_color='transparent')
        frame_tipo.pack(side='left', fill='x', expand=True, padx=6)
        ctk.CTkLabel(frame_tipo, text='Tipo:', anchor='w').pack(fill='x')
        self.combo_tipo = ctk.CTkComboBox(frame_tipo, values=[])
        self.combo_tipo.pack(fill='x')

        # Proveedor selector (values loaded from proveedores table as 'Nombre (ID)')
        frame_prov = ctk.CTkFrame(f3, fg_color='transparent')
        frame_prov.pack(side='left', fill='x', expand=True, padx=6)
        ctk.CTkLabel(frame_prov, text='Proveedor:', anchor='w').pack(fill='x')
        self.combo_proveedor = ctk.CTkComboBox(frame_prov, values=[])
        self.combo_proveedor.pack(fill='x')

        # BLOQUE 2: ECONOMÍA
        self.crear_titulo_seccion("2. PRECIOS E IMPUESTOS", parent=gen_frame)
        f4 = ctk.CTkFrame(gen_frame, fg_color="transparent")
        f4.pack(fill="x", pady=5)
        self.entry_coste = self.crear_campo_in_row(f4, "Coste unitario (EUR):", size='small')
        self.entry_pvp = self.crear_campo_in_row(f4, "Precio de venta (EUR):", size='small')
        frame_iva = ctk.CTkFrame(f4, fg_color="transparent")
        frame_iva.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(frame_iva, text="IVA %:", anchor="w").pack(fill="x")
        self.combo_iva = ctk.CTkComboBox(frame_iva, values=["21", "10", "4", "0"])
        self.combo_iva.pack(fill="x")
        frame_switch = ctk.CTkFrame(f4, fg_color="transparent")
        frame_switch.pack(side="left", fill="x", expand=True, padx=20, pady=(20,0))
        self.switch_variable = ctk.CTkSwitch(frame_switch, text="¿PVP Variable?")
        self.switch_variable.pack()

        # BLOQUE 3: CÓDIGOS DE BARRAS
        self.crear_titulo_seccion("3. CÓDIGOS DE BARRAS (EAN)", parent=gen_frame)
        ctk.CTkLabel(gen_frame, text="Introduce los códigos (uno por línea):", anchor="w").pack(fill="x", padx=10)
        self.txt_ean = ctk.CTkTextbox(gen_frame, height=80)
        self.txt_ean.pack(fill="x", padx=10, pady=5)

        # BLOQUE 4: STOCK
        self.crear_titulo_seccion("4. INVENTARIO", parent=gen_frame)
        f5 = ctk.CTkFrame(gen_frame, fg_color="transparent")
        f5.pack(fill="x", pady=5)
        self.entry_stock = self.crear_campo_in_row(f5, "Stock actual:", size='small')
        self.entry_stock_min = self.crear_campo_in_row(f5, "Stock mínimo:", size='small')
        # Images: simple list with add button
        img_frame = ctk.CTkFrame(gen_frame, fg_color="transparent")
        img_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(img_frame, text="Imágenes:", text_color='gray').pack(anchor='w')
        self.images_list = ctk.CTkTextbox(img_frame, height=80)
        self.images_list.pack(fill='x', pady=4)
        def _add_image():
            from tkinter import filedialog
            path = filedialog.askopenfilename()
            if path:
                self.images_list.insert('end', path + '\n')
        ctk.CTkButton(img_frame, text='Añadir imagen', command=_add_image).pack(pady=4)

        # Active checkbox
        act_frame = ctk.CTkFrame(gen_frame, fg_color='transparent')
        act_frame.pack(fill='x', pady=5)
        self.chk_activo = ctk.CTkCheckBox(act_frame, text='Activo', command=lambda: None)
        self.chk_activo.pack(anchor='w', padx=6)

        # Cargar opciones de selectores (proveedores y categorías)
        try:
            self.cargar_selectores()
        except Exception:
            pass

        # Bind paste handler for SKU to avoid double-paste behavior
        try:
            self.entry_sku.bind('<Control-v>', self._on_entry_paste)
            try:
                # macOS Command-V
                self.entry_sku.bind('<Command-v>', self._on_entry_paste)
            except Exception:
                pass
            try:
                self.entry_sku.bind('<<Paste>>', self._on_entry_paste)
            except Exception:
                pass
        except Exception:
            pass

        # --- Shopify fields (no section title/line) ---
        # Título (full-width row)
        ctk.CTkLabel(shop_frame, text='Título', anchor='w').pack(fill='x', padx=6, pady=(6,0))
        self.entry_titulo = ctk.CTkEntry(shop_frame)
        self.entry_titulo.pack(fill='x', padx=6, pady=(0,6))

        # Descripción (full width)
        ctk.CTkLabel(shop_frame, text='Descripción (Shopify):', text_color='gray').pack(anchor='w', padx=6)
        self.txt_descripcion_shop = ctk.CTkTextbox(shop_frame, height=120)
        self.txt_descripcion_shop.pack(fill='both', padx=6, pady=6)

        # SEO Title
        ctk.CTkLabel(shop_frame, text='SEO Title', text_color='gray').pack(anchor='w', padx=6)
        self.entry_seo_title = ctk.CTkEntry(shop_frame)
        self.entry_seo_title.pack(fill='x', padx=6, pady=4)

        # SEO Description
        ctk.CTkLabel(shop_frame, text='SEO Description', text_color='gray').pack(anchor='w', padx=6)
        self.entry_seo_description = ctk.CTkEntry(shop_frame)
        self.entry_seo_description.pack(fill='x', padx=6, pady=4)

        # Taxonomía Shopify
        ctk.CTkLabel(shop_frame, text='Taxonomía Shopify', text_color='gray').pack(anchor='w', padx=6)
        self.entry_shopify_taxonomy = ctk.CTkEntry(shop_frame)
        self.entry_shopify_taxonomy.pack(fill='x', padx=6, pady=4)

        # Etiquetas
        ctk.CTkLabel(shop_frame, text='Etiquetas', text_color='gray').pack(anchor='w', padx=6)
        self.entry_etiquetas = ctk.CTkEntry(shop_frame)
        self.entry_etiquetas.pack(fill='x', padx=6, pady=4)

        # Tipo / Estado (same row, small)
        shop_row = ctk.CTkFrame(shop_frame, fg_color='transparent')
        shop_row.pack(fill='x', pady=4)
        # Shopify: categoría desplegable (tomada de la tabla categorias) y estado
        frame_shop_cat = ctk.CTkFrame(shop_row, fg_color='transparent')
        frame_shop_cat.pack(side='left', fill='x', expand=True, padx=6)
        ctk.CTkLabel(frame_shop_cat, text='Categoría:', anchor='w').pack(fill='x')
        self.combo_shop_categoria = ctk.CTkComboBox(frame_shop_cat, values=())
        self.combo_shop_categoria.pack(fill='x')

        self.entry_estado = self.crear_campo_in_row(shop_row, 'Estado:', size='small')

        # Link + Ir button (last row)
        link_row = ctk.CTkFrame(shop_frame, fg_color='transparent')
        link_row.pack(fill='x', pady=6, padx=6)
        link_entry_frame = ctk.CTkFrame(link_row, fg_color='transparent')
        link_entry_frame.pack(side='left', fill='x', expand=True)
        ctk.CTkLabel(link_entry_frame, text='Link', anchor='w').pack(fill='x')
        self.entry_link = ctk.CTkEntry(link_entry_frame)
        self.entry_link.pack(fill='x')
        ctk.CTkButton(link_row, text='Ir', width=60, command=lambda: self.ir_link()).pack(side='left', padx=8)

        # BOTONES: Guardar/Cancelar/Eliminar
        btns = ctk.CTkFrame(self.scroll_frame, fg_color='transparent')
        btns.pack(fill='x', pady=20)
        ctk.CTkButton(btns, text='💾 Guardar', fg_color='green', command=self.guardar_datos).pack(side='left', padx=6)
        ctk.CTkButton(btns, text='✖ Cancelar', fg_color='gray', command=self.volver).pack(side='left', padx=6)
        ctk.CTkButton(btns, text='🗑 Eliminar', fg_color='#AA3333', command=self._eliminar_producto).pack(side='left', padx=6)

        # History collapsible
        self.hist_frame = ctk.CTkFrame(self.scroll_frame, fg_color='#101010')
        self.hist_frame.pack(fill='x', pady=6)
        self.hist_visible = False
        def _toggle_hist():
            self.hist_visible = not self.hist_visible
            for w in self.hist_frame.winfo_children():
                w.destroy()
            if self.hist_visible:
                ctk.CTkLabel(self.hist_frame, text='Historial (últimos 5):', text_color='gray').pack(anchor='w', padx=6)
                # load history
                try:
                    conn = connect()
                    cur = conn.cursor()
                    cur.execute('SELECT usuario, fecha, cambios FROM product_history WHERE producto_id=? ORDER BY fecha DESC LIMIT 5', (self.producto_id,))
                    for u,f,c in cur.fetchall():
                        ctk.CTkLabel(self.hist_frame, text=f"{f} - {u} - {c}", text_color='white').pack(anchor='w', padx=6)
                    conn.close()
                except Exception:
                    pass
        ctk.CTkButton(self.scroll_frame, text='Mostrar/Ocultar Historial', command=_toggle_hist).pack(pady=6)

        # Si venimos a editar, cargar datos
        if self.producto_id:
            self.cargar_producto(self.producto_id)
        else:
            # ensure selectors (including Shopify tab combobox) are populated after widgets exist
            try:
                self.cargar_selectores()
            except Exception:
                pass

    # --- FUNCIONES AUXILIARES ---
    def crear_titulo_seccion(self, texto, parent=None):
        target = parent if parent is not None else self.scroll_frame
        ctk.CTkLabel(target, text=texto, font=("Arial", 16, "bold"), text_color="#3399FF").pack(pady=(20, 5), anchor="w", padx=10)
        ctk.CTkFrame(target, height=2, fg_color="#444444").pack(fill="x", padx=10, pady=(0,10))

    def cargar_selectores(self):
        # Load providers and categories from DB into the combo boxes
        try:
            conn = connect()
            cur = conn.cursor()
            provs = []
            self._prov_map = {}
            self._prov_rev = {}
            try:
                cur.execute('SELECT id, nombre FROM proveedores ORDER BY nombre')
                for pid, nombre in cur.fetchall():
                    label = f"{nombre} ({pid})"
                    provs.append(label)
                    self._prov_map[label] = pid
                    self._prov_rev[pid] = label
            except Exception:
                pass

            cats = []
            self._cat_tax = {}
            try:
                # Prefer canonical categories table with taxonomy
                cur.execute("SELECT nombre, shopify_taxonomy FROM categorias ORDER BY nombre")
                rows = cur.fetchall()
                if rows:
                    for nombre, tax in rows:
                        if nombre:
                            cats.append(nombre)
                            self._cat_tax[nombre] = tax or ''
                else:
                    # Fallback: take distinct categoria values from productos
                    cur.execute("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
                    cats = [r[0] for r in cur.fetchall() if r[0]]
                    for c in cats:
                        self._cat_tax[c] = ''
            except Exception:
                try:
                    cur.execute("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
                    cats = [r[0] for r in cur.fetchall() if r[0]]
                    for c in cats:
                        self._cat_tax[c] = ''
                except Exception:
                    pass
            # Tipos (separado)
            tipos = []
            try:
                cur.execute("SELECT nombre FROM tipos ORDER BY nombre")
                tipos = [r[0] for r in cur.fetchall() if r[0]]
            except Exception:
                tipos = []
            conn.close()
            if hasattr(self, 'combo_proveedor'):
                try:
                    self.combo_proveedor.configure(values=tuple(provs))
                    try:
                        # ensure no placeholder text like 'CTkCombobox' appears
                        self.combo_proveedor.set('')
                    except Exception:
                        pass
                except Exception:
                    pass
            if hasattr(self, 'combo_categoria'):
                try:
                    # set values and attach selection callback to populate taxonomy
                    try:
                        self.combo_categoria.configure(values=tuple(cats), command=self._on_categoria_selected)
                        try:
                            self.combo_categoria.set('')
                        except Exception:
                            pass
                    except Exception:
                        self.combo_categoria.configure(values=tuple(cats))
                        try:
                            self.combo_categoria.set('')
                        except Exception:
                            pass
                except Exception:
                    pass
            # populate tipos combobox in General tab if present
            if hasattr(self, 'combo_tipo'):
                try:
                    self.combo_tipo.configure(values=tuple(tipos))
                    try:
                        self.combo_tipo.set('')
                    except Exception:
                        pass
                except Exception:
                    pass
            # also populate the Shopify-tab category combobox if present
            if hasattr(self, 'combo_shop_categoria'):
                try:
                    try:
                        self.combo_shop_categoria.configure(values=tuple(cats), command=self._on_shop_categoria_selected)
                        try:
                            self.combo_shop_categoria.set('')
                        except Exception:
                            pass
                    except Exception:
                        self.combo_shop_categoria.configure(values=tuple(cats))
                        try:
                            self.combo_shop_categoria.set('')
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _on_categoria_selected(self, value):
        try:
            if not hasattr(self, 'entry_shopify_taxonomy'):
                return
            tax = self._cat_tax.get(value, '') if getattr(self, '_cat_tax', None) else ''
            # Only auto-fill if product field is empty
            curval = self.entry_shopify_taxonomy.get().strip()
            # only auto-fill when selecting category in the General tab
            # but do not overwrite product taxonomy if already present
            if not curval and tax:
                try:
                    self.entry_shopify_taxonomy.delete(0, 'end')
                    self.entry_shopify_taxonomy.insert(0, tax)
                except Exception:
                    pass
            # synchronize Shopify-tab combobox if present
            try:
                if hasattr(self, 'combo_shop_categoria'):
                    current = self.combo_shop_categoria.get()
                    if current != value:
                        try:
                            self.combo_shop_categoria.set(value)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def crear_campo(self, parent, label_text, width_percent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(frame, text=label_text, anchor="w").pack(fill="x")
        entry = ctk.CTkEntry(frame)
        entry.pack(fill="x")
        return entry

    def _on_entry_paste(self, event):
        """Handle paste into SKU entry to avoid duplicate insertion."""
        try:
            entry = self.entry_sku
            clip = ''
            try:
                clip = entry.clipboard_get()
            except Exception:
                try:
                    clip = self.clipboard_get()
                except Exception:
                    clip = ''
            if clip is None:
                clip = ''
            # remove current selection if any
            try:
                sel_first = entry.index('sel.first')
                sel_last = entry.index('sel.last')
                entry.delete(sel_first, sel_last)
                pos = sel_first
            except Exception:
                pos = entry.index('insert')
            # insert clipboard text once
            try:
                entry.insert(pos, clip)
            except Exception:
                pass
        except Exception:
            pass
        return "break"

    def crear_campo_in_row(self, parent, label_text, size='large', shopify=False):
        # size: 'large' or 'small'
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.pack(side='left', fill='x', expand=True, padx=6)
        ctk.CTkLabel(frame, text=label_text, anchor='w').pack(fill='x')
        width = 400 if size=='large' else 200
        kwargs = {}
        if shopify:
            kwargs = {'border_width':0}
        entry = ctk.CTkEntry(frame, width=width, **kwargs)
        entry.pack(fill='x')
        return entry

    def volver(self):
        # If we were opened from the Todos list and it saved a state, return there
        try:
            state = getattr(self.controller, 'todos_articulos_state', None)
            if state:
                try:
                    # mostrar_todos_articulos will restore the saved state in its __init__
                    self.controller.mostrar_todos_articulos()
                    return
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback to submenu/Inicio
        self.controller.mostrar_submenu_almacen()

    # --- LÓGICA DE GUARDADO ---
    def guardar_datos(self):
        print("--- EL BOTÓN FUNCIONA: INICIANDO GUARDADO ---")
        
        # Recogida de datos con manejo de errores simple
        try:
            nombre = self.entry_nombre.get()
            nombre_boton = self.entry_nombre_boton.get()
            titulo = self.entry_titulo.get() if hasattr(self, 'entry_titulo') else ''
            sku = self.entry_sku.get()
            # Categoria from combo (string)
            if hasattr(self, 'combo_categoria'):
                categoria = self.combo_categoria.get()
            else:
                categoria = ''

            # Tipo from combo (string)
            if hasattr(self, 'combo_tipo'):
                tipo_sel = self.combo_tipo.get()
            else:
                tipo_sel = ''

            # Proveedor: if combo maps to an ID, store the numeric ID, otherwise store the raw value
            if hasattr(self, 'combo_proveedor'):
                sel = self.combo_proveedor.get()
                proveedor = self._prov_map.get(sel, sel)
            else:
                proveedor = ''

            # (tipo is read earlier into tipo_sel)

            val_coste = self.entry_coste.get().replace(',', '.')
            coste = float(val_coste) if val_coste else 0.0

            val_pvp = self.entry_pvp.get().replace(',', '.')
            pvp = float(val_pvp) if val_pvp else 0.0

            iva = self.combo_iva.get()

            val_stock = self.entry_stock.get()
            stock = int(val_stock) if val_stock else 0
            val_stock_min = self.entry_stock_min.get() if hasattr(self, 'entry_stock_min') else '0'
            stock_min = int(val_stock_min) if val_stock_min else 0

            # Switch: a veces devuelve 1/0, a veces True/False, protegemos esto:
            es_variable = 1 if self.switch_variable.get() else 0

            texto_eans = self.txt_ean.get("1.0", "end")
            lista_eans = [e.strip() for e in texto_eans.split('\n') if e.strip()]

            descripcion_shop = self.txt_descripcion_shop.get('1.0', 'end') if hasattr(self, 'txt_descripcion_shop') else ''
            seo_title = self.entry_seo_title.get() if hasattr(self, 'entry_seo_title') else ''
            seo_desc = self.entry_seo_description.get() if hasattr(self, 'entry_seo_description') else ''
            shopify_taxonomy = self.entry_shopify_taxonomy.get() if hasattr(self, 'entry_shopify_taxonomy') else ''
            tipo_shop = self.entry_tipo_shop.get() if hasattr(self, 'entry_tipo_shop') else ''
            estado = self.entry_estado.get() if hasattr(self, 'entry_estado') else ''
            etiquetas = self.entry_etiquetas.get() if hasattr(self, 'entry_etiquetas') else ''
            link = self.entry_link.get() if hasattr(self, 'entry_link') else ''
            activo = 1 if getattr(self, 'chk_activo', None) and self.chk_activo.get() else 1

            # Validar
            if not nombre or not sku:
                messagebox.showerror("Faltan Datos", "¡El Nombre y el SKU son obligatorios!")
                return
            # require categoria and tipo when using the new comboboxes
            if hasattr(self, 'combo_categoria') and not categoria:
                messagebox.showerror('Faltan Datos', 'La Categoría es obligatoria')
                return
            if hasattr(self, 'combo_tipo') and not tipo_sel:
                messagebox.showerror('Faltan Datos', 'El Tipo es obligatorio')
                return

            # Validaciones: SKU único
            conn = connect()
            cur = conn.cursor()
            cur.execute('SELECT id FROM productos WHERE sku = ? LIMIT 1', (sku,))
            row_sku = cur.fetchone()
            if row_sku and (not self.producto_id or row_sku[0] != self.producto_id):
                conn.close()
                messagebox.showerror('SKU duplicado', 'El SKU ya existe para otro producto')
                return

            # Price/stock non-negative
            if pvp < 0 or coste < 0 or stock < 0 or stock_min < 0:
                messagebox.showerror('Valores inválidos', 'Precio y stock no pueden ser negativos')
                conn.close()
                return

            # Conexión DB
            # Use existing conn/cur
            now = datetime.now().isoformat(sep=' ', timespec='seconds')
            pending = 1 if getattr(self.controller, 'offline_mode', False) else 0
            if not self.producto_id:
                cur.execute('''
                    INSERT INTO productos (nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, created_at, updated_at, descripcion_shopify, pending_sync)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nombre, nombre_boton, sku, categoria, proveedor, int(iva), stock, es_variable, titulo, stock_min, activo, now, now, descripcion_shop, pending))
                producto_id = cur.lastrowid
            else:
                producto_id = self.producto_id
                cur.execute('''
                    UPDATE productos SET nombre=?, nombre_boton=?, sku=?, categoria=?, proveedor=?, tipo_iva=?, stock_actual=?, pvp_variable=?, titulo=?, stock_minimo=?, activo=?, updated_at=?, descripcion_shopify=?, pending_sync=?
                    WHERE id=?
                ''', (nombre, nombre_boton, sku, categoria, proveedor, int(iva), stock, es_variable, titulo, stock_min, activo, now, descripcion_shop, pending, producto_id))

            # If the productos table has a tipo-like column, update it with the selected tipo
            try:
                try:
                    cur.execute('PRAGMA table_info(productos)')
                    cols = [c[1] for c in cur.fetchall()]
                except Exception:
                    cols = []
                tipo_candidates = ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']
                for tc in tipo_candidates:
                    if tc in cols:
                        try:
                            cur.execute(f'UPDATE productos SET {tc}=? WHERE id=?', (tipo_sel, producto_id))
                        except Exception:
                            pass
                        break
            except Exception:
                pass

            # Precios: desactivar antiguos and add new price record
            cur.execute('UPDATE precios SET activo=0 WHERE producto_id=?', (producto_id,))
            cur.execute('INSERT INTO precios (producto_id, pvp, coste, fecha_registro, activo) VALUES (?, ?, ?, ?, 1)', (producto_id, pvp, coste, now))

            # EANs
            cur.execute('DELETE FROM codigos_barras WHERE producto_id=?', (producto_id,))
            for ean_limpio in lista_eans:
                cur.execute('INSERT INTO codigos_barras (producto_id, ean) VALUES (?, ?)', (producto_id, ean_limpio))

            # Images: store paths
            try:
                cur.execute('DELETE FROM product_images WHERE producto_id=?', (producto_id,))
                imgs = [i.strip() for i in self.images_list.get('1.0', 'end').split('\n') if i.strip()]
                for pth in imgs:
                    cur.execute('INSERT INTO product_images (producto_id, path) VALUES (?, ?)', (producto_id, pth))
            except Exception:
                pass

            # Shopify fields (update optional columns if they exist)
            try:
                cur.execute('UPDATE productos SET descripcion_shopify=?, updated_at=? WHERE id=?', (descripcion_shop, now, producto_id))
                try:
                    cur.execute('UPDATE productos SET link=? WHERE id=?', (link, producto_id))
                except Exception:
                    pass
                try:
                    cur.execute('UPDATE productos SET shopify_taxonomy=? WHERE id=?', (shopify_taxonomy, producto_id))
                except Exception:
                    pass
            except Exception:
                pass

            # History: store a minimal change record
            try:
                cambios = []
                if self.producto_id:
                    # compare previous values
                    cur.execute('SELECT nombre, sku FROM productos WHERE id=?', (producto_id,))
                    # note: this reads current values after update; for a robust diff we'd fetch before update. Keep minimal.
                cambios_txt = f"Saved at {now}"
                cur.execute('INSERT INTO product_history (producto_id, usuario, fecha, cambios) VALUES (?, ?, ?, ?)', (producto_id, getattr(self.controller, 'usuario', 'user'), now, cambios_txt))
            except Exception:
                pass

            conn.commit()
            conn.close()
            print("--- GUARDADO EN BD EXITOSO ---")
            # update internal id and header label
            try:
                self.producto_id = producto_id
                self.lbl_id_bd.configure(text=f"ID: {producto_id}")
            except Exception:
                pass
            # Emit event for sync
            try:
                print(f"evento: producto:actualizado -> {{'sku': '{sku}', 'updated_at': '{now}'}}")
            except Exception:
                pass
            messagebox.showinfo("¡Hecho!", f"Producto '{nombre}' guardado correctamente.")
            self.limpiar_formulario()

        except sqlite3.IntegrityError:
            messagebox.showerror("Error SKU", "Ese SKU ya existe. Cámbialo.")
        except Exception as e:
            print(f"ERROR: {e}") # Ver error en consola
            messagebox.showerror("Error", f"Algo falló: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def limpiar_formulario(self):
        self.entry_nombre.delete(0, 'end')
        self.entry_nombre_boton.delete(0, 'end')
        self.entry_sku.delete(0, 'end')
        if hasattr(self, 'combo_categoria'):
            try:
                self.combo_categoria.set('')
            except Exception:
                pass
        else:
            try:
                self.entry_categoria.delete(0, 'end')
            except Exception:
                pass
        if hasattr(self, 'combo_proveedor'):
            try:
                self.combo_proveedor.set('')
            except Exception:
                pass
        else:
            try:
                self.entry_proveedor.delete(0, 'end')
            except Exception:
                pass
        self.entry_coste.delete(0, 'end')
        self.entry_pvp.delete(0, 'end')
        self.entry_stock.delete(0, 'end')
        self.txt_ean.delete("1.0", "end")
        self.switch_variable.deselect()
        try:
            self.lbl_id_bd.configure(text=f"ID: -")
            self.producto_id = None
        except Exception:
            pass
        try:
            if hasattr(self, 'entry_link'):
                self.entry_link.delete(0, 'end')
        except Exception:
            pass
        # ensure shopify taxonomy is cleared as requested
        try:
            if hasattr(self, 'entry_shopify_taxonomy'):
                self.entry_shopify_taxonomy.delete(0, 'end')
        except Exception:
            pass

    def cargar_producto(self, producto_id):
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute('SELECT nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, descripcion_shopify, created_at, updated_at, pending_sync FROM productos WHERE id=?', (producto_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return
                return
            (nombre, nombre_boton, sku, categoria, proveedor, tipo_iva, stock_actual, pvp_variable, titulo, stock_minimo, activo, descripcion_shopify, created_at, updated_at, pending_sync) = row
            self.entry_nombre.delete(0, 'end'); self.entry_nombre.insert(0, nombre)
            self.entry_nombre_boton.delete(0, 'end'); self.entry_nombre_boton.insert(0, nombre_boton or '')
            self.entry_sku.delete(0, 'end'); self.entry_sku.insert(0, sku or '')
            if hasattr(self, 'entry_titulo'):
                self.entry_titulo.delete(0, 'end'); self.entry_titulo.insert(0, titulo or '')
            # Category -> combo
            try:
                if hasattr(self, 'combo_categoria'):
                    self.combo_categoria.set(category_or := (categoria or ''))
                else:
                    self.entry_categoria.delete(0, 'end'); self.entry_categoria.insert(0, category_or := (categoria or ''))
            except Exception:
                pass

            # If product-level taxonomy not set, try to fill from categorias table mapping
            try:
                if hasattr(self, 'entry_shopify_taxonomy'):
                    # product may already have shopify_taxonomy saved (loaded below); only overwrite if empty
                    curval = self.entry_shopify_taxonomy.get().strip()
                    if not curval:
                        # try mapping
                        if getattr(self, '_cat_tax', None):
                            tax = self._cat_tax.get(category_or, '')
                            if tax:
                                try:
                                    self.entry_shopify_taxonomy.delete(0, 'end')
                                    self.entry_shopify_taxonomy.insert(0, tax)
                                except Exception:
                                    pass
                        else:
                            # fallback: try reading from categorias table directly
                            try:
                                conn2 = connect()
                                cur2 = conn2.cursor()
                                cur2.execute('SELECT shopify_taxonomy FROM categorias WHERE nombre=? LIMIT 1', (category_or,))
                                r = cur2.fetchone()
                                conn2.close()
                                if r and r[0]:
                                    try:
                                        self.entry_shopify_taxonomy.delete(0, 'end')
                                        self.entry_shopify_taxonomy.insert(0, r[0])
                                    except Exception:
                                        pass
                            except Exception:
                                pass
            except Exception:
                pass

            # Provider -> combo (try to map numeric id to display label)
            try:
                if hasattr(self, 'combo_proveedor'):
                    display = None
                    # proveedor might be stored as integer id or as string name
                    try:
                        pid_val = int(proveedor) if proveedor is not None and str(proveedor).isdigit() else None
                    except Exception:
                        pid_val = None
                    if pid_val and getattr(self, '_prov_rev', None):
                        display = self._prov_rev.get(pid_val)
                    if not display and getattr(self, '_prov_map', None):
                        for lbl, pid in self._prov_map.items():
                            if lbl.startswith(str(proveedor)):
                                display = lbl
                                break
                    if display:
                        self.combo_proveedor.set(display)
                    else:
                        self.combo_proveedor.set(str(proveedor or ''))
                else:
                    self.entry_proveedor.delete(0, 'end'); self.entry_proveedor.insert(0, proveedor or '')
            except Exception:
                pass
            # also set Shopify tab category combobox to current category if present
            try:
                if hasattr(self, 'combo_shop_categoria'):
                    try:
                        self.combo_shop_categoria.set(category_or)
                    except Exception:
                        pass
            except Exception:
                pass
            self.combo_iva.set(str(tipo_iva))
            self.entry_stock.delete(0, 'end'); self.entry_stock.insert(0, str(stock_actual or 0))
            if hasattr(self, 'entry_stock_min'):
                self.entry_stock_min.delete(0, 'end'); self.entry_stock_min.insert(0, str(stock_minimo or 0))
            if pvp_variable:
                try:
                    self.switch_variable.select()
                except Exception:
                    pass

            # Precio activo
            cursor.execute('SELECT pvp, coste FROM precios WHERE producto_id=? AND activo=1 LIMIT 1', (producto_id,))
            pr = cursor.fetchone()
            if pr:
                pvp, coste = pr
                self.entry_pvp.delete(0, 'end'); self.entry_pvp.insert(0, str(pvp))
                self.entry_coste.delete(0, 'end'); self.entry_coste.insert(0, str(coste))

            # EANs
            cursor.execute('SELECT ean FROM codigos_barras WHERE producto_id=?', (producto_id,))
            eans = [r[0] for r in cursor.fetchall()]
            self.txt_ean.delete('1.0', 'end')
            if eans:
                self.txt_ean.insert('1.0', '\n'.join(eans))

            # Images
            try:
                cursor.execute('SELECT path FROM product_images WHERE producto_id=?', (producto_id,))
                imgs = [r[0] for r in cursor.fetchall()]
                self.images_list.delete('1.0', 'end')
                for pth in imgs:
                    self.images_list.insert('end', pth + '\n')
            except Exception:
                pass

            # Shopify fields
            try:
                if hasattr(self, 'txt_descripcion_shop'):
                    self.txt_descripcion_shop.delete('1.0', 'end')
                    self.txt_descripcion_shop.insert('1.0', descripcion_shopify or '')
                # SEO and others may be stored in productos.notes or separate table; try to fetch from productos columns if exist
                try:
                    cursor.execute('PRAGMA table_info(productos)')
                    cols = [c[1] for c in cursor.fetchall()]
                    if 'seo_title' in cols:
                        cursor.execute('SELECT seo_title FROM productos WHERE id=?', (producto_id,))
                        r = cursor.fetchone(); self.entry_seo_title.delete(0,'end'); self.entry_seo_title.insert(0, r[0] if r else '')
                    # link field if present
                    if 'link' in cols and hasattr(self, 'entry_link'):
                        try:
                            cursor.execute('SELECT link FROM productos WHERE id=?', (producto_id,))
                            rl = cursor.fetchone()
                            self.entry_link.delete(0, 'end')
                            if rl and rl[0]:
                                self.entry_link.insert(0, rl[0])
                        except Exception:
                            pass
                    # shopify_taxonomy: clear by default; user may fill or select category in Shopify tab to auto-fill
                    if 'shopify_taxonomy' in cols and hasattr(self, 'entry_shopify_taxonomy'):
                        try:
                            self.entry_shopify_taxonomy.delete(0, 'end')
                        except Exception:
                            pass
                except Exception:
                    pass

            except Exception:
                pass

            # Load tipo value if the productos table contains a tipo-like column
            try:
                cursor.execute('PRAGMA table_info(productos)')
                pcols = [c[1] for c in cursor.fetchall()]
                tipo_candidates = ['tipo', 'tipo_id', 'id_tipo', 'tipo_shop']
                tipo_val = ''
                for tc in tipo_candidates:
                    if tc in pcols:
                        try:
                            cursor.execute(f'SELECT {tc} FROM productos WHERE id=? LIMIT 1', (producto_id,))
                            tr = cursor.fetchone()
                            tipo_val = tr[0] if tr and tr[0] is not None else ''
                        except Exception:
                            tipo_val = ''
                        break
                if tipo_val and hasattr(self, 'combo_tipo'):
                    try:
                        self.combo_tipo.set(str(tipo_val))
                    except Exception:
                        pass
            except Exception:
                pass

            conexion.close()
        except Exception as e:
            print(f"Error cargando producto {producto_id}: {e}")

    def _on_shop_categoria_selected(self, value):
        """When selecting a category in the Shopify tab, populate taxonomy into the product taxonomy field (editable)."""
        try:
            tax = self._cat_tax.get(value, '') if getattr(self, '_cat_tax', None) else ''
            if hasattr(self, 'entry_shopify_taxonomy'):
                try:
                    self.entry_shopify_taxonomy.delete(0, 'end')
                    if tax:
                        self.entry_shopify_taxonomy.insert(0, tax)
                except Exception:
                    pass
        except Exception:
            pass
        # also sync back to General tab category combobox if present
        try:
            if hasattr(self, 'combo_categoria'):
                curv = self.combo_categoria.get()
                if curv != value:
                    try:
                        self.combo_categoria.set(value)
                    except Exception:
                        pass
        except Exception:
            pass

    def ir_link(self):
        try:
            if not hasattr(self, 'entry_link'):
                return
            url = self.entry_link.get().strip()
            if not url:
                return
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
            webbrowser.open(url)
        except Exception:
            pass

    def _eliminar_producto(self):
        try:
            if not getattr(self, 'producto_id', None):
                messagebox.showinfo('Eliminar', 'No hay producto seleccionado.')
                return
            if not messagebox.askyesno('Confirmar', '¿Eliminar este producto?'):
                return
            try:
                conn = connect()
                cur = conn.cursor()
                pid = int(self.producto_id)
                # Delete related rows safely
                try:
                    cur.execute('DELETE FROM precios WHERE producto_id=?', (pid,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM codigos_barras WHERE producto_id=?', (pid,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM product_images WHERE producto_id=?', (pid,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM product_history WHERE producto_id=?', (pid,))
                except Exception:
                    pass
                try:
                    cur.execute('DELETE FROM productos WHERE id=?', (pid,))
                except Exception:
                    pass
                conn.commit()
                conn.close()
            except Exception:
                pass
            messagebox.showinfo('Eliminar', 'Producto eliminado.')
            try:
                self.controller.mostrar_todos_articulos()
            except Exception:
                pass
        except Exception:
            messagebox.showerror('Error', 'No se pudo eliminar el producto.')