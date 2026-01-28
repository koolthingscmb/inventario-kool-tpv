import customtkinter as ctk
from modulos.almacen.producto_service import ProductoService
import database
import webbrowser
from tkinter import messagebox # <--- ESTO ES VITAL PARA QUE SALGAN LAS VENTANAS
from database import ensure_product_schema
from datetime import datetime

class PantallaCrearProducto(ctk.CTkFrame):
    def __init__(self, parent, controller, producto_id=None):
        super().__init__(parent)
        self.controller = controller
        self.producto_id = producto_id
        self.service = ProductoService()
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
                    detalle = self.service.obtener_producto_completo(self.producto_id) or {}
                    historial = detalle.get('historial', [])
                    for h in historial:
                        try:
                            f = h.get('fecha')
                            u = h.get('usuario')
                            c = h.get('cambios')
                            ctk.CTkLabel(self.hist_frame, text=f"{f} - {u} - {c}", text_color='white').pack(anchor='w', padx=6)
                        except Exception:
                            pass
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
        # Load providers, categories and tipos via service (no SQL in UI)
        try:
            datos = self.service.obtener_datos_maestros()
            provs = []
            self._prov_map = {}
            self._prov_rev = {}
            for p in datos.get('proveedores', []):
                try:
                    pid = p.get('id')
                    nombre = p.get('nombre')
                    label = f"{nombre} ({pid})"
                    provs.append(label)
                    self._prov_map[label] = pid
                    self._prov_rev[pid] = label
                except Exception:
                    pass

            cats = [c.get('nombre') for c in datos.get('categorias', []) if c.get('nombre')]
            self._cat_tax = {c.get('nombre'): c.get('shopify_taxonomy', '') for c in datos.get('categorias', []) if c.get('nombre')}

            tipos = datos.get('tipos', []) or []

            if hasattr(self, 'combo_proveedor'):
                try:
                    self.combo_proveedor.configure(values=tuple(provs))
                    try:
                        self.combo_proveedor.set('')
                    except Exception:
                        pass
                except Exception:
                    pass

            if hasattr(self, 'combo_categoria'):
                try:
                    self.combo_categoria.configure(values=tuple(cats), command=self._on_categoria_selected)
                    try:
                        self.combo_categoria.set('')
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.combo_categoria.configure(values=tuple(cats))
                    except Exception:
                        pass

            if hasattr(self, 'combo_tipo'):
                try:
                    self.combo_tipo.configure(values=tuple(tipos))
                    try:
                        self.combo_tipo.set('')
                    except Exception:
                        pass
                except Exception:
                    pass

            if hasattr(self, 'combo_shop_categoria'):
                try:
                    self.combo_shop_categoria.configure(values=tuple(cats), command=self._on_shop_categoria_selected)
                    try:
                        self.combo_shop_categoria.set('')
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.combo_shop_categoria.configure(values=tuple(cats))
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

            # Price/stock non-negative
            if pvp < 0 or coste < 0 or stock < 0 or stock_min < 0:
                messagebox.showerror('Valores inválidos', 'Precio y stock no pueden ser negativos')
                return

            # Preparar datos para el servicio
            now = datetime.now().isoformat(sep=' ', timespec='seconds')
            pending = 1 if getattr(self.controller, 'offline_mode', False) else 0
            lista_imagenes = [i.strip() for i in self.images_list.get('1.0', 'end').split('\n') if i.strip()]

            datos_producto = {
                'id': self.producto_id,
                'nombre': nombre,
                'nombre_boton': nombre_boton,
                'titulo': titulo,
                'sku': sku,
                'categoria': categoria,
                'tipo': tipo_sel,
                'proveedor': proveedor,
                'coste': coste,
                'pvp': pvp,
                'tipo_iva': int(iva) if iva else 0,
                'stock_actual': stock,
                'stock_minimo': stock_min,
                'pvp_variable': es_variable,
                'descripcion_shopify': descripcion_shop.strip(),
                'shopify_taxonomy': shopify_taxonomy,
                'link': link,
                'activo': activo,
                'pending_sync': pending,
                'usuario': getattr(self.controller, 'usuario', 'user'),
                'cambios': f"Saved at {now}",
                'seo_title': seo_title,
                'seo_desc': seo_desc,
                'tipo_shop': tipo_shop,
                'estado': estado,
                'etiquetas': etiquetas,
            }

            try:
                producto_id = self.service.guardar_producto(datos_producto, lista_eans, lista_imagenes)
            except Exception as e:
                print(f"ERROR guardando producto via servicio: {e}")
                messagebox.showerror('Error', f'No se pudo guardar el producto: {e}')
                return

            if producto_id:
                print('--- GUARDADO VIA SERVICE EXITOSO ---')
                try:
                    self.producto_id = producto_id
                    self.lbl_id_bd.configure(text=f"ID: {producto_id}")
                except Exception:
                    pass
                try:
                    print(f"evento: producto:actualizado -> {{'sku': '{sku}', 'updated_at': '{now}'}}")
                except Exception:
                    pass
                messagebox.showinfo("¡Hecho!", f"Producto '{nombre}' guardado correctamente.")
                self.limpiar_formulario()
            else:
                messagebox.showerror('Error', 'No se pudo guardar el producto. Revisa los logs.')
        except Exception as e:
            print(f"ERROR: {e}")
            messagebox.showerror("Error", f"Algo falló: {e}")

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
            detalle = self.service.obtener_producto_completo(producto_id) or {}
            producto = detalle.get('producto', {})
            precio = detalle.get('precio') or {}
            eans = detalle.get('eans', []) or []
            imagenes = detalle.get('imagenes', []) or []
            tipo_val = detalle.get('tipo')

            nombre = producto.get('nombre', '')
            nombre_boton = producto.get('nombre_boton', '')
            sku = producto.get('sku', '')
            categoria = producto.get('categoria', '')
            proveedor = producto.get('proveedor', '')
            tipo_iva = producto.get('tipo_iva', producto.get('tipo_iva', 0))
            stock_actual = producto.get('stock_actual', 0)
            pvp_variable = int(producto.get('pvp_variable', 0) or 0)
            titulo = producto.get('titulo', '')
            stock_minimo = producto.get('stock_minimo', 0)
            activo = int(producto.get('activo', 1) or 1)
            descripcion_shopify = producto.get('descripcion_shopify', '')

            # rellenar campos UI
            try:
                self.entry_nombre.delete(0, 'end'); self.entry_nombre.insert(0, nombre)
                self.entry_nombre_boton.delete(0, 'end'); self.entry_nombre_boton.insert(0, nombre_boton or '')
                self.entry_sku.delete(0, 'end'); self.entry_sku.insert(0, sku or '')
                if hasattr(self, 'entry_titulo'):
                    self.entry_titulo.delete(0, 'end'); self.entry_titulo.insert(0, titulo or '')
            except Exception:
                pass

            # Categoria / proveedor
            try:
                if hasattr(self, 'combo_categoria'):
                    try:
                        self.combo_categoria.set(categoria or '')
                    except Exception:
                        pass
                else:
                    try:
                        self.entry_categoria.delete(0, 'end'); self.entry_categoria.insert(0, categoria or '')
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if hasattr(self, 'combo_proveedor'):
                    display = None
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
                        try:
                            self.combo_proveedor.set(display)
                        except Exception:
                            pass
                    else:
                        try:
                            self.combo_proveedor.set(str(proveedor or ''))
                        except Exception:
                            pass
                else:
                    try:
                        self.entry_proveedor.delete(0, 'end'); self.entry_proveedor.insert(0, proveedor or '')
                    except Exception:
                        pass
            except Exception:
                pass

            # otros campos
            try:
                try:
                    self.combo_shop_categoria.set(categoria or '')
                except Exception:
                    pass
            except Exception:
                pass
            try:
                self.combo_iva.set(str(tipo_iva))
            except Exception:
                pass
            try:
                self.entry_stock.delete(0, 'end'); self.entry_stock.insert(0, str(stock_actual or 0))
            except Exception:
                pass
            if hasattr(self, 'entry_stock_min'):
                try:
                    self.entry_stock_min.delete(0, 'end'); self.entry_stock_min.insert(0, str(stock_minimo or 0))
                except Exception:
                    pass
            try:
                if pvp_variable:
                    self.switch_variable.select()
                else:
                    self.switch_variable.deselect()
            except Exception:
                pass

            # precio activo
            try:
                if precio:
                    self.entry_pvp.delete(0, 'end'); self.entry_pvp.insert(0, str(precio.get('pvp', '')))
                    self.entry_coste.delete(0, 'end'); self.entry_coste.insert(0, str(precio.get('coste', '')))
            except Exception:
                pass

            # EANs
            try:
                self.txt_ean.delete('1.0', 'end')
                if eans:
                    self.txt_ean.insert('1.0', '\n'.join(eans))
            except Exception:
                pass

            # Images
            try:
                self.images_list.delete('1.0', 'end')
                for pth in imagenes:
                    try:
                        self.images_list.insert('end', pth + '\n')
                    except Exception:
                        pass
            except Exception:
                pass

            # Shopify fields and optional columns
            try:
                if hasattr(self, 'txt_descripcion_shop'):
                    try:
                        self.txt_descripcion_shop.delete('1.0', 'end')
                        self.txt_descripcion_shop.insert('1.0', descripcion_shopify or '')
                    except Exception:
                        pass
                try:
                    if hasattr(self, 'entry_seo_title') and producto.get('seo_title'):
                        self.entry_seo_title.delete(0, 'end'); self.entry_seo_title.insert(0, producto.get('seo_title'))
                except Exception:
                    pass
                try:
                    if hasattr(self, 'entry_link') and producto.get('link'):
                        self.entry_link.delete(0, 'end'); self.entry_link.insert(0, producto.get('link'))
                except Exception:
                    pass
                try:
                    if hasattr(self, 'entry_shopify_taxonomy'):
                        val = producto.get('shopify_taxonomy') or self._cat_tax.get(categoria, '')
                        self.entry_shopify_taxonomy.delete(0, 'end')
                        if val:
                            self.entry_shopify_taxonomy.insert(0, val)
                except Exception:
                    pass
            except Exception:
                pass

            # tipo
            try:
                if tipo_val and hasattr(self, 'combo_tipo'):
                    try:
                        self.combo_tipo.set(str(tipo_val))
                    except Exception:
                        pass
            except Exception:
                pass
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
                ok = self.service.eliminar_producto(self.producto_id)
            except Exception as e:
                print(f"ERROR eliminando producto via servicio: {e}")
                ok = False
            if ok:
                messagebox.showinfo('Eliminar', 'Producto eliminado.')
                try:
                    self.controller.mostrar_todos_articulos()
                except Exception:
                    pass
            else:
                messagebox.showerror('Error', 'No se pudo eliminar el producto.')
        except Exception:
            messagebox.showerror('Error', 'No se pudo eliminar el producto.')