from tkinter import ttk, messagebox
import tkinter as tk
import customtkinter as ctk
from database import connect
from typing import Optional
import re
from datetime import datetime


class GestionClientesView(ctk.CTkFrame):
    """Vista para listar, buscar y ver clientes.

    Diseño: dos columnas. Izquierda: buscador + lista. Derecha: ficha y acciones.
    """

    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_id: Optional[int] = None
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        # column proportions ~30% / 70%
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=7)
        self.pack(fill="both", expand=True)
        self._build_ui()
        self._load_tags()
        self._load_initial_clients()

    def _build_ui(self):
        # Header compacto (altura fija)
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, columnspan=2, sticky='ew')
        header_frame.grid_columnconfigure(0, weight=1)
        btn_back = ctk.CTkButton(header_frame, text='← Volver', width=120, command=self._on_volver)
        btn_back.grid(row=0, column=0, padx=12, pady=8, sticky='w')
        header = ctk.CTkLabel(header_frame, text="GESTIÓN DE CLIENTES", font=("Arial", 18, "bold"))
        header.grid(row=0, column=1, pady=8)

        # --- Columna izquierda: buscador + lista ---
        left = ctk.CTkFrame(self, fg_color='transparent')
        left.grid(row=1, column=0, sticky="nsew", padx=(12,6), pady=6)
        left.grid_rowconfigure(0, weight=0)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Buscador compacto en la parte superior de la lista
        search_frame = ctk.CTkFrame(left, fg_color='transparent')
        search_frame.grid(row=0, column=0, sticky='ew', pady=(6,10))
        search_frame.grid_columnconfigure(0, weight=1)
        self.entry_search = ctk.CTkEntry(search_frame, placeholder_text="Buscar por Nombre, DNI, Tlf...")
        self.entry_search.grid(row=0, column=0, sticky='ew', padx=(0,8))
        btn_search = ctk.CTkButton(search_frame, text="🔍", width=44, command=self._on_search)
        btn_search.grid(row=0, column=1)
        self.combo_tag = ctk.CTkComboBox(search_frame, values=["Todos"], width=140)
        self.combo_tag.set("Todos")
        self.combo_tag.grid(row=0, column=2, padx=(8,0))

        # Tabla de resultados (Treeview dentro de un frame scrollable)
        tree_frame = ctk.CTkFrame(left)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        # Treeview compacto: sólo Nombre y Teléfono
        cols = ("id", "nombre", "telefono")
        # style headings to left-align
        try:
            style = ttk.Style()
            style.configure("Treeview.Heading", anchor='w')
        except Exception:
            pass
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('nombre', text='Nombre', anchor='w')
        self.tree.heading('telefono', text='Tlf', anchor='w')
        # columnas: id (oculta estrecha), nombre flexible, telefono
        self.tree.column('id', width=1, stretch=False)
        self.tree.column('nombre', width=220)
        self.tree.column('telefono', width=120)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind('<<TreeviewSelect>>', self._on_select_item)

        # --- Columna derecha: detalle y acciones (fondo gris claro) ---
        right = ctk.CTkFrame(self, fg_color='#f0f0f0')
        right.grid(row=1, column=1, sticky="nsew", padx=(6,12), pady=6)
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=0)

        # Ficha cliente (panel derecho) -- se renderiza en modo lectura por defecto
        self.ficha = ctk.CTkFrame(right, fg_color='#f0f0f0')
        self.ficha.grid(row=0, column=0, sticky='nsew', pady=(0,12))
        self.ficha.grid_columnconfigure(0, weight=1)
        # Renderizado inicial en modo lectura
        self._render_ficha_lectura()

        # Botonera
        # Botonera principal al pie del detalle
        btns = ctk.CTkFrame(right, fg_color='#f0f0f0')
        btns.grid(row=1, column=0, sticky='ew', pady=8)
        btns.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(btns, text='➕ NUEVO CLIENTE', width=240, fg_color='#2ecc71', command=self._on_new).grid(row=0, column=0, padx=8, pady=6, sticky='ew')
        ctk.CTkButton(btns, text='✏️ EDITAR', width=240, fg_color='#3498db', command=self._on_edit).grid(row=0, column=1, padx=8, pady=6, sticky='ew')
        ctk.CTkButton(btns, text='🗑️ BORRAR', width=240, fg_color='#e74c3c', command=self._on_delete).grid(row=0, column=2, padx=8, pady=6, sticky='ew')
        self.btn_msg = ctk.CTkButton(btns, text='📧 ENVIAR MENSAJE', width=240, fg_color='#95a5a6', state='disabled', command=self._on_send_mail)
        self.btn_msg.grid(row=1, column=0, columnspan=3, padx=8, pady=6, sticky='ew')

    def _on_volver(self):
        """Volver a la pantalla anterior (inicio)."""
        try:
            if self.controller and hasattr(self.controller, 'mostrar_inicio'):
                self.controller.mostrar_inicio()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass

    # --- DB / Lógica ---
    def _db(self):
        return connect()

    def _load_tags(self):
        try:
            conn = self._db()
            cur = conn.cursor()
            cur.execute("SELECT tags FROM clientes WHERE tags IS NOT NULL AND tags <> ''")
            vals = cur.fetchall()
            tags = set()
            for (t,) in vals:
                for part in (t or '').split(','):
                    p = part.strip()
                    if p:
                        tags.add(p)
            values = ["Todos"] + sorted(tags)
            try:
                self.combo_tag.configure(values=values)
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _load_initial_clients(self):
        try:
            conn = self._db()
            cur = conn.cursor()
            cur.execute('''
                SELECT id, nombre, telefono, puntos_fidelidad FROM clientes
                ORDER BY nombre COLLATE NOCASE
                LIMIT 50
            ''')
            rows = cur.fetchall()
            self._populate_list(rows)
        except Exception:
            self._populate_list([])
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _populate_list(self, rows):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            # row: (id, nombre, telefono, puntos_fidelidad)
            id_, nombre, telefono, puntos = row
            # values must match columns order: (id, nombre, telefono)
            self.tree.insert('', 'end', iid=str(id_), values=(id_, nombre or '', telefono or ''))

    def _on_select_item(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        try:
            conn = self._db()
            cur = conn.cursor()
            cur.execute('''SELECT id, nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas_internas, puntos_fidelidad, puntos_activados, total_gastado, fecha_alta
                           FROM clientes WHERE id=?''', (item_id,))
            r = cur.fetchone()
            if not r:
                return
            (id_, nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas, puntos, puntos_activados, total, fecha_alta) = r
            self.selected_id = id_
            self.lbl_nombre.configure(text=nombre or '-')
            # Fecha alta formatting
            try:
                if fecha_alta:
                    dt = datetime.fromisoformat(fecha_alta)
                    fecha_fmt = dt.strftime('%d/%m/%Y')
                else:
                    fecha_fmt = '-'
            except Exception:
                fecha_fmt = '-'
            self.lbl_meta.configure(text=f'ID: {id_}   Alta: {fecha_fmt}')
            self.lbl_dni.configure(text=f'DNI: {dni or "-"}')
            self.lbl_email.configure(text=f'Email: {email or "-"}')
            self.lbl_contacto.configure(text=f'Tlf: {telefono or "-"}    ✉️ Email: {email or "-"}')
            addr = direccion or '-'
            if ciudad:
                addr = f"{addr} — {ciudad} {cp or ''}"
            self.lbl_direccion.configure(text=f'Dirección: {addr}')
            self.lbl_tags.configure(text=f'Tags: {tags or "-"}')
            self.lbl_notas.configure(text=f'Notas: {notas or "-"}')
            try:
                self.lbl_puntos.configure(text=str(int(puntos or 0)))
            except Exception:
                self.lbl_puntos.configure(text='0')
            # points switch reflect state
            try:
                if hasattr(self, 'lbl_switch'):
                    self.lbl_switch.set(int(puntos_activados if puntos_activados is not None else 1))
            except Exception:
                pass
            # enable send mail if email looks valid
            try:
                if email and re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    self.btn_msg.configure(state='normal')
                else:
                    self.btn_msg.configure(state='disabled')
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _on_search(self):
        q = (self.entry_search.get() or '').strip()
        tag = (self.combo_tag.get() or 'Todos')
        like = f"%{q}%"
        try:
            conn = self._db()
            cur = conn.cursor()
            if tag and tag != 'Todos':
                cur.execute('''SELECT id, nombre, telefono, puntos_fidelidad FROM clientes
                               WHERE (nombre LIKE ? OR dni LIKE ? OR telefono LIKE ?) AND tags LIKE ?
                               ORDER BY nombre COLLATE NOCASE LIMIT 200''', (like, like, like, f'%{tag}%'))
            else:
                cur.execute('''SELECT id, nombre, telefono, puntos_fidelidad FROM clientes
                               WHERE (nombre LIKE ? OR dni LIKE ? OR telefono LIKE ?)
                               ORDER BY nombre COLLATE NOCASE LIMIT 200''', (like, like, like))
            rows = cur.fetchall()
            self._populate_list(rows)
        except Exception as e:
            print('Error en búsqueda clientes:', e)
            self._populate_list([])
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _on_new(self):
        # Iniciar modo edición en blanco para crear nuevo cliente
        self.activar_edicion(es_nuevo=True)

    def _on_edit(self):
        if not self.selected_id:
            messagebox.showwarning('Editar', 'Selecciona un cliente primero.')
            return
        # Activar modo edición con datos del cliente seleccionado
        self.activar_edicion(es_nuevo=False)

    def _on_delete(self):
        if not self.selected_id:
            messagebox.showwarning('Borrar', 'Selecciona un cliente primero.')
            return
        try:
            ok = messagebox.askyesno('Borrar cliente', '¿Eliminar cliente seleccionado?')
            if not ok:
                return
        except Exception:
            return
        try:
            conn = self._db()
            cur = conn.cursor()
            cur.execute('DELETE FROM clientes WHERE id=?', (self.selected_id,))
            conn.commit()
            messagebox.showinfo('Borrado', 'Cliente eliminado.')
            self.selected_id = None
            # refresh
            self._load_initial_clients()
            # clear ficha
            self.lbl_nombre.configure(text='Nombre completo')
            self.lbl_dni.configure(text='DNI: -')
            self.lbl_email.configure(text='Email: -')
            self.lbl_direccion.configure(text='Dirección: -')
            self.lbl_tags.configure(text='Tags: -')
            self.lbl_notas.configure(text='Notas: -')
            self.lbl_puntos.configure(text='0')
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo eliminar cliente: {e}')
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # --- Modo Edición / Lectura ---
    def _render_ficha_lectura(self):
        # Limpia y dibuja la ficha en modo lectura
        try:
            for w in getattr(self, 'ficha', []).winfo_children():
                w.destroy()
        except Exception:
            pass
        ficha = self.ficha
        ficha.grid_columnconfigure(0, weight=1)
        ficha.grid_columnconfigure(1, weight=0)
        # Nombre grande a la izquierda
        self.lbl_nombre = ctk.CTkLabel(ficha, text='Nombre completo', font=("Arial", 26, "bold"), anchor='w')
        self.lbl_nombre.grid(row=0, column=0, sticky='w', pady=(6,12))
        # Fecha alta (derecha)
        self.lbl_meta = ctk.CTkLabel(ficha, text='ID: -   Alta: -', font=("Arial", 10), text_color='gray')
        self.lbl_meta.grid(row=0, column=1, sticky='ne', padx=(8,0))

        # Puntos fidelidad grande a la derecha, con botón y switch
        points_frame = ctk.CTkFrame(ficha, fg_color='#f0f0f0')
        points_frame.grid(row=1, column=1, sticky='ne', padx=(8,0))
        self.lbl_puntos = ctk.CTkLabel(points_frame, text='0', font=("Arial", 28, "bold"), text_color="#2ecc71")
        self.lbl_puntos.grid(row=0, column=0, sticky='e')
        # modificar button
        self.btn_modify_points = ctk.CTkButton(points_frame, text='⚙️ Modificar', width=90, height=28, command=self._modify_points_modal)
        self.btn_modify_points.grid(row=1, column=0, sticky='e', pady=(6,0))
        # switch (read-only appearance)
        try:
            self.lbl_switch = tk.IntVar(value=1)
            self.switch_read = ctk.CTkSwitch(points_frame, text='Puntos activados', variable=self.lbl_switch, onvalue=1, offvalue=0)
            self.switch_read.grid(row=2, column=0, sticky='e', pady=(6,0))
        except Exception:
            pass

        # Detalle lectura
        self.lbl_dni = ctk.CTkLabel(ficha, text='DNI: -', font=("Arial", 14))
        self.lbl_dni.grid(row=2, column=0, columnspan=2, sticky='w', pady=(8,2))
        self.lbl_contacto = ctk.CTkLabel(ficha, text='Tlf: -    ✉️ Email: -', font=("Arial", 14))
        self.lbl_contacto.grid(row=3, column=0, columnspan=2, sticky='w', pady=(2,2))
        self.lbl_direccion = ctk.CTkLabel(ficha, text='Dirección: -', wraplength=700, font=("Arial", 14))
        self.lbl_direccion.grid(row=4, column=0, columnspan=2, sticky='w', pady=(6,2))
        self.lbl_tags = ctk.CTkLabel(ficha, text='Tags: -', font=("Arial", 14))
        self.lbl_tags.grid(row=5, column=0, columnspan=2, sticky='w', pady=(4,2))
        self.lbl_notas = ctk.CTkLabel(ficha, text='Notas: -', wraplength=700, font=("Arial", 14))
        self.lbl_notas.grid(row=6, column=0, columnspan=2, sticky='w', pady=(6,6))

    def activar_edicion(self, es_nuevo=False):
        """Activa el modo edición: si es_nuevo=True, campos vacíos; si False, rellenar con cliente seleccionado."""
        # limpiar ficha
        try:
            for w in self.ficha.winfo_children():
                w.destroy()
        except Exception:
            pass
        # Scrollable frame para formulario
        form = ctk.CTkScrollableFrame(self.ficha, fg_color='transparent')
        form.pack(fill='both', expand=True)
        # Campos editables arranged in grid for cleaner layout
        self.form_inner = ctk.CTkFrame(form, fg_color='transparent')
        self.form_inner.pack(fill='both', expand=True, padx=8, pady=8)
        self.form_inner.grid_columnconfigure(0, weight=3)
        self.form_inner.grid_columnconfigure(1, weight=1)
        self.form_inner.grid_columnconfigure(2, weight=1)

        self.entry_nombre = ctk.CTkEntry(self.form_inner, placeholder_text='Nombre completo')
        self.entry_nombre.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(8,4))

        self.entry_dni = ctk.CTkEntry(self.form_inner, placeholder_text='DNI')
        self.entry_dni.grid(row=1, column=0, sticky='ew', padx=(0,6), pady=4)
        self.entry_telefono = ctk.CTkEntry(self.form_inner, placeholder_text='Teléfono')
        self.entry_telefono.grid(row=1, column=1, sticky='ew', padx=(0,6), pady=4)
        self.entry_email = ctk.CTkEntry(self.form_inner, placeholder_text='Email')
        self.entry_email.grid(row=1, column=2, sticky='ew', pady=4)

        self.entry_direccion = ctk.CTkEntry(self.form_inner, placeholder_text='Dirección')
        self.entry_direccion.grid(row=2, column=0, columnspan=1, sticky='ew', pady=4)
        self.entry_ciudad = ctk.CTkEntry(self.form_inner, placeholder_text='Ciudad')
        self.entry_ciudad.grid(row=2, column=1, sticky='ew', padx=(6,6), pady=4)
        self.entry_cp = ctk.CTkEntry(self.form_inner, placeholder_text='CP')
        self.entry_cp.grid(row=2, column=2, sticky='ew', pady=4)

        self.entry_tags = ctk.CTkEntry(self.form_inner, placeholder_text='Tags (separadas por comas)')
        self.entry_tags.grid(row=3, column=0, columnspan=3, sticky='ew', pady=4)

        # Notas: multiline text widget
        lbl_notas = ctk.CTkLabel(self.form_inner, text='Notas internas')
        lbl_notas.grid(row=4, column=0, columnspan=3, sticky='w', pady=(8,2))
        self.text_notas = tk.Text(self.form_inner, height=6)
        self.text_notas.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(0,8))

        # Puntos y switch
        points_sub = ctk.CTkFrame(self.form_inner, fg_color='transparent')
        points_sub.grid(row=6, column=0, columnspan=3, sticky='w', pady=(4,8))
        self.entry_puntos = ctk.CTkEntry(points_sub, width=100, placeholder_text='Puntos')
        self.entry_puntos.grid(row=0, column=0, padx=(0,8))
        self.btn_modify_points = ctk.CTkButton(points_sub, text='⚙️ Modificar', width=110, height=28, command=self._modify_points_modal)
        self.btn_modify_points.grid(row=0, column=1, padx=(0,8))
        try:
            self.var_puntos_activados = tk.IntVar(value=1)
            self.switch_puntos = ctk.CTkSwitch(points_sub, text='Puntos activados', variable=self.var_puntos_activados, onvalue=1, offvalue=0)
            self.switch_puntos.grid(row=0, column=2)
        except Exception:
            self.var_puntos_activados = tk.IntVar(value=1)

        # Switch: puntos_activados (UI tolerante si la columna no existe)
        try:
            self.var_puntos_activados = tk.IntVar(value=1)
            self.switch_puntos = ctk.CTkSwitch(form, text='Puntos activados', variable=self.var_puntos_activados, onvalue=1, offvalue=0)
            self.switch_puntos.pack(anchor='w', padx=8, pady=(4,8))
        except Exception:
            self.var_puntos_activados = tk.IntVar(value=1)

        # Botonera guardar / cancelar
        btn_frame = ctk.CTkFrame(form, fg_color='transparent')
        btn_frame.pack(fill='x', padx=8, pady=8)
        self.btn_guardar = ctk.CTkButton(btn_frame, text='Guardar', fg_color='#2ecc71', command=lambda: self.guardar_cambios(es_nuevo))
        self.btn_guardar.pack(side='left', padx=6)
        ctk.CTkButton(btn_frame, text='Cancelar', fg_color='#e74c3c', command=self.cancelar_edicion).pack(side='left', padx=6)

        # Si no es nuevo, cargar datos actuales
        if not es_nuevo and self.selected_id:
            try:
                conn = self._db()
                cur = conn.cursor()
                # detect if puntos_activados column exists
                cur.execute("PRAGMA table_info(clientes)")
                cols = [c[1] for c in cur.fetchall()]
                # select extended fields if present
                sel_cols = ['nombre','dni','email','telefono','direccion','ciudad','cp','tags','notas_internas','puntos_fidelidad']
                if 'puntos_activados' in cols:
                    sel_cols.append('puntos_activados')
                if 'fecha_alta' in cols:
                    sel_cols.append('fecha_alta')
                q = 'SELECT ' + ','.join(sel_cols) + ' FROM clientes WHERE id=?'
                cur.execute(q, (self.selected_id,))
                r = cur.fetchone()
                if r:
                    # map returned values safely
                    data = dict(zip(sel_cols, r))
                    nombre = data.get('nombre')
                    dni = data.get('dni')
                    email = data.get('email')
                    telefono = data.get('telefono')
                    direccion = data.get('direccion')
                    ciudad = data.get('ciudad')
                    cp = data.get('cp')
                    tags = data.get('tags')
                    notas = data.get('notas_internas')
                    puntos_act = data.get('puntos_activados') if 'puntos_activados' in data else None
                    puntos_fid = data.get('puntos_fidelidad')
                    try:
                        self.entry_nombre.insert(0, nombre or '')
                        self.entry_dni.insert(0, dni or '')
                        self.entry_email.insert(0, email or '')
                        self.entry_telefono.insert(0, telefono or '')
                        self.entry_direccion.insert(0, direccion or '')
                        try:
                            self.entry_ciudad.insert(0, ciudad or '')
                        except Exception:
                            pass
                        try:
                            self.entry_cp.insert(0, cp or '')
                        except Exception:
                            pass
                        self.entry_tags.insert(0, tags or '')
                        try:
                            self.text_notas.delete('1.0', tk.END)
                            self.text_notas.insert('1.0', notas or '')
                        except Exception:
                            pass
                        try:
                            if puntos_fid is not None:
                                self.entry_puntos.delete(0, tk.END)
                                self.entry_puntos.insert(0, str(int(puntos_fid or 0)))
                        except Exception:
                            pass
                        try:
                            if puntos_act is not None:
                                self.var_puntos_activados.set(int(puntos_act or 1))
                        except Exception:
                            pass
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

    def cancelar_edicion(self):
        # Restaurar vista en modo lectura para el cliente actual
        self._render_ficha_lectura()
        if self.selected_id:
            # rellenar labels con datos actuales
            try:
                self._on_select_item()
            except Exception:
                pass

    def _on_send_mail(self):
        # Simple modal placeholder
        try:
            if not self.selected_id:
                messagebox.showinfo('Enviar', 'Selecciona un cliente.')
                return
            # fetch email
            conn = self._db()
            cur = conn.cursor()
            cur.execute('SELECT email FROM clientes WHERE id=?', (self.selected_id,))
            r = cur.fetchone()
            email = (r[0] if r else None)
            if not email:
                messagebox.showwarning('Enviar', 'El cliente no tiene email.')
                return
            messagebox.showinfo('Enviar mail', f'Abrir diálogo para enviar email a: {email}\n(Envío no implementado)')
        except Exception:
            pass
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _modify_points_modal(self):
        # small modal to adjust puntos_fidelidad
        dlg = tk.Toplevel(self)
        dlg.title('Modificar puntos')
        dlg.geometry('300x120')
        tk.Label(dlg, text='Nuevos puntos:').pack(pady=(12,6))
        ent = tk.Entry(dlg)
        ent.pack()
        def _ok():
            try:
                val = int(ent.get())
            except Exception:
                messagebox.showerror('Error', 'Introduce un número válido')
                return
            # set in form or in label depending mode
            try:
                if hasattr(self, 'entry_puntos'):
                    self.entry_puntos.delete(0, tk.END)
                    self.entry_puntos.insert(0, str(val))
                if hasattr(self, 'lbl_puntos'):
                    self.lbl_puntos.configure(text=str(val))
            except Exception:
                pass
            try:
                dlg.destroy()
            except Exception:
                pass
        tk.Button(dlg, text='OK', command=_ok).pack(pady=8)
        try:
            dlg.grab_set()
        except Exception:
            pass

    def guardar_cambios(self, es_nuevo=False):
        # Recoger valores
        nombre = (getattr(self, 'entry_nombre', None).get() or '').strip()
        if not nombre:
            messagebox.showwarning('Validación', 'El nombre es obligatorio.')
            return
        dni = (getattr(self, 'entry_dni', None).get() or '').strip()
        email = (getattr(self, 'entry_email', None).get() or '').strip()
        telefono = (getattr(self, 'entry_telefono', None).get() or '').strip()
        direccion = (getattr(self, 'entry_direccion', None).get() or '').strip()
        tags = (getattr(self, 'entry_tags', None).get() or '').strip()
        # notas from Text if available
        try:
            notas = self.text_notas.get('1.0', tk.END).strip()
        except Exception:
            notas = (getattr(self, 'entry_notas', None).get() or '').strip()
        ciudad = (getattr(self, 'entry_ciudad', None).get() or '').strip()
        cp = (getattr(self, 'entry_cp', None).get() or '').strip()
        puntos_fid = 0
        try:
            puntos_fid = int((getattr(self, 'entry_puntos', None).get() or '0'))
        except Exception:
            puntos_fid = 0

        try:
            conn = self._db()
            cur = conn.cursor()
            # detect if puntos_activados column exists
            cur.execute("PRAGMA table_info(clientes)")
            cols = [r[1] for r in cur.fetchall()]
            has_puntos = 'puntos_activados' in cols
            puntos_val = 1
            try:
                puntos_val = int(getattr(self, 'var_puntos_activados', tk.IntVar(value=1)).get())
            except Exception:
                puntos_val = 1
            if es_nuevo:
                fecha_alta = datetime.now().isoformat()
                if has_puntos:
                    cur.execute('''INSERT INTO clientes (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas_internas, puntos_activados, puntos_fidelidad, total_gastado, fecha_alta)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)''', (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas, puntos_val, puntos_fid, fecha_alta))
                else:
                    cur.execute('''INSERT INTO clientes (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas_internas, puntos_fidelidad, total_gastado, fecha_alta)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)''', (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas, puntos_fid, fecha_alta))
                conn.commit()
                new_id = cur.lastrowid
                self.selected_id = new_id
            else:
                if has_puntos:
                    cur.execute('''UPDATE clientes SET nombre=?, dni=?, email=?, telefono=?, direccion=?, ciudad=?, cp=?, tags=?, notas_internas=?, puntos_activados=?, puntos_fidelidad=? WHERE id=?''',
                                (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas, puntos_val, puntos_fid, self.selected_id))
                else:
                    cur.execute('''UPDATE clientes SET nombre=?, dni=?, email=?, telefono=?, direccion=?, ciudad=?, cp=?, tags=?, notas_internas=?, puntos_fidelidad=? WHERE id=?''',
                                (nombre, dni, email, telefono, direccion, ciudad, cp, tags, notas, puntos_fid, self.selected_id))
                conn.commit()
        except Exception as e:
            messagebox.showerror('Error', f'No se pudo guardar: {e}')
            return
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # Refrescar lista y volver a modo lectura
        try:
            self._load_initial_clients()
            self._render_ficha_lectura()
            if self.selected_id:
                self._on_select_item()
        except Exception:
            pass
