import customtkinter as ctk


class HistoricoCierresView(ctk.CTkFrame):
    """Esqueleto de la pantalla de Histórico de Cierres."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.pack(fill='both', expand=True)
        self.controller = controller
import customtkinter as ctk
from datetime import datetime, timedelta
from database import connect
from tkinter import filedialog, messagebox

try:
    from modulos.impresion.impresora import imprimir_ticket_y_abrir_cajon
except Exception:
    imprimir_ticket_y_abrir_cajon = None


class HistoricoCierresView(ctk.CTkFrame):
    """Vista para el histórico de cierres con filtros y detalle."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.pack(fill='both', expand=True)
        self.controller = controller

        header = ctk.CTkFrame(self)
        header.pack(side='top', fill='x', padx=8, pady=8)

        ctk.CTkButton(header, text='← Volver', width=100, command=lambda: self.controller.mostrar_cierre_caja()).pack(side='right', padx=6)

        title = ctk.CTkLabel(self, text='HISTÓRICO DE CIERRES', font=(None, 20, 'bold'))
        title.pack(pady=(12,8))

        main = ctk.CTkFrame(self)
        main.pack(fill='both', expand=True, padx=12, pady=12)

        # two columns: left filters+list, right detail
        left = ctk.CTkFrame(main)
        left.pack(side='left', fill='y', padx=(0,12), pady=6)
        right = ctk.CTkFrame(main)
        right.pack(side='right', fill='both', expand=True, pady=6)

        # Filters pane
        frm_filters = ctk.CTkFrame(left)
        frm_filters.pack(fill='x', pady=(0,8))
        ctk.CTkLabel(frm_filters, text='Desde (YYYY-MM-DD)').pack(anchor='w', padx=6, pady=(6,0))
        self.ent_desde = ctk.CTkEntry(frm_filters, width=180)
        self.ent_desde.pack(padx=6, pady=(0,6))
        # bind Enter (normal and numeric keypad) to trigger search
        try:
            self.ent_desde.bind('<Return>', lambda e: self._on_search())
            self.ent_desde.bind('<KP_Enter>', lambda e: self._on_search())
        except Exception:
            pass
        ctk.CTkLabel(frm_filters, text='Hasta (YYYY-MM-DD)').pack(anchor='w', padx=6)
        self.ent_hasta = ctk.CTkEntry(frm_filters, width=180)
        self.ent_hasta.pack(padx=6, pady=(0,6))
        try:
            self.ent_hasta.bind('<Return>', lambda e: self._on_search())
            self.ent_hasta.bind('<KP_Enter>', lambda e: self._on_search())
        except Exception:
            pass
        ctk.CTkButton(frm_filters, text='🔍 Buscar', command=self._on_search).pack(padx=6, pady=(6,8))

        # Results list (scrollable)
        ctk.CTkLabel(left, text='Resultados').pack(anchor='w', padx=6)
        self.result_list = ctk.CTkScrollableFrame(left, width=300, height=400)
        self.result_list.pack(padx=6, pady=6)

        # Header for columns
        hdr = ctk.CTkFrame(self.result_list)
        hdr.pack(fill='x', pady=(0,4))
        ctk.CTkLabel(hdr, text='Nº', width=6).pack(side='left', padx=(2,6))
        ctk.CTkLabel(hdr, text='Fecha', width=18).pack(side='left', padx=6)
        ctk.CTkLabel(hdr, text='Importe', width=12).pack(side='left', padx=6)

        self._list_rows_container = ctk.CTkFrame(self.result_list)
        self._list_rows_container.pack(fill='both', expand=True)

        # Right column: detalle + botones
        self.detalle_txt = ctk.CTkTextbox(right, width=560, height=420)
        self.detalle_txt.pack(fill='both', expand=True, padx=6, pady=6)
        try:
            # use monospaced font and larger size for clarity
            self.detalle_txt.configure(font=('Courier', 16), fg_color='black', text_color='white')
        except Exception:
            pass
        btns = ctk.CTkFrame(right)
        btns.pack(fill='x', pady=6)
        self.btn_reimprimir = ctk.CTkButton(btns, text='🖨️ REIMPRIMIR TICKET', state='disabled', command=self._on_reimprimir)
        self.btn_reimprimir.pack(side='left', padx=8)
        self.btn_export = ctk.CTkButton(btns, text='📄 EXPORTAR CSV', state='disabled', command=self._on_export_csv)
        self.btn_export.pack(side='left', padx=8)
        # Button to view tickets of the cierre day (disabled until a cierre is selected)
        self.btn_ver_tickets = ctk.CTkButton(btns, text='🔍 VER TICKETS DEL DÍA', state='disabled', command=self._on_ver_tickets)
        self.btn_ver_tickets.pack(side='left', padx=8)

        # load last 30 days
        self._load_initial()

    def _load_initial(self):
        hasta = datetime.now().date()
        desde = hasta - timedelta(days=30)
        self.ent_desde.delete(0, 'end')
        self.ent_desde.insert(0, desde.isoformat())
        self.ent_hasta.delete(0, 'end')
        self.ent_hasta.insert(0, hasta.isoformat())
        self._query_and_populate(desde.isoformat(), hasta.isoformat())

    def _valid_date(self, s):
        try:
            datetime.strptime(s, '%Y-%m-%d')
            return True
        except Exception:
            return False

    def _on_search(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            try:
                from tkinter import messagebox as _mb
                _mb.showerror('Fecha', 'Formato de fecha inválido. Use YYYY-MM-DD')
            except Exception:
                print('Formato de fecha inválido. Use YYYY-MM-DD')
            return
        self._query_and_populate(d, h)

    def _query_and_populate(self, desde, hasta):
        conn = connect()
        cur = conn.cursor()
        try:
            # include new columns if present; COALESCE to treat NULL as 0.0
            cur.execute(
                "SELECT id, fecha_hora, total_ingresos, num_ventas, cajero, COALESCE(total_efectivo,0), COALESCE(total_tarjeta,0), COALESCE(total_web,0), COALESCE(puntos_ganados,0), COALESCE(puntos_canjeados,0) "
                "FROM cierres_caja WHERE date(fecha_hora) BETWEEN ? AND ? ORDER BY fecha_hora DESC",
                (desde, hasta)
            )
            rows = cur.fetchall()
        except Exception:
            rows = []
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # store found rows for export/printing
        self.cierres_encontrados = rows

        # populate list
        for w in self._list_rows_container.winfo_children():
            w.destroy()

        # compute aggregated totals for the period using SQL to be robust and fast
        try:
            # open a new connection/cursor for the aggregation (previous conn may be closed)
            conn2 = connect()
            cur2 = conn2.cursor()
            cur2.execute(
                "SELECT COUNT(*), COALESCE(SUM(total_ingresos),0), COALESCE(SUM(total_efectivo),0), COALESCE(SUM(total_tarjeta),0), COALESCE(SUM(total_web),0), COALESCE(SUM(puntos_ganados),0), COALESCE(SUM(puntos_canjeados),0), COALESCE(SUM(num_ventas),0) "
                "FROM cierres_caja WHERE date(fecha_hora) BETWEEN ? AND ?",
                (desde, hasta)
            )
            agg = cur2.fetchone()
            if agg:
                count_rows = int(agg[0] or 0)
                total_sum = float(agg[1] or 0.0)
                total_efectivo = float(agg[2] or 0.0)
                total_tarjeta = float(agg[3] or 0.0)
                total_web = float(agg[4] or 0.0)
                puntos_ganados = float(agg[5] or 0.0)
                puntos_canjeados = float(agg[6] or 0.0)
                total_ventas = int(agg[7] or 0)
            else:
                count_rows = 0
                total_sum = total_efectivo = total_tarjeta = total_web = puntos_ganados = puntos_canjeados = 0.0
                total_ventas = 0
            try:
                cur2.close()
            except Exception:
                pass
            try:
                conn2.close()
            except Exception:
                pass
        except Exception:
            # fallback to python accumulation if aggregate query fails
            total_sum = 0.0
            total_ventas = 0
            total_efectivo = 0.0
            total_tarjeta = 0.0
            puntos_ganados = 0.0
            puntos_canjeados = 0.0
            for r in rows:
                # rows may include additional columns
                cid = r[0]
                fecha_hora = r[1]
                total_ing = r[2]
                num_ventas = r[3]
                total_sum += float(total_ing or 0.0)
                total_ventas += int(num_ventas or 0)
            count_rows = len(rows)

        # populate list entries (use original rows variable)
        for r in rows:
            # r expected: id, fecha_hora, total_ingresos, num_ventas, cajero, total_efectivo, total_tarjeta, puntos_ganados, puntos_canjeados
            cid = r[0]
            fecha_hora = r[1]
            try:
                total_ing = float(r[2] or 0.0)
            except Exception:
                total_ing = 0.0
            item = ctk.CTkButton(self._list_rows_container, text=f"{cid}    {fecha_hora.split('T')[0]}    {total_ing:.2f}€", anchor='w', command=lambda _id=cid: self._on_select(_id))
            item.pack(fill='x', pady=2, padx=2)

        # enable/disable action buttons
        if rows:
            try:
                self.btn_reimprimir.configure(state='normal')
                self.btn_export.configure(state='normal')
            except Exception:
                pass
        else:
            try:
                self.btn_reimprimir.configure(state='disabled')
                self.btn_export.configure(state='disabled')
            except Exception:
                pass

        # show structured summary in detalle with larger font
        try:
            try:
                self.detalle_txt.configure(font=('Arial', 16), fg_color='black', text_color='white')
            except Exception:
                pass
            self.detalle_txt.delete('0.0', 'end')
            summary_lines = []
            summary_lines.append('RESUMEN DEL PERIODO\n')
            summary_lines.append(f'Cierres: {count_rows} | Ventas: {total_ventas}\n')
            summary_lines.append('-'*27 + '\n')
            summary_lines.append(f'TOTAL INGRESOS: {total_sum:.2f} €\n')
            summary_lines.append(f'- Efectivo: {total_efectivo:.2f} €\n')
            summary_lines.append(f'- Tarjeta:  {total_tarjeta:.2f} €\n')
            summary_lines.append(f'- Web:      {float(total_web or 0.0):.2f} €\n')
            summary_lines.append('-'*27 + '\n')
            summary_lines.append('FIDELIZACIÓN:\n')
            summary_lines.append(f'- Puntos Regalados: {puntos_ganados:.2f}\n')
            summary_lines.append(f'- Puntos Canjeados: {puntos_canjeados:.2f}\n')
            summary = ''.join(summary_lines)
            self.detalle_txt.insert('end', summary)
        except Exception:
            pass

    def _on_select(self, cierre_id):
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute('SELECT id, fecha_hora, total_ingresos, num_ventas, cajero, COALESCE(total_efectivo,0) AS total_efectivo, COALESCE(total_tarjeta,0) AS total_tarjeta, COALESCE(total_web,0) AS total_web, COALESCE(puntos_ganados,0) AS puntos_ganados, COALESCE(puntos_canjeados,0) AS puntos_canjeados FROM cierres_caja WHERE id=? LIMIT 1', (cierre_id,))
            r = cur.fetchone()
        except Exception:
            r = None
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        if not r:
            return
        # r: id, fecha_hora, total_ingresos, num_ventas, cajero, total_efectivo, total_tarjeta, total_web, puntos_ganados, puntos_canjeados
        cid, fecha_hora, total_ing, num_ventas, cajero, total_efectivo, total_tarjeta, total_web, puntos_ganados, puntos_canjeados = r

        # Find previous cierre datetime to determine the ticket period
        prev_dt = None
        try:
            conn_prev = connect()
            cur_prev = conn_prev.cursor()
            cur_prev.execute('SELECT MAX(fecha_hora) FROM cierres_caja WHERE fecha_hora < ?', (fecha_hora,))
            p = cur_prev.fetchone()
            prev_dt = p[0] if p and p[0] else None
        except Exception:
            prev_dt = None
        finally:
            try:
                cur_prev.close()
            except Exception:
                pass
            try:
                conn_prev.close()
            except Exception:
                pass

        if not prev_dt:
            prev_dt = '1970-01-01T00:00:00'

        # Aggregate ticket data for that period
        conn_t = connect()
        cur_t = conn_t.cursor()
        por_categoria = []
        por_tipo = []
        por_articulo = []
        por_forma_pago = []
        try:
            where_from = prev_dt
            where_to = fecha_hora

            # categories
            try:
                cur_t.execute(
                    "SELECT COALESCE(p.categoria,''), SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY p.categoria",
                    (where_from, where_to)
                )
                por_categoria = [{'categoria': r[0], 'qty': r[1], 'total': r[2]} for r in cur_t.fetchall()]
            except Exception:
                por_categoria = []

            # types
            try:
                cur_t.execute(
                    "SELECT COALESCE(p.tipo,''), SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id JOIN productos p ON tl.sku = p.sku "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY p.tipo",
                    (where_from, where_to)
                )
                por_tipo = [{'tipo': r[0], 'qty': r[1], 'total': r[2]} for r in cur_t.fetchall()]
            except Exception:
                por_tipo = []

            # top articles
            try:
                cur_t.execute(
                    "SELECT tl.nombre, SUM(tl.cantidad) as qty, COALESCE(SUM(tl.cantidad * tl.precio),0) as total "
                    "FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id "
                    "WHERE t.created_at > ? AND t.created_at <= ? GROUP BY tl.nombre ORDER BY qty DESC LIMIT 10",
                    (where_from, where_to)
                )
                por_articulo = [{'nombre': r[0], 'qty': r[1], 'total': r[2]} for r in cur_t.fetchall()]
            except Exception:
                por_articulo = []

            # forma de pago breakdown
            try:
                cur_t.execute("SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE created_at > ? AND created_at <= ? GROUP BY forma_pago", (where_from, where_to))
                por_forma_pago = [{'forma': r[0] or '', 'count': r[1], 'total': r[2]} for r in cur_t.fetchall()]
            except Exception:
                por_forma_pago = []

        finally:
            try:
                cur_t.close()
            except Exception:
                pass
            try:
                conn_t.close()
            except Exception:
                pass

        # Build detailed master ticket
        lines = []
        lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
        lines.append("="*40 + "\n")
        lines.append(f"CIERRE DE CAJA Nº {cid}\n")
        try:
            fh = datetime.fromisoformat(fecha_hora).strftime('%d/%m/%Y %H:%M')
        except Exception:
            fh = fecha_hora
        lines.append(f"Fecha: {fh}\n")
        lines.append(f"Cajero: {cajero or ''}\n")
        lines.append("-"*30 + "\n")
        lines.append(f"TOTAL INGRESOS: {float(total_ing or 0.0):.2f}€\n")
        lines.append(f"- Efectivo: {float(total_efectivo or 0.0):.2f}€\n")
        lines.append(f"- Tarjeta:  {float(total_tarjeta or 0.0):.2f}€\n")
        lines.append(f"- Web:      {float(total_web or 0.0):.2f}€\n")
        lines.append("-"*30 + "\n")
        lines.append("FIDELIZACIÓN:\n")
        lines.append(f"Puntos Ganados hoy: {float(puntos_ganados or 0.0):.2f}\n")
        lines.append(f"Puntos Canjeados hoy: {float(puntos_canjeados or 0.0):.2f} pts\n")
        lines.append("-"*30 + "\n")

        if por_categoria:
            lines.append("RESUMEN POR CATEGORÍAS:\n")
            for c in por_categoria:
                try:
                    qty = int(c.get('qty') or 0)
                except Exception:
                    qty = c.get('qty')
                lines.append(f"{c.get('categoria')}: {qty}  {float(c.get('total') or 0.0):.2f}€\n")
            lines.append("-"*30 + "\n")

        if por_tipo:
            lines.append("RESUMEN POR TIPOS:\n")
            for t in por_tipo:
                try:
                    qty = int(t.get('qty') or 0)
                except Exception:
                    qty = t.get('qty')
                lines.append(f"{t.get('tipo')}: {qty}  {float(t.get('total') or 0.0):.2f}€\n")
            lines.append("-"*30 + "\n")

        if por_articulo:
            lines.append("TOP 10 ARTÍCULOS:\n")
            for a in por_articulo:
                try:
                    qty = int(a.get('qty') or 0)
                except Exception:
                    qty = a.get('qty')
                lines.append(f"{a.get('nombre')}: {qty}  {float(a.get('total') or 0.0):.2f}€\n")
            lines.append("-"*30 + "\n")

        master_text = ''.join(lines)
        try:
            self.detalle_txt.delete('0.0', 'end')
            self.detalle_txt.insert('end', master_text)
        except Exception:
            pass

        # store selected cierre date (YYYY-MM-DD) and enable "ver tickets" button
        try:
            fecha_only = fecha_hora.split('T')[0] if fecha_hora and 'T' in fecha_hora else fecha_hora
            self._selected_cierre_date = fecha_only
            try:
                self.btn_ver_tickets.configure(state='normal')
            except Exception:
                pass
        except Exception:
            self._selected_cierre_date = None

    def _on_reimprimir(self):
        # print current content of the detalle_txt
        try:
            text = self.detalle_txt.get('0.0', 'end')
        except Exception:
            text = ''
        if not text.strip():
            messagebox.showinfo('Impresión', 'No hay texto para imprimir')
            return
        if imprimir_ticket_y_abrir_cajon is None:
            messagebox.showerror('Impresión', 'Función de impresión no disponible')
            return
        try:
            imprimir_ticket_y_abrir_cajon(text)
            messagebox.showinfo('Impresión', 'Enviado a impresora (simulado)')
        except Exception as e:
            messagebox.showerror('Impresión', f'Error enviando a impresora: {e}')

    def _on_ver_tickets(self):
        # Open the Tickets view for the selected cierre date
        fecha = getattr(self, '_selected_cierre_date', None)
        if not fecha:
            messagebox.showinfo('Ver tickets', 'No hay fecha de cierre seleccionada')
            return
        try:
            # call controller to show tickets for the date (YYYY-MM-DD)
            self.controller.mostrar_tickets(fecha, retorno_historico=True)
        except Exception:
            try:
                messagebox.showerror('Error', 'No se puede abrir la vista de tickets')
            except Exception:
                pass

    def _on_export_csv(self):
        # export self.cierres_encontrados to CSV (semicolon separated, utf-8-sig)
        rows = getattr(self, 'cierres_encontrados', []) or []
        if not rows:
            messagebox.showinfo('Exportar', 'No hay datos para exportar')
            return
        fpath = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')])
        if not fpath:
            return
        try:
            with open(fpath, 'w', encoding='utf-8-sig', newline='') as fh:
                # write header (include new columns if present)
                fh.write('ID Cierre;Fecha;Hora;Importe Total;Nº Ventas;Cajero;Total Efectivo;Total Tarjeta;Total Web;Puntos Ganados;Puntos Canjeados\n')
                for row in rows:
                    # rows expected (new schema): cid, fecha_hora, total_ing, num_ventas, cajero, total_efectivo, total_tarjeta, total_web, puntos_ganados, puntos_canjeados
                    try:
                        cid, fecha_hora, total_ing, num_ventas, cajero, total_efectivo, total_tarjeta, total_web, puntos_ganados, puntos_canjeados = row
                    except Exception:
                        # handle legacy rows without total_web (or older layouts)
                        try:
                            cid, fecha_hora, total_ing, num_ventas, cajero, total_efectivo, total_tarjeta, puntos_ganados, puntos_canjeados = row
                            total_web = 0.0
                        except Exception:
                            cid, fecha_hora, total_ing, num_ventas, cajero = row[:5]
                            total_efectivo = total_tarjeta = total_web = puntos_ganados = puntos_canjeados = 0.0
                    # split fecha and hora
                    fecha = fecha_hora.split('T')[0] if fecha_hora and 'T' in fecha_hora else fecha_hora
                    hora = ''
                    try:
                        if fecha_hora and 'T' in fecha_hora:
                            hora = fecha_hora.split('T')[1].split('.')[0]
                    except Exception:
                        hora = ''
                    # importe with comma decimal
                    try:
                        importe = f"{float(total_ing or 0):.2f}".replace('.', ',')
                    except Exception:
                        importe = str(total_ing or '')
                    try:
                        ef = f"{float(total_efectivo or 0):.2f}".replace('.', ',')
                    except Exception:
                        ef = '0,00'
                    try:
                        ta = f"{float(total_tarjeta or 0):.2f}".replace('.', ',')
                    except Exception:
                        ta = '0,00'
                    try:
                        we = f"{float(total_web or 0):.2f}".replace('.', ',')
                    except Exception:
                        we = '0,00'
                    try:
                        pg = f"{float(puntos_ganados or 0):.2f}".replace('.', ',')
                    except Exception:
                        pg = '0,00'
                    try:
                        pc = f"{float(puntos_canjeados or 0):.2f}".replace('.', ',')
                    except Exception:
                        pc = '0,00'
                    line = f"{cid};{fecha};{hora};{importe};{num_ventas or 0};{(cajero or '')};{ef};{ta};{we};{pg};{pc}\n"
                    fh.write(line)
            messagebox.showinfo('Exportar', f'Exportado a {fpath}')
        except Exception as e:
            messagebox.showerror('Exportar', f'Error exportando CSV: {e}')
