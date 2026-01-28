import customtkinter as ctk
import sqlite3
from database import connect
from datetime import datetime
from tkinter import ttk
try:
    from modulos.tpv.preview_imprimir import preview_ticket
except Exception:
    preview_ticket = None
from tkinter import messagebox as _mb


class TicketsView(ctk.CTkFrame):
    """
    Vista sencilla y eficiente de tickets:
    - Página por día (navegación Prev/Next)
    - Lista de tickets por hora para el día seleccionado
    - Al clicar un ticket se muestra el carrito/lineas en panel derecho
    """
    def __init__(self, parent, controller, fecha=None, retorno_historico=False):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.controller = controller
        self.retorno_historico = bool(retorno_historico)

        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=8, pady=8)

        self.btn_prev = ctk.CTkButton(header, text="◀ Día", width=100, command=self._prev_day)
        self.btn_prev.pack(side="left", padx=(0,8))
        self.lbl_fecha = ctk.CTkLabel(header, text="", font=(None, 14))
        self.lbl_fecha.pack(side="left")
        self.btn_next = ctk.CTkButton(header, text="Día ▶", width=100, command=self._next_day)
        self.btn_next.pack(side="left", padx=8)
        # Inline options removed for cleaner UI; keep state vars for compatibility
        self.opt_cat = ctk.BooleanVar(value=True)
        self.opt_top = ctk.BooleanVar(value=False)
        self.opt_print = ctk.BooleanVar(value=True)
        # Volver al TPV
        try:
            if self.retorno_historico:
                cmd = lambda: self.controller.mostrar_historico_cierres()
            else:
                cmd = lambda: self.controller.mostrar_ventas()
            self.btn_volver = ctk.CTkButton(header, text="⬅ Volver", width=100, command=cmd)
            self.btn_volver.pack(side="right", padx=8)
        except Exception:
            pass

        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=8, pady=8)

        left = ctk.CTkFrame(content)
        left.pack(side="left", fill="both", expand=True)

        # columns: Nº ticket, Hora, Cajero, Cliente, Total, Forma Pago
        self.tree = ttk.Treeview(left, columns=("ticket_no", "hora","cajero","cliente","total","forma_pago"), show="headings")
        self.tree.heading("ticket_no", text="Nº ticket", anchor="w")
        self.tree.heading("hora", text="Día/Hora", anchor="w")
        self.tree.heading("cajero", text="Cajero", anchor="w")
        self.tree.heading("cliente", text="Cliente", anchor="w")
        self.tree.heading("total", text="Total", anchor="w")
        self.tree.heading("forma_pago", text="Forma Pago", anchor="w")
        self.tree.column("ticket_no", width=90, anchor="w")
        self.tree.column("hora", width=140, anchor="w")
        self.tree.column("cajero", width=140, anchor="w")
        self.tree.column("cliente", width=140, anchor="w")
        self.tree.column("total", width=100, anchor="e")
        self.tree.column("forma_pago", width=120, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")
        # ensure headings and columns are left-justified where applicable
        try:
            style = ttk.Style()
            style.configure("Treeview.Heading", anchor='w')
        except Exception:
            pass
        # use single-click selection to load ticket detail
        self.tree.bind('<<TreeviewSelect>>', self._on_ticket_select)

        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        right = ctk.CTkFrame(content, width=360)
        right.pack(side="right", fill="y")
        self.detalle_txt = ctk.CTkTextbox(right, width=360, height=400)
        self.detalle_txt.pack(fill="both", expand=True, padx=6, pady=6)

        self.days = []
        self.day_index = 0
        self.current_date = None

        self._load_days()
        if fecha:
            try:
                idx = self.days.index(fecha)
                self.day_index = idx
            except Exception:
                pass
        self._show_day(self.day_index)

    def _load_days(self):
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT DISTINCT date(created_at) as dia FROM tickets ORDER BY dia DESC")
            rows = cur.fetchall()
            self.days = [r[0] for r in rows]
        except Exception:
            self.days = []
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _show_day(self, index):
        if not self.days:
            self.lbl_fecha.configure(text="No hay tickets")
            self.tree.delete(*self.tree.get_children())
            self.detalle_txt.delete("0.0", "end")
            return

        index = max(0, min(index, len(self.days)-1))
        self.day_index = index
        self.current_date = self.days[index]
        self.lbl_fecha.configure(text=f"Día {index+1}: {self.current_date}")

        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, created_at, total, ticket_no, forma_pago, cajero, pagado, cambio, cliente FROM tickets WHERE date(created_at)=? ORDER BY created_at ASC", (self.current_date,))
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

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            try:
                tid, created_at, total, ticket_no, forma, cajero, pagado, cambio, cliente = r
            except Exception:
                # fallback if row shorter
                tid = r[0]
                created_at = r[1] if len(r) > 1 else None
                total = r[2] if len(r) > 2 else 0
                ticket_no = r[3] if len(r) > 3 else ''
                forma = r[4] if len(r) > 4 else ''
                cajero = r[5] if len(r) > 5 else ''
                pagado = r[6] if len(r) > 6 else None
                cambio = r[7] if len(r) > 7 else None
                cliente = r[8] if len(r) > 8 else ''
            try:
                hora = datetime.fromisoformat(created_at).strftime("%d/%m %H:%M") if created_at else ""
            except Exception:
                # fallback to time only if parsing fails
                try:
                    hora = datetime.fromisoformat(created_at).strftime("%H:%M:%S")
                except Exception:
                    hora = created_at or ''
            try:
                total_str = f"{total:.2f}" if total is not None else ""
            except Exception:
                total_str = str(total)
            self.tree.insert("", "end", iid=str(tid), values=(ticket_no, hora, cajero, cliente or '', total_str, forma))

    def _on_ticket_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        tid = sel[0]
        self._load_ticket_detail(tid)

    def _load_ticket_detail(self, ticket_id):
        # Try to render the ticket in the same textual format used for printing
        try:
            from modulos.impresion.ticket_generator import generar_ticket
        except Exception:
            generar_ticket = None

        conn = connect()
        cur = conn.cursor()
        try:
            # basic ticket header info (include pagado/cambio and fidelización)
            cur.execute('SELECT created_at, cajero, total, ticket_no, forma_pago, pagado, cambio, cliente, puntos_ganados, puntos_canjeados, puntos_total_momento FROM tickets WHERE id=? LIMIT 1', (ticket_id,))
            meta = cur.fetchone()
            created_at = meta[0] if meta and len(meta) > 0 else None
            cajero = meta[1] if meta and len(meta) > 1 else ''
            total = meta[2] if meta and len(meta) > 2 else 0
            ticket_no = meta[3] if meta and len(meta) > 3 else ''
            forma = meta[4] if meta and len(meta) > 4 else ''
            pagado = meta[5] if meta and len(meta) > 5 else None
            cambio = meta[6] if meta and len(meta) > 6 else None
            cliente = meta[7] if meta and len(meta) > 7 else ''
            puntos_ganados_meta = meta[8] if meta and len(meta) > 8 else 0.0
            puntos_canjeados_meta = meta[9] if meta and len(meta) > 9 else 0.0
            puntos_total_momento_meta = meta[10] if meta and len(meta) > 10 else None

            cur.execute("SELECT sku, nombre, cantidad, precio, iva FROM ticket_lines WHERE ticket_id=? ORDER BY id ASC", (ticket_id,))
            rows = cur.fetchall()
        except Exception:
            rows = []
            created_at = None
            cajero = ''
            total = 0
            ticket_no = ''
            forma = ''
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        # Build the textual ticket from the DB record so it matches the printed ticket
        header_lines = []
        header_lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
        header_lines.append("-"*30 + "\n")
        header_lines.append(f"FACTURA Nº: {ticket_no}\n")
        try:
            if created_at:
                dt_disp = datetime.fromisoformat(created_at).strftime("%d/%m/%Y %H:%M")
                header_lines.append(f"Fecha: {dt_disp}\n")
        except Exception:
            header_lines.append(f"Fecha: {created_at or ''}\n")
        header_lines.append(f"Cajero: {cajero}\n")
        header_lines.append(f"Cliente: {cliente or ''}\n")
        header_lines.append("-"*30 + "\n")

        body_lines = []
        for sku, nombre, cantidad, precio, iva in rows:
            try:
                if isinstance(cantidad, float) and float(cantidad).is_integer():
                    cantidad_show = int(cantidad)
                else:
                    cantidad_show = cantidad
            except Exception:
                cantidad_show = cantidad
            try:
                body_lines.append(f"{cantidad_show}x {nombre}  {precio:.2f}\n")
            except Exception:
                body_lines.append(f"{cantidad}x {nombre}  {precio}\n")

        totals_lines = []
        totals_lines.append("-"*30 + "\n")
        try:
            totals_lines.append(f"TOTAL: {total:.2f}\n")
        except Exception:
            totals_lines.append(f"TOTAL: {total}\n")
        try:
            if pagado is not None:
                etiqueta = forma or 'EFECTIVO'
                try:
                    totals_lines.append(f"{etiqueta}: {pagado:.2f}\n")
                except Exception:
                    totals_lines.append(f"{etiqueta}: {pagado}\n")
            if cambio is not None:
                try:
                    totals_lines.append(f"CAMBIO: {cambio:.2f}\n")
                except Exception:
                    totals_lines.append(f"CAMBIO: {cambio}\n")
        except Exception:
            pass

        # Build final ticket text identical to the TPV printout
        try:
            pg = float(puntos_ganados_meta) if puntos_ganados_meta is not None else 0.0
        except Exception:
            pg = 0.0
        try:
            pc = float(puntos_canjeados_meta) if puntos_canjeados_meta is not None else 0.0
        except Exception:
            pc = 0.0
        try:
            saldo_final = float(puntos_total_momento_meta) if puntos_total_momento_meta is not None else None
        except Exception:
            saldo_final = None

        # totals + thank you line
        ticket_core = ''.join(header_lines) + ''.join(body_lines) + ''.join(totals_lines) + "\n¡Gracias por tu compra!\n"

        fide_section = []
        fide_section.append('\n' + ('-'*20) + '\n')
        if pc and float(pc) != 0:
            try:
                fide_section.append(f"Puntos canjeados: -{float(pc):.2f} pts\n")
            except Exception:
                pass
        if pg and float(pg) != 0:
            try:
                fide_section.append(f"Puntos ganados en esta compra: {float(pg):.2f}\n")
            except Exception:
                pass
        # Saldo final line (show as blank if None)
        try:
            if saldo_final is not None:
                fide_section.append(f"Saldo total de puntos: {float(saldo_final):.2f}\n")
            else:
                fide_section.append("Saldo total de puntos: \n")
        except Exception:
            fide_section.append("Saldo total de puntos: \n")

        text = ticket_core + ''.join(fide_section)

        self.detalle_txt.delete("0.0", "end")
        try:
            self.detalle_txt.insert("end", text)
        except Exception:
            pass

    def _build_cierre_text(self, resumen, fecha, tipo='X'):
        lines = []
        lines.append("CIERRE DE CAJA\n")
        lines.append(f"Tipo: {resumen.get('numero','') or ''} - {tipo}\n")
        lines.append(f"Día: {fecha}\n")
        lines.append(f"Tickets: {resumen.get('count_tickets',0)}  TOTAL: {resumen.get('total',0):.2f}€\n")
        for p in resumen.get('por_forma_pago', []):
            lines.append(f"{p.get('forma','OTROS')}: {p.get('total',0):.2f}€\n")
        # Explicit Web total (ensure visibility even if not present in por_forma_pago)
        try:
            if resumen.get('total_web') is not None:
                lines.append(f"Web: {float(resumen.get('total_web') or 0.0):.2f}€\n")
        except Exception:
            pass
        if resumen.get('por_categoria'):
            lines.append('\nDesglose por categoría:\n')
            for c in resumen.get('por_categoria'):
                lines.append(f"{c.get('categoria')}: {c.get('qty')}  {c.get('total'):.2f}€\n")
        if resumen.get('top_products'):
            lines.append('\nTop productos:\n')
            for tprod in resumen.get('top_products'):
                lines.append(f"{tprod.get('nombre')}: {tprod.get('qty')}  {tprod.get('total'):.2f}€\n")
        return ''.join(lines)

    def _on_consulta(self):
        # Generate an informative closure (type X) and display in the right panel
        if not self.current_date:
            _mb.showinfo('Consulta', 'No hay fecha seleccionada')
            return
        from database import close_day
        try:
            resumen = close_day(self.current_date, tipo='X', include_category=self.opt_cat.get(), include_products=self.opt_top.get())
        except Exception as e:
            _mb.showerror('Error', f'Error generando consulta: {e}')
            return
        text = self._build_cierre_text(resumen, self.current_date, tipo='X')
        # display in detalle_txt (right pane)
        try:
            self.detalle_txt.delete('0.0', 'end')
            self.detalle_txt.insert('end', text)
        except Exception:
            # fallback to preview modal
            if preview_ticket is not None:
                try:
                    preview_ticket(self, text, modo='ventana')
                except Exception:
                    preview_ticket(None, text, modo='terminal')

    def _on_cierre_z(self):
        # Perform definitive closure (Z) for the current date
        if not self.current_date:
            _mb.showinfo('Cierre', 'No hay fecha seleccionada')
            return
        from database import close_day
        tipo = 'Z'
        try:
            resumen = close_day(self.current_date, tipo=tipo, include_category=self.opt_cat.get(), include_products=self.opt_top.get())
        except Exception as e:
            _mb.showerror('Error', f'Error ejecutando cierre: {e}')
            return
        # Inform user and show preview
        try:
            _mb.showinfo('Cierre creado', f"Tipo: {tipo}  Número: {resumen.get('numero','')}\nTickets: {resumen.get('count_tickets',0)}\nTotal: {resumen.get('total',0):.2f}€")
        except Exception:
            pass
        text = self._build_cierre_text(resumen, self.current_date, tipo=tipo)
        # show preview modal
        if preview_ticket is not None:
            try:
                preview_ticket(self, text, modo='ventana')
            except Exception:
                preview_ticket(None, text, modo='terminal')
        else:
            try:
                self.detalle_txt.delete('0.0', 'end')
                self.detalle_txt.insert('end', text)
            except Exception:
                pass

    def _prev_day(self):
        if self.day_index > 0:
            self.day_index -= 1
            self._show_day(self.day_index)

    def _next_day(self):
        if self.day_index < len(self.days)-1:
            self.day_index += 1
            self._show_day(self.day_index)
