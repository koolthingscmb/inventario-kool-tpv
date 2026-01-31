import customtkinter as ctk
from tkinter import ttk
from tkinter import messagebox as _mb
from datetime import datetime
from database import connect, close_day
from modulos.tpv.cierre_service import CierreService
try:
    from modulos.tpv.preview_imprimir import preview_ticket
except Exception:
    preview_ticket = None
from modulos.impresion.print_service import ImpresionService

# instancia compartida de impresión
impresion_service = ImpresionService()


class CierreCajaView(ctk.CTkFrame):
    """
    Vista para el cierre de caja (solo admin).
    Muestra tickets desde el último cierre hasta la última venta del día actual.
    Visualmente similar a `TicketsView` pero sin paginación.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.controller = controller

        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=8, pady=8)

        self.lbl_fecha = ctk.CTkLabel(header, text="", font=(None, 14))
        self.lbl_fecha.pack(side="left")

        # Header controls: checkboxes and action buttons
        opts = ctk.CTkFrame(header)
        opts.pack(side='right')

        # Checkboxes: Resumen Categorías, Resumen Tipos, Resumen Artículos
        # Inicialmente desactivados según especificación
        self.opt_cat = ctk.BooleanVar(value=False)
        self.opt_top = ctk.BooleanVar(value=False)
        self.opt_lines = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(opts, text="Resumen Categorías", variable=self.opt_cat).pack(side='left', padx=6)
        ctk.CTkCheckBox(opts, text="Resumen Tipos", variable=self.opt_top).pack(side='left', padx=6)
        ctk.CTkCheckBox(opts, text="Resumen Artículos", variable=self.opt_lines).pack(side='left', padx=6)

        # Action buttons: Consulta, Cierre Z and Back
        ctk.CTkButton(opts, text="Consulta", width=100, command=self._on_consulta).pack(side='left', padx=6)
        ctk.CTkButton(opts, text="Cierre Z", width=100, fg_color='darkred', command=self._on_cierre_z).pack(side='left', padx=6)
        # Histórico button (placeholder)
        ctk.CTkButton(header, text="📂 HISTÓRICO", width=120, command=lambda: self.controller.mostrar_historico_cierres()).pack(side='right', padx=6)
        ctk.CTkButton(header, text="← Volver", width=90, command=lambda: self.controller.mostrar_ventas()).pack(side='right', padx=6)

        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=8, pady=8)

        left = ctk.CTkFrame(content)
        left.pack(side="left", fill="both", expand=True)

        self.tree = ttk.Treeview(left, columns=("ticket_no","hora","cajero","cliente","total","forma_pago"), show='headings')
        self.tree.heading("ticket_no", text="Nº ticket")
        self.tree.heading("hora", text="Hora")
        self.tree.heading("cajero", text="Cajero")
        self.tree.heading("cliente", text="Cliente")
        self.tree.heading("total", text="Total")
        self.tree.heading("forma_pago", text="Forma Pago")
        self.tree.column("ticket_no", width=90)
        self.tree.column("hora", width=100)
        self.tree.column("cajero", width=140)
        self.tree.column("cliente", width=140)
        self.tree.column("total", width=100, anchor='e')
        self.tree.column("forma_pago", width=120)
        self.tree.pack(fill='both', expand=True, side='left')
        self.tree.bind('<<TreeviewSelect>>', self._on_ticket_select)

        sb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side='right', fill='y')

        right = ctk.CTkFrame(content, width=360)
        right.pack(side='right', fill='y')
        self.detalle_txt = ctk.CTkTextbox(right, width=360, height=400)
        self.detalle_txt.pack(fill='both', expand=True, padx=6, pady=6)

        # Footer: contador de cierres
        footer = ctk.CTkFrame(self)
        footer.pack(side='bottom', fill='x', padx=8, pady=(0,8))
        self.lbl_footer = ctk.CTkLabel(footer, text="Último Cierre: NINGUNO | Próximo Cierre será: Nº 1", anchor='w')
        self.lbl_footer.pack(side='left', padx=8)

        self.current_date = datetime.now().date().isoformat()
        self.lbl_fecha.configure(text=f"Día: {self.current_date}")

        # Service instance for centralized calculations
        try:
            self.cierre_service = CierreService()
        except Exception:
            self.cierre_service = None

        # actualizar footer y cargar tickets
        self._update_footer_cierre()
        self._load_tickets_since_last_cierre()

    def _get_last_cierre_id(self):
        # legacy: still available but prefer datetime-based last cierre
        conn = connect()
        cur = conn.cursor()
        try:
            # Prefer the `cierres_caja` sequence for last cierre id
            cur.execute('SELECT MAX(id) FROM cierres_caja')
            r = cur.fetchone()
            return r[0] if r and r[0] is not None else None
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

    def _get_last_cierre_datetime(self):
        """Return ISO datetime string of last cierre stored in `cierres_caja`, or None.

        Only reads from `cierres_caja`.
        """
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT MAX(fecha_hora) FROM cierres_caja")
            r = cur.fetchone()
            return r[0] if r and r[0] else None
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _get_next_cierre_num(self):
        conn = connect()
        cur = conn.cursor()
        try:
            # Use `cierres_caja` id sequence for the next cierre number
            cur.execute('SELECT MAX(id) FROM cierres_caja')
            r = cur.fetchone()
            last = r[0] if r and r[0] is not None else 0
            return int(last) + 1
        except Exception:
            return 1
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _update_footer_cierre(self):
        # Query cierres_caja for last id and fecha
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute("SELECT MAX(id), fecha_hora FROM cierres_caja")
            r = cur.fetchone()
            if r and r[0] is not None:
                last_id = r[0]
                # try to get fecha_hora for that id
                try:
                    cur.execute('SELECT fecha_hora FROM cierres_caja WHERE id=?', (last_id,))
                    fr = cur.fetchone()
                    fecha = fr[0] if fr and fr[0] else 'N/D'
                except Exception:
                    fecha = 'N/D'
                next_id = int(last_id) + 1
                text = f"Último Cierre: Nº {last_id} ({fecha}) | Próximo Cierre será: Nº {next_id}"
            else:
                text = "Último Cierre: NINGUNO | Próximo Cierre será: Nº 1"
        except Exception:
            text = "Último Cierre: NINGUNO | Próximo Cierre será: Nº 1"
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

        try:
            self.lbl_footer.configure(text=text)
        except Exception:
            pass

    def _load_tickets_since_last_cierre(self):
        # load tickets from last cierre Z datetime until now
        last_dt = self._get_last_cierre_datetime()
        now_dt = datetime.now().isoformat()
        conn = connect()
        cur = conn.cursor()
        try:
            if last_dt:
                cur.execute("SELECT id, created_at, ticket_no, cajero, cliente, total, forma_pago FROM tickets WHERE created_at > ? AND created_at <= ? ORDER BY created_at ASC", (last_dt, now_dt))
            else:
                cur.execute("SELECT id, created_at, ticket_no, cajero, cliente, total, forma_pago FROM tickets ORDER BY created_at ASC")
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
            tid, created_at, ticket_no, cajero, cliente, total, forma = r
            try:
                hora = datetime.fromisoformat(created_at).strftime('%H:%M:%S')
            except Exception:
                hora = created_at
            total_str = f"{(total or 0):.2f}"
            self.tree.insert('', 'end', iid=str(tid), values=(ticket_no or '', hora, cajero or '', cliente or '', total_str, forma or ''))

    def _on_ticket_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        tid = sel[0]
        self._load_ticket_detail(tid)

    def _load_ticket_detail(self, ticket_id):
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute('SELECT created_at, cajero, total, ticket_no, forma_pago, pagado, cambio, cliente FROM tickets WHERE id=? LIMIT 1', (ticket_id,))
            meta = cur.fetchone()
            cur.execute('SELECT sku, nombre, cantidad, precio, iva FROM ticket_lines WHERE ticket_id=? ORDER BY id ASC', (ticket_id,))
            rows = cur.fetchall()
        except Exception:
            meta = None
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

        header_lines = []
        header_lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
        header_lines.append("-"*30 + "\n")
        if meta:
            created_at = meta[0]
            cajero = meta[1]
            total = meta[2]
            ticket_no = meta[3]
            forma = meta[4]
            pagado = meta[5]
            cambio = meta[6]
            cliente = meta[7]
            try:
                if created_at:
                    header_lines.append(f"Fecha: {datetime.fromisoformat(created_at).strftime('%d/%m/%Y %H:%M')}\n")
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

        text = ''.join(header_lines) + ''.join(body_lines) + ''.join(totals_lines)
        self.detalle_txt.delete('0.0', 'end')
        try:
            self.detalle_txt.insert('end', text)
        except Exception:
            pass

    def _build_cierre_text(self, resumen, fecha, tipo='X'):
        lines = []
        def qty_str(q):
            try:
                if q is None:
                    return '0'
                if isinstance(q, float) and float(q).is_integer():
                    return str(int(q))
                return str(q)
            except Exception:
                return str(q)
        # Cabecera fiscal
        lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
        lines.append("="*40 + "\n")

        # Título y número
        numero = resumen.get('numero') or ''
        lines.append(f"CIERRE DE CAJA Nº {numero}   Tipo: {tipo}\n")
        lines.append(f"Fecha Consulta: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        lines.append("="*40 + "\n")

        # Resumen de ventas
        lines.append("RESUMEN DE VENTAS\n")
        lines.append(f"Facturas simplificadas: {resumen.get('count_tickets',0)}\n")
        lines.append(f"Total Ingresos: {float(resumen.get('total',0.0)):.2f}€\n")
        lines.append("-"*40 + "\n")

        # Desglose principal por tipo de pago (para cuadre rápido)
        lines.append("DESGLOSE PRINCIPAL DE PAGOS:\n")
        try:
            te = float(resumen.get('total_efectivo', 0.0) or 0.0)
            if te:
                lines.append(f"EFECTIVO: {te:.2f}€\n")
        except Exception:
            pass
        try:
            tt = float(resumen.get('total_tarjeta', 0.0) or 0.0)
            if tt:
                lines.append(f"TARJETA:  {tt:.2f}€\n")
        except Exception:
            pass
        try:
            tw = float(resumen.get('total_web', 0.0) or 0.0)
            if tw:
                lines.append(f"WEB:      {tw:.2f}€\n")
        except Exception:
            pass
        lines.append("-"*40 + "\n")

        # Medios de pago (detalle por forma)
        lines.append("DESGLOSE POR MEDIOS DE PAGO:\n")
        for p in resumen.get('por_forma_pago', []):
            forma = p.get('forma') or 'OTROS'
            try:
                total_fp = float(p.get('total', 0.0) or 0.0)
            except Exception:
                total_fp = 0.0
            lines.append(f"{forma}: {total_fp:.2f}€\n")
        lines.append("-"*40 + "\n")

        # Bloque de fidelización
        lines.append("--- RESUMEN FIDELIZACIÓN ---\n")
        try:
            puntos_ganados = float(resumen.get('puntos_ganados', 0.0) or 0.0)
        except Exception:
            puntos_ganados = 0.0
        try:
            puntos_canjeados = float(resumen.get('puntos_canjeados', 0.0) or 0.0)
        except Exception:
            puntos_canjeados = 0.0
        lines.append(f"Puntos Ganados hoy: {puntos_ganados:.2f}\n")
        lines.append(f"Puntos Canjeados hoy: {puntos_canjeados:.2f} pts\n")
        lines.append("-"*40 + "\n")

        # Desglose de impuestos
        lines.append("DESGLOSE DE IMPUESTOS (por tipo IVA):\n")
        lines.append("Base Imponible      Cuota IVA     Total\n")
        for imp in resumen.get('impuestos', []):
            iva = imp.get('iva',0)
            base = imp.get('base',0.0)
            cuota = imp.get('cuota',0.0)
            total = imp.get('total',0.0)
            lines.append(f"{str(iva)+'%':<6} {base:>10.2f}€ {cuota:>10.2f}€ {total:>10.2f}€\n")
        lines.append("-"*40 + "\n")

        # Estadísticas de personal
        lines.append("ESTADÍSTICAS DE PERSONAL:\n")
        for c in resumen.get('por_cajero', []):
            lines.append(f"{c.get('cajero')}: {c.get('total',0):.2f}€ ({c.get('count',0)} tickets)\n")
        lines.append(f"Aperturas de Cajón (sin venta): {resumen.get('aperturas_cajon_sin_venta',0)}\n")
        lines.append("-"*40 + "\n")

        # Bloques condicionales
        if resumen.get('por_categoria'):
            lines.append('\nRESUMEN CATEGORÍAS:\n')
            for c in resumen.get('por_categoria'):
                lines.append(f"{c.get('categoria')}: {qty_str(c.get('qty'))}  {c.get('total',0):.2f}€\n")

        if resumen.get('por_tipo'):
            lines.append('\nRESUMEN TIPOS:\n')
            for t in resumen.get('por_tipo'):
                lines.append(f"{t.get('tipo')}: {qty_str(t.get('qty'))}  {t.get('total',0):.2f}€\n")

        if resumen.get('por_articulo'):
            lines.append('\nRESUMEN ARTÍCULOS:\n')
            for a in resumen.get('por_articulo'):
                lines.append(f"{a.get('nombre')}: {qty_str(a.get('qty'))}  {a.get('total',0):.2f}€\n")

        return ''.join(lines)

    def _aggregate_for_selected(self):
        # build where clause based on last cierre datetime
        last_dt = self._get_last_cierre_datetime()
        now_dt = datetime.now().isoformat()
        conn = connect()
        cur = conn.cursor()
        try:
            if last_dt:
                where = "created_at > ? AND created_at <= ?"
                params = (last_dt, now_dt)
            else:
                where = "created_at <= ?"
                params = (now_dt,)

            # Try to include fidelity columns if present; fallback if table doesn't have them
            try:
                cur.execute(f"SELECT MIN(ticket_no), MAX(ticket_no), COUNT(*), COALESCE(SUM(total),0), COALESCE(SUM(puntos_ganados),0), COALESCE(SUM(puntos_canjeados),0) FROM tickets WHERE {where}", params)
                min_no, max_no, count_tickets, sum_total, sum_puntos_ganados, sum_puntos_canjeados = cur.fetchone()
            except Exception:
                cur.execute(f"SELECT MIN(ticket_no), MAX(ticket_no), COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {where}", params)
                min_no, max_no, count_tickets, sum_total = cur.fetchone()
                sum_puntos_ganados = 0.0
                sum_puntos_canjeados = 0.0

            cur.execute(f"SELECT forma_pago, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {where} GROUP BY forma_pago", params)
            pagos = [{"forma": r[0] or '', "count": r[1], "total": r[2] or 0.0} for r in cur.fetchall()]

            # Totales por forma de pago (EFECTIVO / TARJETA)
            try:
                cur.execute(f"SELECT COALESCE(SUM(total),0) FROM tickets WHERE {where} AND forma_pago = ?", params + ('EFECTIVO',))
                total_efectivo = float(cur.fetchone()[0] or 0.0)
            except Exception:
                total_efectivo = 0.0

            try:
                cur.execute(f"SELECT COALESCE(SUM(total),0) FROM tickets WHERE {where} AND forma_pago = ?", params + ('TARJETA',))
                total_tarjeta = float(cur.fetchone()[0] or 0.0)
            except Exception:
                total_tarjeta = 0.0
            # total for WEB payments
            try:
                cur.execute(f"SELECT COALESCE(SUM(total),0) FROM tickets WHERE {where} AND forma_pago = ?", params + ('WEB',))
                total_web = float(cur.fetchone()[0] or 0.0)
            except Exception:
                total_web = 0.0

            resumen = {
                'fecha_desde': last_dt,
                'fecha_hasta': now_dt,
                'tickets_from': min_no,
                'tickets_to': max_no,
                'count_tickets': count_tickets,
                'total': float(sum_total or 0.0),
                'por_forma_pago': pagos,
                'numero': self._get_next_cierre_num(),
                'puntos_ganados': float(sum_puntos_ganados or 0.0),
                'puntos_canjeados': float(sum_puntos_canjeados or 0.0),
                'total_efectivo': float(total_efectivo or 0.0),
                'total_tarjeta': float(total_tarjeta or 0.0),
                'total_web': float(total_web or 0.0),
            }

            # impuestos por tipo de IVA (usar el servicio centralizado si está disponible)
            try:
                desde_iso = last_dt if last_dt else '1970-01-01T00:00:00'
                hasta_iso = now_dt
                if self.cierre_service:
                    impuestos = self.cierre_service.desglose_impuestos_periodo(desde_iso, hasta_iso)
                else:
                    # fallback: compute here (legacy)
                    where_t = where.replace('created_at', 't.created_at')
                    cur.execute(f"SELECT tl.iva, COALESCE(SUM(tl.cantidad * tl.precio),0) as subtotal FROM ticket_lines tl JOIN tickets t ON tl.ticket_id = t.id WHERE {where_t} GROUP BY tl.iva", params)
                    impuestos = []
                    for iva_rate, subtotal in cur.fetchall():
                        try:
                            iva_f = float(iva_rate or 0.0)
                            subtotal_f = float(subtotal or 0.0)
                            divisor = 1 + (iva_f / 100.0) if iva_f != 0 else 1.0
                            base = subtotal_f / divisor
                            cuota = subtotal_f - base
                        except Exception:
                            base = 0.0
                            cuota = 0.0
                        impuestos.append({'iva': iva_f, 'base': base, 'cuota': cuota, 'total': subtotal_f})
                resumen['impuestos'] = impuestos
            except Exception:
                resumen['impuestos'] = []

            # ventas por cajero
            cur.execute(f"SELECT cajero, COUNT(*), COALESCE(SUM(total),0) FROM tickets WHERE {where} GROUP BY cajero", params)
            resumen['por_cajero'] = [{'cajero': r[0] or 'N/D', 'count': r[1], 'total': r[2]} for r in cur.fetchall()]

            # aperturas de cajón sin venta: no hay trazado en BD -> devolver 0
            resumen['aperturas_cajon_sin_venta'] = 0

            # condicionales: categorias, tipos, articulos
            # Use centralized service to obtain breakdowns for categories, types and articles
            try:
                desde_iso = last_dt if last_dt else '1970-01-01T00:00:00'
                hasta_iso = now_dt
                if self.cierre_service:
                    desglose = self.cierre_service.desglose_ventas(desde_iso, hasta_iso)
                    resumen['por_categoria'] = desglose.get('por_categoria') or []
                    resumen['por_tipo'] = desglose.get('por_tipo') or []
                    resumen['por_articulo'] = desglose.get('por_articulo') or []
                else:
                    # fallback to previous per-query calculations
                    if self.opt_cat.get():
                        cur.execute(f"""
                            SELECT COALESCE(p.categoria, ''), SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total
                            FROM ticket_lines tl
                            JOIN tickets t ON tl.ticket_id = t.id
                            JOIN productos p ON tl.sku = p.sku
                            WHERE {where_t}
                            GROUP BY p.categoria
                        """, params)
                        resumen['por_categoria'] = [{"categoria": r[0], "qty": r[1], "total": r[2]} for r in cur.fetchall()]

                    if self.opt_top.get():
                        cur.execute(f"""
                            SELECT COALESCE(p.tipo, ''), SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total
                            FROM ticket_lines tl
                            JOIN tickets t ON tl.ticket_id = t.id
                            JOIN productos p ON tl.sku = p.sku
                            WHERE {where_t}
                            GROUP BY p.tipo
                        """, params)
                        resumen['por_tipo'] = [{"tipo": r[0], "qty": r[1], "total": r[2]} for r in cur.fetchall()]

                    if self.opt_lines.get():
                        cur.execute(f"""
                            SELECT tl.nombre, SUM(tl.cantidad) as qty, SUM(tl.cantidad * tl.precio) as total
                            FROM ticket_lines tl
                            JOIN tickets t ON tl.ticket_id = t.id
                            WHERE {where_t}
                            GROUP BY tl.nombre
                            ORDER BY qty DESC
                        """, params)
                        resumen['por_articulo'] = [{"nombre": r[0], "qty": r[1], "total": r[2]} for r in cur.fetchall()]
            except Exception:
                resumen['por_categoria'] = resumen.get('por_categoria', [])
                resumen['por_tipo'] = resumen.get('por_tipo', [])
                resumen['por_articulo'] = resumen.get('por_articulo', [])

            return resumen
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

    def _on_consulta(self):
        resumen = self._aggregate_for_selected()
        if not resumen:
            _mb.showinfo('Consulta', 'No hay datos para este periodo')
            return
        text = self._build_cierre_text(resumen, self.current_date, tipo='X')
        try:
            self.detalle_txt.delete('0.0', 'end')
            self.detalle_txt.insert('end', text)
        except Exception:
            if preview_ticket is not None:
                try:
                    preview_ticket(self, text, modo='ventana')
                except Exception:
                    preview_ticket(None, text, modo='terminal')

    def _on_imprimir_cierre(self):
        try:
            texto = self.detalle_txt.get('0.0', 'end')
            impresion_service.imprimir_ticket(texto, abrir_cajon=True)
        except Exception as e:
            _mb.showerror('Impresión', f'Error imprimiendo: {e}')

    def _on_cierre_z(self):
        # Confirm, persist in `cierres_caja`, print and give feedback
        if not self.current_date:
            _mb.showinfo('Cierre', 'No hay fecha seleccionada')
            return

        # modal confirmation using CTkToplevel
        def do_confirm():
            # close the confirmation dialog and perform cierre sequence
            top.destroy()
            try:
                resumen = self._aggregate_for_selected()
                if not resumen:
                    _mb.showinfo('Cierre', 'No hay datos para este periodo')
                    return

                # Prevent performing a cierre when there are no tickets to close
                try:
                    if int(resumen.get('count_tickets', 0) or 0) <= 0:
                        _mb.showinfo('Cierre', 'No hay ventas abiertas para cerrar el día. Cierre no realizado.')
                        return
                except Exception:
                    # If count_tickets isn't numeric, treat as no tickets
                    _mb.showinfo('Cierre', 'No hay ventas abiertas para cerrar el día. Cierre no realizado.')
                    return

                # delegate persistence to central `close_day` (no direct DB access here)
                try:
                    cierre_cajero = self.cajero_activo.get('nombre') if getattr(self, 'cajero_activo', None) else None
                    resumen = close_day(fecha=self.current_date, tipo='Z', cajero=cierre_cajero)
                except Exception as e:
                    _mb.showerror('Error', f'Error ejecutando cierre: {e}')
                    return

                cierre_id = resumen.get('cierre_id') or resumen.get('numero')
                tipo = 'Z'
                text = self._build_cierre_text(resumen, self.current_date, tipo=tipo)

                # imprimir
                try:
                    impresion_service.imprimir_ticket(text, abrir_cajon=True)
                except Exception as e:
                    _mb.showerror('Impresión', f'Error imprimiendo: {e}')
                    return

                # feedback
                ts = datetime.now()
                _mb.showinfo('Cierre realizado', f"Cierre de caja Nº {cierre_id} efectuado el día {ts.strftime('%d/%m/%Y')} a la hora {ts.strftime('%H:%M')}")
                try:
                    # limpiar visor
                    self.detalle_txt.delete('0.0', 'end')
                except Exception:
                    pass

                # volver al menú anterior
                try:
                    self.controller.mostrar_ventas()
                except Exception:
                    pass
            except Exception as e:
                _mb.showerror('Error', f'Error ejecutando cierre: {e}')

        # show larger modal with next cierre number
        next_num = self._get_next_cierre_num()
        top = ctk.CTkToplevel(self)
        top.title('Confirmar Cierre')
        try:
            top.geometry('600x400')
            top.resizable(False, False)
        except Exception:
            pass
        top.transient(self)
        lbl_intro = ctk.CTkLabel(top, text=f"Va a cerrar el día {self.current_date}.", font=(None, 16))
        lbl_intro.pack(padx=16, pady=(16,6))
        lbl_num = ctk.CTkLabel(top, text=f"Próximo Cierre será: Nº {next_num}", font=(None, 20, 'bold'))
        lbl_num.pack(padx=16, pady=(6,12))
        lbl = ctk.CTkLabel(top, text="¿Está conforme?")
        lbl.pack(padx=16, pady=(6,12))
        frm = ctk.CTkFrame(top)
        frm.pack(padx=12, pady=12)
        btn_ok = ctk.CTkButton(frm, text='Sí, Imprimir', fg_color='#2E8B57', command=do_confirm, width=200, height=60, font=(None, 16, 'bold'))
        btn_ok.pack(side='left', padx=20)
        btn_cancel = ctk.CTkButton(frm, text='Cancelar', fg_color='#6c6c6c', command=top.destroy, width=200, height=60, font=(None, 16, 'bold'))
        btn_cancel.pack(side='left', padx=20)
        top.grab_set()
