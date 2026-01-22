import customtkinter as ctk
import sqlite3
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from database import connect, DB_PATH

class PantallaCategoriasTipos(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill='both', expand=True)
        # configure grid so left and right panes share space
        try:
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(1, weight=1)
        except Exception:
            pass

        # Header
        header = ctk.CTkFrame(self, height=50)
        header.grid(row=0, column=0, columnspan=2, sticky='ew', padx=8, pady=(8,4))
        ctk.CTkLabel(header, text='GESTOR DE CATEGORÍAS & TIPOS', font=('Arial', 18, 'bold')).pack(side='left', padx=8)
        ctk.CTkButton(header, text='Volver', fg_color='gray', command=self._volver).pack(side='right', padx=8)

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=8, pady=8)
        self.tabview.add('Categorías')
        self.tabview.add('Tipos')

        self.tab_cats = self.tabview.tab('Categorías')
        self.tab_tipos = self.tabview.tab('Tipos')

        # Build tabs
        self._build_tab(self.tab_cats, table='categorias')
        self._build_tab(self.tab_tipos, table='tipos')

        # Ensure tables exist
        self._ensure_tables()

    def _ensure_tables(self):
        conn = connect()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS categorias (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE,
                        descripcion TEXT,
                        shopify_taxonomy TEXT,
                        created_at TEXT,
                        updated_at TEXT
                      )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS tipos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE,
                        descripcion TEXT,
                        shopify_taxonomy TEXT,
                        created_at TEXT,
                        updated_at TEXT
                      )''')
        conn.commit()
        conn.close()

    def _build_tab(self, parent, table='categorias'):
        # ensure parent tab uses two equal-width columns
        try:
            parent.grid_columnconfigure(0, weight=1, uniform='cols')
            parent.grid_columnconfigure(1, weight=1, uniform='cols')
            # ensure the main rows of the tab expand so both panes fill available vertical space
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_rowconfigure(1, weight=1)
        except Exception:
            pass

        # Left: listbox with scrollbar
        left = ctk.CTkFrame(parent, fg_color='transparent')
        left.grid(row=0, column=0, sticky='nsew', padx=(8,4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(left, text=table.capitalize(), font=('Arial', 14, 'bold'))
        lbl.grid(row=0, column=0, sticky='w', padx=6, pady=(6,4))

        list_container = ctk.CTkFrame(left, fg_color='transparent')
        list_container.grid(row=1, column=0, sticky='nsew', padx=6, pady=6)
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        # native Listbox for stability
        listbox = tk.Listbox(list_container, activestyle='none', exportselection=False)
        scrollbar = tk.Scrollbar(list_container, orient='vertical', command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        setattr(self, f'listbox_{table}', listbox)
        setattr(self, f'_list_items_{table}', [])

        btns = ctk.CTkFrame(left)
        btns.grid(row=2, column=0, sticky='ew', pady=6, padx=6)
        ctk.CTkButton(btns, text='Crear', width=90, command=lambda t=table: self._crear_nuevo(t)).pack(side='left', padx=4)
        ctk.CTkButton(btns, text='Borrar', width=90, fg_color='#AA3333', command=lambda t=table: self._borrar_seleccionado(t)).pack(side='left', padx=4)

        # Right: detail form
        right = ctk.CTkFrame(parent, fg_color='transparent')
        right.grid(row=0, column=1, rowspan=3, sticky='nsew', padx=(4,8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)
        setattr(self, f'right_{table}', right)

        # Build right pane using grid so it expands cleanly
        hdr = ctk.CTkFrame(right, fg_color='transparent')
        hdr.grid(row=0, column=0, sticky='ew', padx=6, pady=(2,6))
        lbl_id = ctk.CTkLabel(hdr, text='ID: -', font=('Arial', 12))
        lbl_id.pack(side='right')
        setattr(self, f'lbl_id_{table}', lbl_id)

        # Nombre
        ctk.CTkLabel(right, text='Nombre', anchor='w').grid(row=1, column=0, sticky='w', padx=6)
        entry_nombre = ctk.CTkEntry(right)
        entry_nombre.grid(row=2, column=0, sticky='ew', padx=6, pady=4)
        setattr(self, f'entry_nombre_{table}', entry_nombre)

        # Descripción (expande)
        ctk.CTkLabel(right, text='Descripción', anchor='w').grid(row=3, column=0, sticky='w', padx=6)
        entry_desc = ctk.CTkTextbox(right, height=120)
        entry_desc.grid(row=4, column=0, sticky='nsew', padx=6, pady=4)
        setattr(self, f'entry_desc_{table}', entry_desc)

        # Shopify Taxonomy: only for Categorías
        if table == 'categorias':
            ctk.CTkLabel(right, text='Taxonomía Shopify', anchor='w').grid(row=5, column=0, sticky='w', padx=6, pady=(8,0))
            entry_shop_tax = ctk.CTkEntry(right)
            entry_shop_tax.grid(row=6, column=0, sticky='ew', padx=6, pady=4)
            setattr(self, f'entry_shopify_taxonomy_{table}', entry_shop_tax)
        else:
            # ensure attribute exists for tipos but do not render the widget
            setattr(self, f'entry_shopify_taxonomy_{table}', None)

        # Bottom buttons
        fbot = ctk.CTkFrame(right)
        fbot.grid(row=7, column=0, sticky='ew', padx=6, pady=8)
        ctk.CTkButton(fbot, text='Guardar', fg_color='green', command=lambda t=table: self._guardar(t)).pack(side='left', padx=6)
        ctk.CTkButton(fbot, text='Limpiar', command=lambda t=table: self._limpiar_form(t)).pack(side='left', padx=6)

        # configure right pane grid weights so description expands and right pane fills vertical space
        try:
            right.grid_rowconfigure(4, weight=1)
            right.grid_rowconfigure(0, weight=0)
            right.grid_rowconfigure(1, weight=0)
            right.grid_rowconfigure(2, weight=0)
            right.grid_rowconfigure(3, weight=0)
            right.grid_rowconfigure(5, weight=0)
            right.grid_rowconfigure(6, weight=0)
            right.grid_rowconfigure(7, weight=0)
            right.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        # bind selection and load list
        try:
            listbox.bind('<<ListboxSelect>>', lambda e, t=table: self._on_listbox_select(e, t))
        except Exception:
            pass
        self._cargar_lista(table)

    def _cargar_lista(self, table):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(f'SELECT id, nombre FROM {table} ORDER BY nombre')
            rows = cur.fetchall()
            conn.close()
            # populate listbox
            try:
                listbox = getattr(self, f'listbox_{table}')
                listbox.delete(0, 'end')
                items_list = []
                for rid, nombre in rows:
                    listbox.insert('end', f"{nombre} ({rid})")
                    items_list.append(rid)
                setattr(self, f'_list_items_{table}', items_list)
            except Exception:
                print(f"[debug] could not populate listbox for {table}")
        except Exception as e:
            print(f"Error cargando {table}: {e}")

    def _crear_nuevo(self, table):
        self._limpiar_form(table)

    def _seleccionar(self, item_id, table):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(f'SELECT id, nombre, descripcion, created_at, updated_at FROM {table} WHERE id=? LIMIT 1', (item_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return
            rid, nombre, desc, created_at, updated_at = row
            lbl = getattr(self, f'lbl_id_{table}')
            lbl.configure(text=f'ID: {rid}')
            entry_nombre = getattr(self, f'entry_nombre_{table}')
            entry_desc = getattr(self, f'entry_desc_{table}')
            entry_shop = getattr(self, f'entry_shopify_taxonomy_{table}')
            entry_nombre.delete(0, 'end')
            entry_nombre.insert(0, nombre or '')
            entry_desc.delete('1.0', 'end')
            entry_desc.insert('1.0', desc or '')
            try:
                conn2 = connect()
                cur2 = conn2.cursor()
                cur2.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cur2.fetchall()]
                if 'shopify_taxonomy' in cols:
                    try:
                        cur2.execute(f'SELECT shopify_taxonomy FROM {table} WHERE id=?', (item_id,))
                        r = cur2.fetchone()
                        entry_shop.delete(0, 'end')
                        if r and r[0]:
                            entry_shop.insert(0, r[0])
                    except Exception:
                        pass
                conn2.close()
            except Exception:
                pass
            setattr(self, f'_selected_{table}', rid)
            # also select in listbox
            try:
                items = getattr(self, f'_list_items_{table}', [])
                if rid in items:
                    idx = items.index(rid)
                    lb = getattr(self, f'listbox_{table}', None)
                    if lb:
                        lb.selection_clear(0, 'end')
                        lb.selection_set(idx)
                        lb.see(idx)
            except Exception:
                pass
        except Exception as e:
            print(f"Error seleccionando {table} {item_id}: {e}")

    def _on_listbox_select(self, event, table):
        try:
            widget = event.widget
            sel = widget.curselection()
            if not sel:
                return
            idx = sel[0]
            items = getattr(self, f'_list_items_{table}', [])
            if idx < 0 or idx >= len(items):
                return
            item_id = items[idx]
            self._seleccionar(item_id, table)
        except Exception:
            pass

    def _guardar(self, table):
        nombre = getattr(self, f'entry_nombre_{table}').get().strip()
        desc = getattr(self, f'entry_desc_{table}').get('1.0', 'end').strip()
        entry_shop_widget = getattr(self, f'entry_shopify_taxonomy_{table}', None)
        try:
            shop_tax = entry_shop_widget.get().strip() if entry_shop_widget is not None else ''
        except Exception:
            shop_tax = ''
        if not nombre:
            messagebox.showerror('Faltan datos', 'El nombre es obligatorio')
            return
        now = datetime.now().isoformat(sep=' ', timespec='seconds')
        try:
            conn = connect()
            cur = conn.cursor()
            sel = getattr(self, f'_selected_{table}', None)
            performed_insert = False
            if sel:
                try:
                    cur.execute(f"PRAGMA table_info({table})")
                    cols = [c[1] for c in cur.fetchall()]
                    if 'shopify_taxonomy' in cols:
                        cur.execute(f'UPDATE {table} SET nombre=?, descripcion=?, shopify_taxonomy=?, updated_at=? WHERE id=?', (nombre, desc, shop_tax, now, sel))
                    else:
                        cur.execute(f'UPDATE {table} SET nombre=?, descripcion=?, updated_at=? WHERE id=?', (nombre, desc, now, sel))
                except Exception:
                    cur.execute(f'UPDATE {table} SET nombre=?, descripcion=?, updated_at=? WHERE id=?', (nombre, desc, now, sel))
            else:
                try:
                    cur.execute(f"PRAGMA table_info({table})")
                    cols = [c[1] for c in cur.fetchall()]
                    if 'shopify_taxonomy' in cols:
                        cur.execute(f'INSERT INTO {table} (nombre, descripcion, shopify_taxonomy, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', (nombre, desc, shop_tax, now, now))
                    else:
                        cur.execute(f'INSERT INTO {table} (nombre, descripcion, created_at, updated_at) VALUES (?, ?, ?, ?)', (nombre, desc, now, now))
                except Exception:
                    cur.execute(f'INSERT INTO {table} (nombre, descripcion, created_at, updated_at) VALUES (?, ?, ?, ?)', (nombre, desc, now, now))
                sel = cur.lastrowid
                performed_insert = True
            conn.commit()
            conn.close()
            messagebox.showinfo('Hecho', f'{table.capitalize()} guardado')
            self._cargar_lista(table)
            # If we inserted a new record, prepare the form for a new entry so
            # subsequent saves create additional records instead of overwriting
            # the one just created. If we updated, re-select the updated item.
            if performed_insert:
                self._limpiar_form(table)
            else:
                self._seleccionar(sel, table)
        except sqlite3.IntegrityError:
            messagebox.showerror('Error', 'Ya existe un registro con ese nombre')
        except Exception as e:
            print(f"Error guardando {table}: {e}")
            messagebox.showerror('Error', str(e))

    def _borrar_seleccionado(self, table):
        sel = getattr(self, f'_selected_{table}', None)
        if not sel:
            messagebox.showwarning('Nada seleccionado', 'Selecciona un elemento para borrar')
            return
        if not messagebox.askyesno('Confirmar', '¿Borrar el elemento seleccionado?'):
            return
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute(f'DELETE FROM {table} WHERE id=?', (sel,))
            conn.commit()
            conn.close()
            messagebox.showinfo('Borrado', 'Elemento borrado')
            setattr(self, f'_selected_{table}', None)
            getattr(self, f'lbl_id_{table}').configure(text='ID: -')
            self._limpiar_form(table)
            self._cargar_lista(table)
        except Exception as e:
            print(f"Error borrando {table}: {e}")
            messagebox.showerror('Error', str(e))

    def _limpiar_form(self, table):
        entry_nombre = getattr(self, f'entry_nombre_{table}')
        entry_desc = getattr(self, f'entry_desc_{table}')
        entry_nombre.delete(0, 'end')
        entry_desc.delete('1.0', 'end')
        getattr(self, f'lbl_id_{table}').configure(text='ID: -')
        try:
            setattr(self, f'_selected_{table}', None)
        except Exception:
            pass
        try:
            # put focus back into the name field so the user can type immediately
            entry_nombre.focus_set()
            try:
                entry_nombre.icursor('end')
            except Exception:
                pass
        except Exception:
            pass

    def _volver(self):
        # Try to return to the almacen submenu if available, otherwise fallback
        try:
            if hasattr(self.controller, 'mostrar_submenu_almacen'):
                try:
                    self.controller.mostrar_submenu_almacen()
                    return
                except Exception:
                    pass
            if hasattr(self.controller, 'mostrar_almacen_antiguo'):
                try:
                    self.controller.mostrar_almacen_antiguo()
                    return
                except Exception:
                    pass
        except Exception:
            pass
        # As a last resort, destroy this frame's parent content
        try:
            parent = self.master
            for w in parent.winfo_children():
                w.destroy()
        except Exception:
            pass
        
