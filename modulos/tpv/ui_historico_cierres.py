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
        ctk.CTkLabel(frm_filters, text='Hasta (YYYY-MM-DD)').pack(anchor='w', padx=6)
        self.ent_hasta = ctk.CTkEntry(frm_filters, width=180)
        self.ent_hasta.pack(padx=6, pady=(0,6))
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
        btns = ctk.CTkFrame(right)
        btns.pack(fill='x', pady=6)
        self.btn_reimprimir = ctk.CTkButton(btns, text='🖨️ REIMPRIMIR TICKET', state='disabled', command=self._on_reimprimir)
        self.btn_reimprimir.pack(side='left', padx=8)
        self.btn_export = ctk.CTkButton(btns, text='📄 EXPORTAR CSV', state='disabled', command=self._on_export_csv)
        self.btn_export.pack(side='left', padx=8)

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
            cur.execute("SELECT id, fecha_hora, total_ingresos, num_ventas, cajero FROM cierres_caja WHERE date(fecha_hora) BETWEEN ? AND ? ORDER BY fecha_hora DESC", (desde, hasta))
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

        total_sum = 0.0
        total_ventas = 0
        for r in rows:
            cid, fecha_hora, total_ing, num_ventas, cajero = r
            total_sum += float(total_ing or 0.0)
            total_ventas += int(num_ventas or 0)
            item = ctk.CTkButton(self._list_rows_container, text=f"{cid}    {fecha_hora.split('T')[0]}    {float(total_ing or 0.0):.2f}€", anchor='w', command=lambda _id=cid: self._on_select(_id))
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

        # show summary global in detalle
        summary = f"Resumen periodo: {len(rows)} cierres\nTotal ingresos: {total_sum:.2f}€\nTotal ventas: {total_ventas}\n"
        try:
            # configure visor: monospaced font and dark background if possible
            try:
                self.detalle_txt.configure(font=('Courier', 11), fg_color='black', text_color='white')
            except Exception:
                pass
            self.detalle_txt.delete('0.0', 'end')
            self.detalle_txt.insert('end', summary)
        except Exception:
            pass

    def _on_select(self, cierre_id):
        conn = connect()
        cur = conn.cursor()
        try:
            cur.execute('SELECT id, fecha_hora, total_ingresos, num_ventas, cajero FROM cierres_caja WHERE id=? LIMIT 1', (cierre_id,))
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
        cid, fecha_hora, total_ing, num_ventas, cajero = r
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
        lines.append(f"Total Ingresos: {float(total_ing or 0.0):.2f}€\n")
        lines.append(f"Número de ventas: {num_ventas or 0}\n")
        text = ''.join(lines)
        try:
            try:
                self.detalle_txt.configure(font=('Courier', 11), fg_color='black', text_color='white')
            except Exception:
                pass
            self.detalle_txt.delete('0.0', 'end')
            self.detalle_txt.insert('end', text)
        except Exception:
            pass

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
                # write header
                fh.write('ID Cierre;Fecha;Hora;Importe Total;Nº Ventas;Cajero\n')
                for cid, fecha_hora, total_ing, num_ventas, cajero in rows:
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
                    line = f"{cid};{fecha};{hora};{importe};{num_ventas or 0};{(cajero or '')}\n"
                    fh.write(line)
            messagebox.showinfo('Exportar', f'Exportado a {fpath}')
        except Exception as e:
            messagebox.showerror('Exportar', f'Error exportando CSV: {e}')
