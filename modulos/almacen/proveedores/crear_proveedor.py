import sqlite3
import customtkinter as ctk
from database import connect

class CrearProveedorForm:
    def __init__(self, parent, controller, proveedores_page=None, proveedor_id=None):
        self.parent = parent
        self.controller = controller
        self.proveedores_page = proveedores_page
        self.proveedor_id = proveedor_id
        self.entries = {}

    def render(self):
        for w in self.parent.winfo_children():
            w.destroy()

        fields = [
            ('nombre', 'Nombre'),
            ('que_vende', 'Qué nos vende?'),
            ('nif_cif', 'NIF/CIF'),
            ('iva_intracom', 'Iva Intracomunitario'),
            ('dir_fiscal', 'Dirección Fiscal'),
            ('dir_envio', 'Dirección Envío'),
            ('email', 'E-mail'),
            ('telefono', 'Teléfono'),
            ('forma_pago', 'Forma de pago'),
            ('persona_comercial', 'Persona comercial'),
            ('telefono_comercial', 'Teléfono del comercial'),
            ('email_comercial', 'E-mail comercial'),
            ('web', 'Web'),
        ]

        frm = ctk.CTkFrame(self.parent, fg_color="#151515")
        frm.pack(fill="both", expand=True, padx=6, pady=6)

        # If editing, show the internal ID at the top-right
        if self.proveedor_id:
            try:
                lbl_id = ctk.CTkLabel(frm, text=f"ID: {self.proveedor_id}", text_color="gray")
                lbl_id.grid(row=0, column=3, sticky='e', padx=6, pady=6)
            except Exception:
                pass

        # Layout: two input columns per row (label+entry, label+entry)
        large_w = 400
        small_w = large_w // 2
        peque_keys = set(['nombre', 'nif_cif', 'iva_intracom', 'email', 'telefono', 'telefono_comercial', 'email_comercial'])

        cols_total = 4
        # configure grid columns
        for c in range(cols_total):
            frm.grid_columnconfigure(c, weight=1)

        for idx, (key, label) in enumerate(fields):
            row = idx // 2
            pos = idx % 2
            lbl_col = pos * 2
            ent_col = lbl_col + 1
            lbl = ctk.CTkLabel(frm, text=label, text_color="gray")
            lbl.grid(row=row, column=lbl_col, sticky="w", padx=6, pady=4)
            w = small_w if key in peque_keys else large_w
            ent = ctk.CTkEntry(frm, width=w)
            ent.grid(row=row, column=ent_col, sticky="w", padx=6, pady=4)
            self.entries[key] = ent

        # Notas (multi-line)
        notes_row = (len(fields) - 1) // 2 + 1
        lbl_notas = ctk.CTkLabel(frm, text='Notas', text_color='gray')
        lbl_notas.grid(row=notes_row, column=0, sticky='nw', padx=6, pady=4)
        self.txt_notas = ctk.CTkTextbox(frm, width=large_w*1 + 100, height=120)
        self.txt_notas.grid(row=notes_row, column=1, columnspan=3, sticky='w', padx=6, pady=4)

        # Web button (placed under the notes area)
        def _abrir_web():
            url = self.entries.get('web').get().strip() if self.entries.get('web') else ''
            import webbrowser
            if url:
                if not url.startswith('http'):
                    url = 'http://' + url
                webbrowser.open(url)
        btn_web = ctk.CTkButton(frm, text='Ir a la web', command=_abrir_web)
        btn_web.grid(row=notes_row+1, column=0, sticky='w', padx=6, pady=6)

        # Guardar Datos button (aligned in a row under the form)
        btn_guardar = ctk.CTkButton(frm, text='Guardar Datos', fg_color='#228B22', command=self._guardar)
        btn_guardar.grid(row=notes_row+2, column=0, columnspan=4, sticky='e', padx=6, pady=10)

        # If editing existing proveedor, cargar datos
        if self.proveedor_id:
            self._cargar_proveedor()

    def _ensure_table(self, cursor):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                que_vende TEXT,
                nif_cif TEXT,
                iva_intracom TEXT,
                dir_fiscal TEXT,
                dir_envio TEXT,
                email TEXT,
                telefono TEXT,
                forma_pago TEXT,
                persona_comercial TEXT,
                telefono_comercial TEXT,
                email_comercial TEXT,
                web TEXT,
                notas TEXT
            )
        ''')

    def _guardar(self):
        data = {k: (v.get().strip() if isinstance(v, ctk.CTkEntry) else '') for k, v in self.entries.items()}
        data['notas'] = self.txt_notas.get('1.0', 'end').strip()
        # Validación: el nombre es obligatorio
        if not data.get('nombre'):
            # Mostrar mensaje de error y enfocar campo (usamos grid)
            try:
                if not hasattr(self, '_err_lbl'):
                    self._err_lbl = ctk.CTkLabel(self.parent, text='El nombre es obligatorio', text_color='#ff3333')
                    # place at top of parent area
                    try:
                        self._err_lbl.pack(pady=6)
                    except Exception:
                        pass
                else:
                    self._err_lbl.configure(text='El nombre es obligatorio')
                self.entries['nombre'].focus()
            except Exception:
                pass
            return
        try:
            conn = connect()
            cur = conn.cursor()
            self._ensure_table(cur)
            if self.proveedor_id:
                # update
                cols = ', '.join([f"{k} = ?" for k in data.keys()])
                vals = list(data.values())
                vals.append(self.proveedor_id)
                sql = f"UPDATE proveedores SET {cols} WHERE id = ?"
                cur.execute(sql, vals)
            else:
                cols = ', '.join(data.keys())
                placeholders = ','.join(['?'] * len(data))
                sql = f"INSERT INTO proveedores ({cols}) VALUES ({placeholders})"
                cur.execute(sql, list(data.values()))
            conn.commit()
            conn.close()
            # Refresh proveedores list if parent provided
            try:
                if self.proveedores_page:
                    self.proveedores_page._cargar_lista_proveedores()
            except Exception:
                pass
            # Show confirmation
            for w in self.parent.winfo_children():
                if isinstance(w, ctk.CTkLabel) and w.cget('text').startswith('Guardado'):
                    w.destroy()
            lbl = ctk.CTkLabel(self.parent, text='Guardado correctamente', text_color='white')
            lbl.pack(pady=6)
        except Exception as e:
            print('Error guardando proveedor:', e)

    def _cargar_proveedor(self):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute('SELECT * FROM proveedores WHERE id = ? LIMIT 1', (self.proveedor_id,))
            row = cur.fetchone()
            if not row:
                return
            cur.execute('PRAGMA table_info(proveedores)')
            cols = [c[1] for c in cur.fetchall()]
            mapping = {}
            for i, col in enumerate(cols):
                mapping[col] = row[i] if i < len(row) else ''
            # Fill entries
            for k, ent in self.entries.items():
                ent.delete(0, 'end')
                ent.insert(0, mapping.get(k, ''))
            self.txt_notas.delete('1.0', 'end')
            self.txt_notas.insert('1.0', mapping.get('notas', ''))
            conn.close()
        except Exception as e:
            print('Error cargando proveedor:', e)
