import customtkinter as ctk
import sqlite3
from database import connect
import sys
from datetime import datetime
from .ui_selector_sin_codigo import SelectorSinCodigo
from tkinter import messagebox, simpledialog
try:
    from modulos.tpv.preview_imprimir import preview_ticket
except Exception:
    preview_ticket = None

class CajaVentas(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True)
        
        # --- CARRITO ---
        self.carrito = [] 
        self._awaiting_final_confirmation = False

        # --- ESTRUCTURA ---
        self.grid_rowconfigure(0, weight=0) 
        self.grid_rowconfigure(1, weight=1) 
        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 

        # --- BARRA SUPERIOR ---
        self.top_bar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#333333")
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        self.lbl_reloj = ctk.CTkLabel(self.top_bar, text="00:00:00", font=("Arial", 18, "bold"))
        self.lbl_reloj.pack(side="left", padx=20)
        self.actualizar_reloj()

        self.lbl_cajero = ctk.CTkLabel(self.top_bar, text="👤 Cajero: EGON (Admin)", font=("Arial", 14))
        self.lbl_cajero.pack(side="right", padx=20)

        self.btn_salir = ctk.CTkButton(self.top_bar, text="❌ Salir", width=60, fg_color="red", 
                                       command=self.controller.mostrar_inicio)
        self.btn_salir.pack(side="right", padx=10)

        # --- ZONA IZQUIERDA ---
        self.frame_visor = ctk.CTkFrame(self)
        self.frame_visor.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.lista_productos = ctk.CTkTextbox(self.frame_visor, font=("Courier", 20))
        self.lista_productos.pack(fill="both", expand=True, padx=5, pady=5)
        self.lista_productos.configure(state="disabled")
        # Habilitar selección por línea y borrar con tecla Supr/Del
        try:
            # tag para línea seleccionada
            self.lista_productos._textbox.tag_configure('selected', foreground='#00A4CC')
            # bind click en el texto para seleccionar la línea
            self.lista_productos._textbox.bind('<Button-1>', self._on_text_click)
            # bind tecla Supr/Delete para eliminar item seleccionado
            self.lista_productos._textbox.bind('<Delete>', self._on_delete_key)
        except Exception:
            pass

        self.frame_totales = ctk.CTkFrame(self.frame_visor, height=100, fg_color="black")
        self.frame_totales.pack(fill="x", side="bottom")

        self.lbl_total = ctk.CTkLabel(self.frame_totales, text="TOTAL: 0.00 €", font=("Arial", 48, "bold"), text_color="#00FF00")
        self.lbl_total.pack(pady=10)
        
        self.lbl_iva = ctk.CTkLabel(self.frame_totales, text="Base: 0.00€ | IVA: 0.00€", font=("Arial", 14), text_color="white")
        self.lbl_iva.pack()

        # Elementos para entrada de efectivo (inicialmente ocultos)
        self.lbl_efectivo = ctk.CTkLabel(self.frame_totales, text="Introducir efectivo entregado:", font=("Arial", 14), text_color="red")
        # variable para controlar el entry de efectivo y buffer de teclas
        self.efectivo_var = ctk.StringVar(value="")
        self._cash_buffer = ""
        self.entry_efectivo = ctk.CTkEntry(self.frame_totales, font=("Arial", 14), textvariable=self.efectivo_var)
        self.entry_efectivo.bind("<Return>", self.procesar_efectivo)

        # Captura teclas numéricas globales para rellenar el efectivo cuando la pantalla está activa
        try:
            self.controller.bind_all("<Key>", self._on_global_key)
            # asegurarse de limpiar el binding al destruir la pantalla
            self.bind("<Destroy>", lambda e: self.controller.unbind_all("<Key>"))
        except Exception:
            pass

        # --- ZONA DERECHA ---
        self.frame_botones = ctk.CTkFrame(self)
        self.frame_botones.grid(row=1, column=1, sticky="nsew", padx=(0,10), pady=10)
        self.frame_botones.grid_columnconfigure((0,1), weight=1) 

        # Caja de Búsqueda
        frame_busqueda = ctk.CTkFrame(self.frame_botones, fg_color="transparent")
        frame_busqueda.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.entry_codigo = ctk.CTkEntry(frame_busqueda, placeholder_text="SKU / EAN", height=50, font=("Arial", 16))
        self.entry_codigo.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_codigo.bind("<Return>", self.buscar_producto)
        self.entry_codigo.focus()

        self.btn_buscar = ctk.CTkButton(frame_busqueda, text="🔍", width=50, height=50, command=self.buscar_producto_evento)
        self.btn_buscar.pack(side="right")

        # Botones Varios - reorganizados
        # Parte superior: cuadro de búsqueda ya en row=0
        # Botón SIN CÓDIGO en su propia línea (debajo de la búsqueda)
        ctk.CTkButton(self.frame_botones, text="SIN CÓDIGO", width=140, height=50, fg_color="#FF6B35", command=self.abrir_selector_sin_codigo).grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(5,10))

        # Zona central: espacio para los botones dinámicos del selector (ocupable)
        self.selector_area = ctk.CTkScrollableFrame(self.frame_botones)
        self.selector_area.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.frame_botones.grid_rowconfigure(2, weight=1)

        # Parte inferior (de arriba a abajo):
        # 6- CLIENTE y CAJERO (misma línea)
        ctk.CTkButton(self.frame_botones, text="👤 CLIENTE", height=40).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="🆔 CAJERO", height=40).grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # 5- TICKETS y SELECTOR IMPRIMIR TICKET (misma línea)
        # Tickets button: open tickets view
        try:
            self.btn_tickets = ctk.CTkButton(self.frame_botones, text="📄 TICKETS", height=40, command=lambda: self.controller.mostrar_tickets())
            self.btn_tickets.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        except Exception:
            ctk.CTkButton(self.frame_botones, text="📄 TICKETS", height=40).grid(row=4, column=0, sticky="ew", padx=5, pady=5)

        # Toggle automatic printing of ticket: visual indicator changes text
        try:
            def _toggle_impr():
                try:
                    # toggle printing flag (default is ON in controller)
                    self.controller.toggle_imprimir_tickets()
                    self._update_impr_button()
                except Exception:
                    pass
                # Show list of tickets included in this cierre so user can verify
                try:
                    conn = connect()
                    cur = conn.cursor()
                    tickets_rows = []
                    if resumen.get('cierre_id'):
                        cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE cierre_id=? ORDER BY created_at ASC', (resumen.get('cierre_id'),))
                        tickets_rows = cur.fetchall()
                    else:
                        cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE date(created_at)=? ORDER BY created_at ASC', (fecha,))
                        tickets_rows = cur.fetchall()
                    try:
                        cur.close()
                    except Exception:
                        pass
                    try:
                        conn.close()
                    except Exception:
                        pass

                    # build modal with Treeview
                    t = ctk.CTkToplevel(self)
                    t.title('Tickets incluidos')
                    t.geometry('600x360')
                    t.transient(self)
                    from tkinter import ttk as _ttk
                    frame = ctk.CTkFrame(t)
                    frame.pack(fill='both', expand=True, padx=8, pady=8)
                    tree = _ttk.Treeview(frame, columns=('no','hora','cajero','total'), show='headings')
                    tree.heading('no', text='Nº')
                    tree.heading('hora', text='Hora')
                    tree.heading('cajero', text='Cajero')
                    tree.heading('total', text='Total')
                    tree.column('no', width=80)
                    tree.column('hora', width=120)
                    tree.column('cajero', width=160)
                    tree.column('total', width=120, anchor='e')
                    tree.pack(fill='both', expand=True, side='left')
                    sb = _ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
                    tree.configure(yscroll=sb.set)
                    sb.pack(side='right', fill='y')
                    for r in tickets_rows:
                        tid, created_at, ticket_no, cajero_t, tot = r
                        hora = ''
                        try:
                            hora = datetime.fromisoformat(created_at).strftime('%H:%M:%S')
                        except Exception:
                            hora = created_at
                        tree.insert('', 'end', iid=str(tid), values=(ticket_no or '', hora, cajero_t or '', f"{(tot or 0):.2f}"))
                    # allow double-click to open ticket detail in main Tickets view
                    def _on_double(e):
                        sel = tree.selection()
                        if not sel:
                            return
                        tid = sel[0]
                        try:
                            t.destroy()
                        except Exception:
                            pass
                        try:
                            # show tickets view focused on the ticket's day and select it
                            self.controller.mostrar_tickets()
                            # rely on the TicketsView to allow user to open details
                        except Exception:
                            pass
                    tree.bind('<Double-1>', _on_double)
                except Exception:
                    pass

            self.btn_impr = ctk.CTkButton(self.frame_botones, text="🖨️ IMPR. TICKET", height=40, command=_toggle_impr)
            self.btn_impr.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
            # set initial visual state
            self._update_impr_button()
        except Exception:
            ctk.CTkButton(self.frame_botones, text="🖨️ IMPR. TICKET", height=40).grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        # 4- DESCUENTO y DEVOLUCIÓN (misma línea)
        ctk.CTkButton(self.frame_botones, text="✂️ DESCUENTO", height=40, fg_color="#E59400").grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="↩️ DEVOLUCIÓN", height=40, fg_color="#FF4500").grid(row=5, column=1, sticky="ew", padx=5, pady=5)

        # 3- TARJETA y WEB (misma línea)
        ctk.CTkButton(self.frame_botones, text="💳 TARJETA", height=60, fg_color="#1E90FF").grid(row=6, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkButton(self.frame_botones, text="🌐 WEB", height=60, fg_color="#00A4CC").grid(row=6, column=1, sticky="ew", padx=5, pady=5)

        # 2- EFECTIVO (línea completa)
        ctk.CTkButton(self.frame_botones, text="💶 EFECTIVO", height=80, fg_color="#228B22", font=("Arial", 20, "bold"), command=self.abrir_cobro_efectivo).grid(row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        # 1- CERRAR DÍA  y CAJÓN (misma línea, al fondo)
        ctk.CTkButton(self.frame_botones, text="🔒 CERRAR DÍA", height=30, fg_color="darkred", command=lambda: self.controller.mostrar_cierre_caja()).grid(row=8, column=0, sticky="ew", padx=5, pady=(20,5))
        ctk.CTkButton(self.frame_botones, text="🔓 CAJÓN", height=30, fg_color="#555555").grid(row=8, column=1, sticky="ew", padx=5, pady=(20,5))

    def actualizar_reloj(self):
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_reloj.configure(text=ahora)
        self.after(1000, self.actualizar_reloj)

    def _compute_day_summary(self, fecha_str: str):
        """Return lightweight summary for `fecha_str` (YYYY-MM-DD)."""
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT MIN(ticket_no), MAX(ticket_no), COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE date(created_at)=?", (fecha_str,))
            min_no, max_no, count_tickets, sum_total = cur.fetchone()
            cur.execute("SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE date(created_at)=? GROUP BY forma_pago", (fecha_str,))
            pagos = cur.fetchall()
            return {
                'fecha': fecha_str,
                'from': min_no,
                'to': max_no,
                'count': count_tickets,
                'total': float(sum_total or 0.0),
                'pagos': pagos
            }
        except Exception:
            return None
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def cerrar_dia_dialog(self):
        """Show modal to confirm day closure and perform close_day on confirm."""
        fecha = datetime.now().date().isoformat()
        summary = self._compute_day_summary(fecha)

        win = ctk.CTkToplevel(self)
        win.title(f"Cerrar día {fecha}")
        win.geometry('480x320')
        win.transient(self)

        # Summary labels
        lbl = ctk.CTkLabel(win, text=f"Resumen día {fecha}", font=(None, 16, 'bold'))
        lbl.pack(pady=(12,6))
        if summary:
            txt = f"Tickets: {summary['count']}  Total: {summary['total']:.2f}€\nRango: {summary['from'] or ''} - {summary['to'] or ''}\n"
            for forma, cnt, tot in summary['pagos']:
                txt += f"{forma or 'OTROS'}: {cnt}  {tot:.2f}€\n"
        else:
            txt = "No hay datos para este día."
        lbl2 = ctk.CTkLabel(win, text=txt, anchor='w', justify='left')
        lbl2.pack(fill='both', padx=12)

        # Options
        var_tipo = ctk.StringVar(value='Z')
        frame_tipo = ctk.CTkFrame(win)
        frame_tipo.pack(anchor='w', padx=12, pady=(8,0))
        ctk.CTkLabel(frame_tipo, text='Tipo:').pack(side='left', padx=(0,8))
        ctk.CTkRadioButton(frame_tipo, text='Z - Cierre definitivo (marca tickets)', variable=var_tipo, value='Z').pack(side='left', padx=4)
        ctk.CTkRadioButton(frame_tipo, text='X - Cierre informativo (no marca)', variable=var_tipo, value='X').pack(side='left', padx=4)

        var_cat = ctk.BooleanVar(value=False)
        var_prod = ctk.BooleanVar(value=False)
        var_print = ctk.BooleanVar(value=False)
        cb1 = ctk.CTkCheckBox(win, text="Incluir desglose por categoría", variable=var_cat)
        cb1.pack(anchor='w', padx=12, pady=(8,0))
        cb2 = ctk.CTkCheckBox(win, text="Incluir top productos", variable=var_prod)
        cb2.pack(anchor='w', padx=12)
        cb3 = ctk.CTkCheckBox(win, text="Imprimir cierre (en impresora)", variable=var_print)
        cb3.pack(anchor='w', padx=12, pady=(0,8))

        btns = ctk.CTkFrame(win)
        btns.pack(side='bottom', fill='x', pady=12)

        def _on_confirm():
            try:
                from database import close_day
                tipo = var_tipo.get()
                resumen = close_day(fecha, tipo=tipo, include_category=var_cat.get(), include_products=var_prod.get(), cajero=None, notas=None)
                # Build closure text (include numero and tipo)
                lines = []
                lines.append("CIERRE DE CAJA\n")
                lines.append(f"Tipo: {resumen.get('numero','') or ''} - {tipo}\n")
                lines.append(f"Día: {fecha}\n")
                lines.append(f"Tickets: {resumen.get('count_tickets',0)}  TOTAL: {resumen.get('total',0):.2f}€\n")
                for p in resumen.get('por_forma_pago', []):
                    lines.append(f"{p.get('forma','OTROS')}: {p.get('total',0):.2f}€\n")
                if resumen.get('por_categoria'):
                    lines.append('\nDesglose por categoría:\n')
                    for c in resumen.get('por_categoria'):
                        lines.append(f"{c.get('categoria')}: {c.get('qty')}  {c.get('total'):.2f}€\n")
                if resumen.get('top_products'):
                    lines.append('\nTop productos:\n')
                    for tprod in resumen.get('top_products'):
                        lines.append(f"{tprod.get('nombre')}: {tprod.get('qty')}  {tprod.get('total'):.2f}€\n")
                text = ''.join(lines)

                # Inform user immediately about created cierre (so they see something even if preview fails)
                try:
                    from tkinter import messagebox as _mb
                    _mb.showinfo('Cierre creado', f"Tipo: {tipo}  Número: {resumen.get('numero','')}\nTickets: {resumen.get('count_tickets',0)}\nTotal: {resumen.get('total',0):.2f}€")
                except Exception:
                    pass

                # Always show a local preview modal for Z closures or when printing requested.
                try:
                    # collect ticket rows to display in the preview
                    conn = connect()
                    cur = conn.cursor()
                    tickets_rows = []
                    if resumen.get('cierre_id'):
                        cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE cierre_id=? ORDER BY created_at ASC', (resumen.get('cierre_id'),))
                        tickets_rows = cur.fetchall()
                    else:
                        cur.execute('SELECT id, created_at, ticket_no, cajero, total FROM tickets WHERE date(created_at)=? ORDER BY created_at ASC', (fecha,))
                        tickets_rows = cur.fetchall()
                    try:
                        cur.close()
                    except Exception:
                        pass
                    try:
                        conn.close()
                    except Exception:
                        pass

                    if tipo == 'Z' or var_print.get():
                        try:
                            self._show_cierre_preview(text, tickets_rows)
                        except Exception:
                            # fallback: ensure at least a simple modal appears
                            t = ctk.CTkToplevel(self)
                            t.title('Previsualizar cierre')
                            tb = ctk.CTkTextbox(t, width=400, height=300)
                            tb.pack(fill='both', expand=True)
                            tb.insert('end', text)
                except Exception:
                    pass
                # if closure already existed, inform user; otherwise proceed to next day
                try:
                    if resumen.get('already_closed'):
                        try:
                            from tkinter import messagebox
                            messagebox.showinfo('Cierre', f"El día {fecha} ya estaba cerrado (id {resumen.get('cierre_id')}). Se mostrará el resumen.")
                        except Exception:
                            pass
                    # navigate to Tickets view for next day
                    import datetime as _dt
                    next_day = (_dt.date.fromisoformat(fecha) + _dt.timedelta(days=1)).isoformat()
                    self.controller.mostrar_tickets(next_day)
                except Exception:
                    try:
                        self.controller.mostrar_tickets()
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                try:
                    win.destroy()
                except Exception:
                    pass

        def _on_cancel():
            try:
                win.destroy()
            except Exception:
                pass

        ctk.CTkButton(btns, text='Confirmar Cierre', fg_color='darkred', command=_on_confirm).pack(side='left', padx=12)
        ctk.CTkButton(btns, text='Cancelar', command=_on_cancel).pack(side='right', padx=12)

    def _show_cierre_preview(self, cierre_text, tickets_rows=None):
        """Show a modal preview of the cierre text and an optional list of included tickets."""
        try:
            modal = ctk.CTkToplevel(self)
            modal.title('Previsualización cierre')
            modal.geometry('720x520')
            modal.transient(self)

            txt = ctk.CTkTextbox(modal, width=700, height=260)
            txt.pack(padx=10, pady=(10,6), fill='x')
            try:
                txt.insert('0.0', cierre_text)
            except Exception:
                txt.insert('end', str(cierre_text))
            try:
                txt.configure(state='disabled')
            except Exception:
                pass

            if tickets_rows:
                frame = ctk.CTkFrame(modal)
                frame.pack(fill='both', expand=True, padx=10, pady=6)
                from tkinter import ttk as _ttk
                tree = _ttk.Treeview(frame, columns=('num','hora','cajero','total'), show='headings', height=8)
                tree.heading('num', text='Nº')
                tree.heading('hora', text='Hora')
                tree.heading('cajero', text='Cajero')
                tree.heading('total', text='Total')
                tree.column('num', width=80)
                tree.column('hora', width=120)
                tree.column('cajero', width=160)
                tree.column('total', width=120, anchor='e')
                tree.pack(side='left', fill='both', expand=True)
                for r in tickets_rows:
                    tid, created_at, ticket_no, cajero_t, tot = r
                    hora = ''
                    try:
                        hora = datetime.fromisoformat(created_at).strftime('%H:%M:%S')
                    except Exception:
                        hora = created_at
                    tree.insert('', 'end', iid=str(tid), values=(ticket_no or '', hora, cajero_t or '', f"{(tot or 0):.2f}"))
                sb = _ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
                sb.pack(side='right', fill='y')
                tree.configure(yscrollcommand=sb.set)

            btns = ctk.CTkFrame(modal)
            btns.pack(fill='x', padx=10, pady=(6,10))

            def _imprimir():
                try:
                    from modulos.impresion.impresora import imprimir_ticket_y_abrir_cajon
                    imprimir_ticket_y_abrir_cajon(cierre_text)
                except Exception:
                    pass

            ctk.CTkButton(btns, text='Imprimir', width=120, command=_imprimir).pack(side='right', padx=6)
            ctk.CTkButton(btns, text='Cerrar', width=120, command=modal.destroy).pack(side='right', padx=6)
        except Exception:
            pass

    def _ask_large_price(self, title, prompt):
        win = ctk.CTkToplevel(self)
        win.title(title)
        try:
            win.geometry("480x220")
        except Exception:
            pass
        win.transient(self)
        win.grab_set()

        lbl = ctk.CTkLabel(win, text=prompt, font=("Arial", 16))
        lbl.pack(pady=(18, 6))

        var = ctk.StringVar()
        entry = ctk.CTkEntry(win, textvariable=var, font=("Arial", 26), justify='center')
        entry.pack(fill='x', padx=24, pady=(0, 12))
        entry.focus_set()
        # accept Enter in the entry as OK and Escape as cancel
        entry.bind("<Return>", lambda e: _on_ok())
        entry.bind("<KP_Enter>", lambda e: _on_ok())
        win.bind("<Escape>", lambda e: _on_cancel())

        result = {'value': None}

        def _on_ok():
            try:
                v = float(var.get().replace(',', '.'))
                result['value'] = v
                win.destroy()
            except Exception:
                messagebox.showerror('Error', 'Introduce un número válido')

        def _on_cancel():
            win.destroy()

        btns = ctk.CTkFrame(win)
        btns.pack(pady=(6, 16))
        ctk.CTkButton(btns, text='Aceptar', width=140, command=_on_ok).pack(side='left', padx=8)
        ctk.CTkButton(btns, text='Cancelar', width=140, command=_on_cancel).pack(side='left', padx=8)

        win.wait_window()
        return result['value']

    def buscar_producto_evento(self):
        self.buscar_producto(None)

    def buscar_producto(self, event):
        codigo_input = self.entry_codigo.get().strip()
        if not codigo_input:
            return

        conn = connect()
        cursor = conn.cursor()
        try:
            # try exact SKU/EAN first
            query = '''
                SELECT p.nombre, pr.pvp, p.sku, p.tipo_iva, p.id, COALESCE(p.pvp_variable, 0) as pvp_variable
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                LEFT JOIN codigos_barras cb ON p.id = cb.producto_id
                WHERE (p.sku = ? OR cb.ean = ?)
                AND pr.activo = 1
                LIMIT 1
            '''
            cursor.execute(query, (codigo_input, codigo_input))
            resultado = cursor.fetchone()

            if resultado:
                pvp_variable = resultado[5] if len(resultado) > 5 else 0
                precio_base = resultado[1]
                if pvp_variable:
                    try:
                        val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                        if val is None:
                            conn.close()
                            self.entry_codigo.delete(0, 'end')
                            return
                        precio_base = float(val)
                    except Exception:
                        pass

                producto = {
                    "nombre": resultado[0],
                    "precio": precio_base,
                    "sku": resultado[2],
                    "iva": resultado[3],
                    "id": resultado[4],
                    "cantidad": 1
                }

                encontrado = False
                for item in self.carrito:
                    if item['id'] == producto['id']:
                        item['cantidad'] += 1
                        encontrado = True
                        break

                if not encontrado:
                    self.carrito.append(producto)

                self.actualizar_visor()
                conn.close()
                self.entry_codigo.delete(0, 'end')
                return

            # otherwise do a LIKE search and render matches in selector_area
            like = f"%{codigo_input}%"
            cursor.execute('''
                SELECT p.id, p.nombre, pr.pvp, p.sku, COALESCE(p.pvp_variable,0) as pvp_variable
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                WHERE (p.nombre LIKE ? OR p.sku LIKE ?) AND pr.activo = 1
                ORDER BY p.nombre COLLATE NOCASE
                LIMIT 30
            ''', (like, like))
            rows = cursor.fetchall()
            conn.close()

            # clear and show results in selector area
            try:
                for w in self.selector_area.winfo_children():
                    w.destroy()
            except Exception:
                pass

            if not rows:
                lbl = ctk.CTkLabel(self.selector_area, text="No hay resultados.")
                lbl.pack(pady=6)
                self.entry_codigo.delete(0, 'end')
                return

            for pid, nombre, pvp, sku, pvp_variable in rows:
                def _make_cmd(pid=pid, pvp=pvp, sku=sku, nombre=nombre, pvp_variable=pvp_variable):
                    def _cmd():
                        precio_base = pvp
                        if pvp_variable:
                            try:
                                val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                                if val is None:
                                    return
                                precio_base = float(val)
                            except Exception:
                                pass
                        producto = {"nombre": nombre, "precio": precio_base, "sku": sku, "iva": 21, "id": pid, "cantidad": 1}
                        encontrado = False
                        for item in self.carrito:
                            if item['id'] == producto['id']:
                                item['cantidad'] += 1
                                encontrado = True
                                break
                        if not encontrado:
                            self.carrito.append(producto)
                        self.actualizar_visor()
                    return _cmd

                btn = ctk.CTkButton(self.selector_area, text=f"{nombre} — {sku} — {pvp:.2f}€", command=_make_cmd())
                btn.pack(fill='x', pady=4, padx=6)

            self.entry_codigo.delete(0, 'end')

        except Exception as e:
            print(f"Error búsqueda global: {e}")
            try:
                conn.close()
            except Exception:
                pass

    def actualizar_visor(self):
        self.lista_productos.configure(state="normal")
        self.lista_productos.delete("0.0", "end")
        
        total_pagar = 0.0
        total_base = 0.0
        total_iva = 0.0

        self.lista_productos.insert("end", f"{'CANT':<5} {'PRODUCTO':<25} {'PRECIO':>10} {'TOTAL':>10}\n")
        self.lista_productos.insert("end", "-"*55 + "\n")

        for idx, item in enumerate(self.carrito):
            subtotal = item['cantidad'] * item['precio']
            divisor = 1 + (item['iva'] / 100)
            base_item = subtotal / divisor
            iva_item = subtotal - base_item

            total_pagar += subtotal
            total_base += base_item
            total_iva += iva_item

            linea = f"{item['cantidad']}x    {item['nombre'][:22]:<25} {item['precio']:>8.2f}€ {subtotal:>9.2f}€\n"
            # insertar y etiquetar la línea para selección
            self.lista_productos.insert("end", linea)
            line_no = 3 + idx
            try:
                self.lista_productos._textbox.tag_remove(f"item_{idx}", f"{line_no}.0", f"{line_no}.end")
            except Exception:
                pass
            try:
                self.lista_productos._textbox.tag_add(f"item_{idx}", f"{line_no}.0", f"{line_no}.end")
            except Exception:
                pass

        self.lista_productos.configure(state="disabled")
        self.lbl_total.configure(text=f"TOTAL: {total_pagar:.2f} €")
        self.lbl_iva.configure(text=f"Base Imponible: {total_base:.2f}€ | Total IVA: {total_iva:.2f}€")

    def _update_impr_button(self):
        try:
            enabled = getattr(self.controller, 'imprimir_tickets_enabled', False)
            if enabled:
                try:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET (ON)", fg_color="#2E8B57")
                except Exception:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET (ON)")
            else:
                try:
                    # visual 'off' state: gray
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET", fg_color="#6c6c6c")
                except Exception:
                    self.btn_impr.configure(text="🖨️ IMPR. TICKET")
        except Exception:
            pass

    def _on_text_click(self, event):
        try:
            # conseguir índice de línea bajo el click
            index = self.lista_productos._textbox.index(f"@{event.x},{event.y}")
            line = int(index.split('.')[0])
            # los items empiezan en la línea 3 (1: header, 2: separador)
            item_idx = line - 3
            if item_idx < 0 or item_idx >= len(self.carrito):
                return
            # quitar selección previa
            try:
                self.lista_productos._textbox.tag_remove('selected', '1.0', 'end')
            except Exception:
                pass
            # añadir tag selected a la línea
            try:
                self.lista_productos._textbox.tag_add('selected', f"{line}.0", f"{line}.end")
            except Exception:
                pass
            self._selected_carrito_index = item_idx
            # asegurar foco para recibir teclas
            try:
                self.lista_productos._textbox.focus_set()
            except Exception:
                pass
        except Exception:
            pass

    def _on_delete_key(self, event):
        try:
            idx = getattr(self, '_selected_carrito_index', None)
            if idx is None:
                return
            if 0 <= idx < len(self.carrito):
                # si hay más de 1 unidad, decrementar en 1; si no, eliminar la línea
                if self.carrito[idx].get('cantidad', 1) > 1:
                    self.carrito[idx]['cantidad'] -= 1
                    # mantener la selección en la misma línea
                else:
                    del self.carrito[idx]
                    # limpiar selección si el item desaparece
                    try:
                        self.lista_productos._textbox.tag_remove('selected', '1.0', 'end')
                    except Exception:
                        pass
                    self._selected_carrito_index = None
                self.actualizar_visor()
        except Exception as e:
            print(f"Error al eliminar item: {e}")

    # --- FUNCIONES DE COBRO ---
    def abrir_cobro_efectivo(self):
        if not self.carrito:
            print("El carrito está vacío, no se puede cobrar.")
            return

        # Mostrar entrada de efectivo
        self.lbl_efectivo.pack()
        self.entry_efectivo.pack()
        # iniciar buffer vacío cuando se abre el cobro
        self._cash_buffer = ""
        self.efectivo_var.set("")
        self.entry_efectivo.focus()
        self.entry_efectivo.delete(0, 'end')
        self._awaiting_final_confirmation = False

    def _on_global_key(self, event):
        """
        Captura teclas numéricas globales para rellenar el campo de efectivo.
        - Ignora si el foco está en otro Entry/Text distinto del entry_efectivo.
        - Digitos y separador decimal se acumulan en _cash_buffer.
        - BackSpace borra y Enter confirma (procesa el cobro).
        """
        try:
            focused = self.controller.focus_get()
            # si el foco está en un entry/text distinto del entry_efectivo, no interferir
            if focused is not None and focused is not self.entry_efectivo:
                cls = focused.winfo_class().lower()
                if 'entry' in cls or 'text' in cls:
                    return

            ch = event.char
            key = event.keysym

            # Enter: si hay buffer, fijar valor y pedir confirmación (doble Enter)
            if key in ("Return", "KP_Enter"):
                if self._cash_buffer:
                    try:
                        val = float(self._cash_buffer.replace(",", "."))
                        # mostrar con 2 decimales
                        self.efectivo_var.set(f"{val:.2f}")
                        # if not already awaiting confirmation, change label and wait for second Enter
                        if not getattr(self, '_awaiting_final_confirmation', False):
                            self._awaiting_final_confirmation = True
                            try:
                                total = sum(item['precio'] * item['cantidad'] for item in self.carrito)
                                cambio = val - total
                                self.lbl_efectivo.configure(text=f"Pulsa Enter para confirmar — Efectivo: {val:.2f}€ | Total: {total:.2f}€ | Cambio: {cambio:.2f}€", text_color="yellow")
                            except Exception:
                                pass
                            # clear buffer but keep amount shown
                            self._cash_buffer = ""
                            return
                        else:
                            # second Enter -> process
                            try:
                                self.procesar_efectivo(None)
                            except Exception:
                                pass
                    except Exception:
                        pass
                # limpiar buffer
                self._cash_buffer = ""
                return

            # Backspace
            if key == "BackSpace":
                self._cash_buffer = self._cash_buffer[:-1]
                self.efectivo_var.set(self._cash_buffer)
                return

            # aceptar dígitos y separador decimal
            if ch and (ch.isdigit() or ch in (".", ",")):
                # si el entry no está visible, abrir cobro para que se muestre
                try:
                    if not self.entry_efectivo.winfo_ismapped():
                        self.abrir_cobro_efectivo()
                except Exception:
                    pass
                if ch == ",":
                    ch = "."
                self._cash_buffer += ch
                self.efectivo_var.set(self._cash_buffer)
        except Exception:
            pass

    def procesar_efectivo(self, event):
        try:
            # If not yet confirmed, set awaiting flag and prompt
            if not getattr(self, '_awaiting_final_confirmation', False):
                try:
                    # try to show entered amount and computed change
                    val = 0.0
                    try:
                        val = float(self.entry_efectivo.get().replace(',', '.'))
                    except Exception:
                        pass
                    total = sum(item['precio'] * item['cantidad'] for item in self.carrito)
                    cambio = val - total
                    self._awaiting_final_confirmation = True
                    self.lbl_efectivo.configure(text=f"Pulsa Enter para confirmar — Efectivo: {val:.2f}€ | Total: {total:.2f}€ | Cambio: {cambio:.2f}€", text_color="yellow")
                except Exception:
                    pass
                return

            efectivo = float(self.entry_efectivo.get())
            total = sum(item['precio'] * item['cantidad'] for item in self.carrito)
            if efectivo >= total:
                cambio = efectivo - total
                # specify payment method as EFECTIVO
                self.limpiar_tras_venta(efectivo, cambio, forma_pago='EFECTIVO')
                # Ocultar entrada
                self.lbl_efectivo.pack_forget()
                self.entry_efectivo.pack_forget()
                self._awaiting_final_confirmation = False
            else:
                self.lbl_efectivo.configure(text="Efectivo insuficiente", text_color="red")
                self.after(2000, lambda: self.lbl_efectivo.configure(text="Introducir efectivo entregado:", text_color="red"))
        except ValueError:
            self.lbl_efectivo.configure(text="Cantidad inválida", text_color="red")
            self.after(2000, lambda: self.lbl_efectivo.configure(text="Introducir efectivo entregado:", text_color="red"))

    def limpiar_tras_venta(self, efectivo, cambio, forma_pago='EFECTIVO'):
        print("¡Venta completada!")
        
        # Generar el texto del ticket
        if self.carrito:
            # First: save ticket and lines to DB (lightweight)
            try:
                conn = connect()
                cur = conn.cursor()
                from datetime import datetime
                now = datetime.now().isoformat()
                # We'll rely on the table autoincrement `id` as the global ticket number.
                # Insert first, then read lastrowid and set `ticket_no = id` to guarantee uniqueness.

                total = sum(item['precio'] * item['cantidad'] for item in self.carrito)
                cajero = getattr(self, 'lbl_cajero', None)
                cajero_txt = ''
                try:
                    if cajero is not None:
                        raw = cajero.cget('text')
                        # remove emoji and extract name after 'Cajero:' if present
                        try:
                            raw = raw.replace('👤', '').strip()
                        except Exception:
                            pass
                        if 'Cajero' in raw:
                            try:
                                name = raw.split('Cajero')[-1]
                                # remove leading ':' and whitespace
                                name = name.lstrip(':').strip()
                                # remove role in parentheses if present
                                if '(' in name:
                                    name = name.split('(')[0].strip()
                                cajero_txt = name
                            except Exception:
                                cajero_txt = raw
                        else:
                            cajero_txt = raw
                except Exception:
                    cajero_txt = ''
                try:
                    # Compute next visible ticket number from existing tickets.
                    # This ensures that if the DB sequences were reset externally,
                    # the next ticket will start at 1 when table is empty.
                    try:
                        cur.execute('SELECT COALESCE(MAX(ticket_no),0)+1 FROM tickets')
                        next_ticket_no = cur.fetchone()[0] or 1
                    except Exception:
                        next_ticket_no = 1

                    cur.execute('INSERT INTO tickets (created_at, total, cajero, cliente, ticket_no, forma_pago, pagado, cambio) VALUES (?,?,?,?,?,?,?,?)', (
                        now, total, cajero_txt, None, next_ticket_no, forma_pago, efectivo, cambio
                    ))
                    ticket_id = cur.lastrowid
                    # insert lines
                    for item in self.carrito:
                        try:
                            # Prefer authoritative SKU from productos table using product id when available
                            sku_to_store = None
                            try:
                                pid = item.get('id')
                                if pid is not None:
                                    cur2 = conn.cursor()
                                    try:
                                        cur2.execute('SELECT sku FROM productos WHERE id=? LIMIT 1', (pid,))
                                        row = cur2.fetchone()
                                        if row and row[0]:
                                            sku_to_store = row[0]
                                    finally:
                                        try:
                                            cur2.close()
                                        except Exception:
                                            pass
                            except Exception:
                                sku_to_store = None

                            if not sku_to_store:
                                sku_to_store = item.get('sku')

                            cur.execute('INSERT INTO ticket_lines (ticket_id, sku, nombre, cantidad, precio, iva) VALUES (?,?,?,?,?,?)', (
                                ticket_id, sku_to_store, item.get('nombre'), item.get('cantidad'), item.get('precio'), item.get('iva', 0)
                            ))
                        except Exception:
                            pass
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
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

            except Exception as e:
                print(f"Error guardando ticket en BD: {e}")

                # Then: print/preview only if printing is enabled in controller
            try:
                # Fetch saved ticket and lines from DB to build an authoritative print text
                try:
                    conn2 = connect()
                    cur2 = conn2.cursor()
                    cur2.execute('SELECT id, created_at, cajero, total, ticket_no, forma_pago, pagado, cambio, cliente FROM tickets WHERE id=? LIMIT 1', (ticket_id,))
                    meta = cur2.fetchone()
                    cur2.execute('SELECT sku, nombre, cantidad, precio, iva FROM ticket_lines WHERE ticket_id=? ORDER BY id ASC', (ticket_id,))
                    lines = cur2.fetchall()
                except Exception:
                    meta = None
                    lines = []
                finally:
                    try:
                        cur2.close()
                    except Exception:
                        pass
                    try:
                        conn2.close()
                    except Exception:
                        pass

                # Build textual ticket (header + lines + totals + pagado/cambio)
                try:
                    if meta:
                        _, created_at, cajero_meta, total_meta, ticket_no_meta, forma_meta, pagado_meta, cambio_meta, cliente_meta = meta
                    else:
                        created_at = None
                        cajero_meta = ''
                        total_meta = total
                        ticket_no_meta = ticket_id
                        forma_meta = forma_pago
                        pagado_meta = efectivo
                        cambio_meta = cambio
                        cliente_meta = ''
                except Exception:
                    created_at = None
                    cajero_meta = ''
                    total_meta = total
                    ticket_no_meta = ticket_id
                    forma_meta = forma_pago
                    pagado_meta = efectivo
                    cambio_meta = cambio
                    cliente_meta = ''

                header_lines = []
                header_lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
                header_lines.append("-"*30 + "\n")
                header_lines.append(f"FACTURA Nº: {ticket_no_meta}\n")
                try:
                    if created_at:
                        dt_disp = datetime.fromisoformat(created_at).strftime("%d/%m/%Y %H:%M")
                        header_lines.append(f"Fecha: {dt_disp}\n")
                except Exception:
                    header_lines.append(f"Fecha: {created_at or ''}\n")
                header_lines.append(f"Cajero: {cajero_meta}\n")
                header_lines.append(f"Cliente: {cliente_meta or ''}\n")
                header_lines.append("-"*30 + "\n")

                body_lines = []
                for sku, nombre, cantidad_l, precio_l, iva_l in lines:
                    try:
                        cantidad_show = int(cantidad_l) if isinstance(cantidad_l, float) and float(cantidad_l).is_integer() else cantidad_l
                    except Exception:
                        cantidad_show = cantidad_l
                    try:
                        # Do not print SKU on tickets; show only product name and unit price
                        body_lines.append(f"{cantidad_show}x {nombre}  {precio_l:.2f}\n")
                    except Exception:
                        body_lines.append(f"{cantidad_show}x {nombre}  {precio_l}\n")

                totals_lines = []
                totals_lines.append("-"*30 + "\n")
                try:
                    totals_lines.append(f"TOTAL: {total_meta:.2f}\n")
                except Exception:
                    totals_lines.append(f"TOTAL: {total_meta}\n")
                if pagado_meta is not None:
                    try:
                        totals_lines.append(f"EFECTIVO: {pagado_meta:.2f}\n")
                    except Exception:
                        totals_lines.append(f"EFECTIVO: {pagado_meta}\n")
                if cambio_meta is not None:
                    try:
                        totals_lines.append(f"CAMBIO: {cambio_meta:.2f}\n")
                    except Exception:
                        totals_lines.append(f"CAMBIO: {cambio_meta}\n")

                ticket_texto = ''.join(header_lines) + ''.join(body_lines) + ''.join(totals_lines) + "\n¡Gracias por tu compra!\n"

                if getattr(self.controller, 'imprimir_tickets_enabled', False):
                    # Prefer preview_ticket on macOS, otherwise try direct print
                    if sys.platform == 'darwin' and preview_ticket is not None:
                        try:
                            preview_ticket(self, ticket_texto, modo='ventana')
                        except Exception:
                            try:
                                preview_ticket(None, ticket_texto, modo='terminal')
                            except Exception:
                                pass
                    else:
                        from modulos.impresion.impresora import imprimir_ticket_y_abrir_cajon
                        try:
                            imprimir_ticket_y_abrir_cajon(ticket_texto)
                        except Exception:
                            try:
                                if preview_ticket is not None:
                                    preview_ticket(None, ticket_texto, modo='terminal')
                            except Exception:
                                pass
                else:
                    try:
                        print('Impresión automática desactivada; ticket guardado en BD.')
                    except Exception:
                        pass
            except Exception:
                pass
        
        # Limpiar carrito
        self.carrito = []
        self.actualizar_visor()

    def abrir_selector_sin_codigo(self):
        """Renderiza el selector de productos sin código dentro del área disponible"""
        selector = SelectorSinCodigo(self.agregar_producto_sin_codigo)
        selector.render_in_frame(self.selector_area)

    def agregar_producto_sin_codigo(self, producto_id, precio, nombre):
        """Agrega un producto al carrito desde el selector sin código"""
        try:
            conn = connect()
            cursor = conn.cursor()
            query = '''
                SELECT p.nombre, pr.pvp, p.sku, p.tipo_iva, p.id, COALESCE(p.pvp_variable, 0) as pvp_variable
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                WHERE p.id = ? AND pr.activo = 1
                LIMIT 1
            '''
            cursor.execute(query, (producto_id,))
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                pvp_variable = resultado[5] if len(resultado) > 5 else 0
                precio_base = resultado[1]
                if pvp_variable:
                    try:
                        val = self._ask_large_price("Precio variable", "¿Cuánto vale?")
                        if val is None:
                            return
                        precio_base = float(val)
                    except Exception:
                        pass

                producto = {
                    "nombre": resultado[0],
                    "precio": precio_base,
                    "sku": resultado[2],
                    "iva": resultado[3],
                    "id": resultado[4],
                    "cantidad": 1
                }
                
                encontrado = False
                for item in self.carrito:
                    if item['id'] == producto['id']:
                        item['cantidad'] += 1
                        encontrado = True
                        break
                
                if not encontrado:
                    self.carrito.append(producto)

                self.actualizar_visor()
        except Exception as e:
            print(f"Error al agregar producto: {e}")