import logging
import customtkinter as ctk
import os
from datetime import datetime, timedelta
from tkinter import messagebox
from tkinter.filedialog import asksaveasfilename
from typing import List, Optional

from modulos.tpv.cierre_service import CierreService
from modulos.exportar_importar.exportar_service import ExportarService
from modulos.impresion.print_service import ImpresionService

# instancia compartida de impresión
impresion_service = ImpresionService()

class HistoricoCierresView(ctk.CTkFrame):
    """Vista histórica de cierres; utiliza exclusivamente CierreService (sin SQL)."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.controller = controller
        self.cierre_service = CierreService()
        self.cierres_encontrados: List[dict] = []
        self._selected_cierre_date: Optional[str] = None

        # Layout: left 20% filters+list, right 80% detalle
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        left = ctk.CTkFrame(main, width=260)
        left.pack(side="left", fill="y", padx=(0, 12), pady=6)
        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True, pady=6)

        # Header
        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", padx=8, pady=8)
        ctk.CTkButton(header, text="← Volver", width=100, command=lambda: self.controller.mostrar_cierre_caja()).pack(side="right", padx=6)
        ctk.CTkLabel(header, text="HISTÓRICO DE CIERRES", font=(None, 18, "bold")).pack(pady=(4, 0))

        # Filters
        frm_filters = ctk.CTkFrame(left)
        frm_filters.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(frm_filters, text="Desde (YYYY-MM-DD)").pack(anchor="w", padx=6, pady=(6, 0))
        self.ent_desde = ctk.CTkEntry(frm_filters, width=220)
        self.ent_desde.pack(padx=6, pady=(0, 6))
        ctk.CTkLabel(frm_filters, text="Hasta (YYYY-MM-DD)").pack(anchor="w", padx=6)
        self.ent_hasta = ctk.CTkEntry(frm_filters, width=220)
        self.ent_hasta.pack(padx=6, pady=(0, 6))
        ctk.CTkButton(frm_filters, text="🔍 Buscar", command=self._on_search).pack(padx=6, pady=(6, 8))

        # Results list
        ctk.CTkLabel(left, text="Resultados").pack(anchor="w", padx=6)
        self._list_rows_container = ctk.CTkScrollableFrame(left, width=240, height=420)
        self._list_rows_container.pack(fill="both", expand=True, padx=6, pady=6)

        # Right: detail textbox + buttons
        self.detalle_txt = ctk.CTkTextbox(right, width=720, height=520)
        try:
            self.detalle_txt.configure(font=("Courier", 16), fg_color="black", text_color="white")
        except Exception:
            pass
        self.detalle_txt.pack(fill="both", expand=True, padx=6, pady=6)

        btns = ctk.CTkFrame(right)
        btns.pack(fill="x", pady=6)
        self.btn_reimprimir = ctk.CTkButton(btns, text="🖨️ REIMPRIMIR TICKET", state="disabled", command=self._on_reimprimir)
        self.btn_reimprimir.pack(side="left", padx=8)
        # Exportar CSV: funcionalidad centralizada en ExportarService.
        # TODO: integrar con `modulos.exportar_importar.exportar_service.ExportarService`
        self.btn_export = ctk.CTkButton(btns, text="📄 EXPORTAR CSV", state="disabled", command=self._on_export_csv)
        self.btn_export.pack(side="left", padx=8)
        self.btn_export_pdf = ctk.CTkButton(btns, text="📕 EXPORTAR PDF", state="disabled", command=self._on_export_pdf)
        self.btn_export_pdf.pack(side="left", padx=8)
        # Export ventas por cajero
        self.btn_export_cajero_csv = ctk.CTkButton(btns, text="📄 EXPORTAR POR CAJERO (CSV)", state="disabled", command=self._on_export_cajero_csv)
        self.btn_export_cajero_csv.pack(side="left", padx=8)
        try:
            self.btn_export_cajero_pdf = ctk.CTkButton(btns, text="📕 EXPORTAR POR CAJERO (PDF)", state="disabled", command=self._on_export_cajero_pdf)
            self.btn_export_cajero_pdf.pack(side="left", padx=8)
        except Exception:
            self.btn_export_cajero_pdf = None
        self.btn_ver_tickets = ctk.CTkButton(btns, text="🔍 VER TICKETS DEL DÍA", state="disabled", command=self._on_ver_tickets)
        self.btn_ver_tickets.pack(side="left", padx=8)

        # Bind Enter keys
        self.ent_desde.bind("<Return>", lambda e: self._on_search())
        self.ent_hasta.bind("<Return>", lambda e: self._on_search())

        self._load_initial()

    def _load_initial(self):
        hasta = datetime.now().date()
        desde = hasta - timedelta(days=30)
        self.ent_desde.delete(0, "end")
        self.ent_desde.insert(0, desde.isoformat())
        self.ent_hasta.delete(0, "end")
        self.ent_hasta.insert(0, hasta.isoformat())
        self._query_and_populate(desde.isoformat(), hasta.isoformat())

    def _valid_date(self, s: str) -> bool:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except:
            return False

    def _on_search(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            messagebox.showerror("Fecha", "Formato de fecha inválido. Use YYYY-MM-DD")
            return
        self._query_and_populate(d, h)

    def _query_and_populate(self, desde: str, hasta: str):
        try:
            rows = self.cierre_service.listar_cierres_periodo(desde, hasta) or []
            self.cierres_encontrados = rows
            for w in self._list_rows_container.winfo_children(): w.destroy()

            for r in rows:
                cid = r.get("id")
                fecha_hora = r.get("fecha_hora")
                total_ing = float(r.get("total_ingresos") or 0.0)
                label = f"{cid}  {str(fecha_hora).split('T')[0]}  {total_ing:.2f}€"
                btn = ctk.CTkButton(self._list_rows_container, text=label, anchor="w", command=lambda _id=cid: self._on_select(_id))
                btn.pack(fill="x", pady=2, padx=2)

            state = "normal" if rows else "disabled"
            self.btn_reimprimir.configure(state=state)
            # keep export button enabled/disabled for parity; command shows TODO
            self.btn_export.configure(state=state)
            try:
                self.btn_export_pdf.configure(state=state)
            except Exception:
                pass
            try:
                self.btn_export_cajero_csv.configure(state=state)
            except Exception:
                pass
            try:
                if self.btn_export_cajero_pdf:
                    self.btn_export_cajero_pdf.configure(state=state)
            except Exception:
                pass
            
            # Resumen rápido en el visor
            total_sum = sum(float(r.get("total_ingresos") or 0.0) for r in rows)
            self.detalle_txt.delete("0.0", "end")
            self.detalle_txt.insert("end", f"Cierres: {len(rows)}\nTotal ingresos: {total_sum:.2f} €\n")

            # Mostrar ventas por cajero para el periodo
            try:
                ventas = self.cierre_service.ventas_por_cajero(desde, hasta) or []
                self.detalle_txt.insert("end", "\nVENTAS POR CAJERO:\n")
                self.detalle_txt.insert("end", f"{'Cajero':<20} {'ID':>6} {'Total':>12}\n")
                self.detalle_txt.insert("end", "-" * 40 + "\n")
                for v in ventas:
                    nombre = (v.get('nombre') or '')[:20]
                    cid = str(v.get('cajero_id') or 'N/A')
                    total = float(v.get('total_ventas') or 0.0)
                    self.detalle_txt.insert("end", f"{nombre:<20} {cid:>6} {total:>12.2f}€\n")
                if not ventas:
                    self.detalle_txt.insert("end", "(Sin ventas por cajero en el periodo)\n")
            except Exception:
                logging.exception('Error mostrando ventas por cajero en UI')
        except Exception:
            logging.exception("Error en _query_and_populate")

    def _on_select(self, cierre_id):
        detalle = self.cierre_service.obtener_detalle_cierre(cierre_id)
        if not detalle: return

        # --- CONFIGURACIÓN DEL MOLDE (30 CARACTERES) ---
        lines = []
        lines.append("KOOL DREAMS\nC/Juan Sebastián Elcano, 2\n43850 Cambrils\nNIF: 39887072N\n")
        lines.append("-" * 30 + "\n")
        lines.append(f"CIERRE Nº: {detalle.get('id')}\n")
        
        try:
            fecha_dt = datetime.fromisoformat(detalle.get('fecha_hora'))
            lines.append(f"Fecha: {fecha_dt.strftime('%d/%m/%Y %H:%M')}\n")
        except:
            lines.append(f"Fecha: {detalle.get('fecha_hora')}\n")
            
        lines.append(f"Cajero: {detalle.get('cajero') or ''}\n")
        lines.append("-" * 30 + "\n")

        # --- RESUMEN ECONÓMICO ---
        total = float(detalle.get('total_ingresos') or 0.0)
        lines.append(f"TOTAL INGRESOS: {total:>10.2f}€\n")
        lines.append(f"Efectivo:      {float(detalle.get('total_efectivo') or 0.0):>10.2f}€\n")
        lines.append(f"Tarjeta:       {float(detalle.get('total_tarjeta') or 0.0):>10.2f}€\n")
        lines.append(f"Web:           {float(detalle.get('total_web') or 0.0):>10.2f}€\n")
        
        # --- FIDELIZACIÓN (Molde de 20 caracteres como en Ventas) ---
        lines.append("\n" + "-" * 20 + "\n")
        lines.append(f"Puntos ganados: {float(detalle.get('puntos_ganados') or 0.0):>10.2f}\n")
        lines.append(f"Puntos canjeados: -{float(detalle.get('puntos_canjeados') or 0.0):>8.2f}\n")
        lines.append("-" * 30 + "\n")

        # --- DESGLOSES (Categorías, Tipos, Artículos) ---
        def add_block(titulo, lista, clave_nom):
            if lista:
                lines.append(f"\n{titulo}:\n")
                for it in lista:
                    nom = it.get(clave_nom)[:18]
                    qty = int(it.get('qty') or 0)
                    val = float(it.get('total') or 0.0)
                    lines.append(f"{nom:<18} {qty:>2} {val:>7.2f}€\n")
                lines.append("-" * 30 + "\n")

        add_block("POR CATEGORÍAS", detalle.get('por_categoria'), 'categoria')
        add_block("POR TIPOS", detalle.get('por_tipo'), 'tipo')
        add_block("TOP 10 ARTÍCULOS", detalle.get('por_articulo'), 'nombre')

        # --- DESGLOSE FIDELIZACIÓN ---
        try:
            from modulos.tpv.fidelizacion_service import FidelizacionService
            fid = FidelizacionService()
            # use cierre date as period (day)
            fecha = str(detalle.get('fecha_hora')).split('T')[0]
            puntos = fid.desglose_puntos_periodo(fecha, fecha)
            lines.append('\nPUNTOS OTORGADOS: ' + f"{puntos.get('puntos_otorgados',0):.2f}\n")
            for c in puntos.get('clientes_otorgados', []):
                lines.append(f"  {c.get('nombre','')[:18]:<18} {c.get('cliente_id') or '':>4} {c.get('puntos',0):>8.2f} pts\n")
            lines.append('\nPUNTOS GASTADOS: ' + f"{puntos.get('puntos_gastados',0):.2f}\n")
            for c in puntos.get('clientes_gastados', []):
                lines.append(f"  {c.get('nombre','')[:18]:<18} {c.get('cliente_id') or '':>4} {c.get('puntos',0):>8.2f} pts\n")
            lines.append('-' * 30 + "\n")
        except Exception:
            pass

        lines.append("\n¡Gracias por tu confianza!\n")

        self.detalle_txt.delete("0.0", "end")
        self.detalle_txt.insert("end", "".join(lines))
        
        self._selected_cierre_date = str(detalle.get('fecha_hora')).split('T')[0]
        try:
            self.btn_ver_tickets.configure(state="normal")
        except Exception:
            pass

    def _on_ver_tickets(self):
        if self._selected_cierre_date:
            self.controller.mostrar_tickets(self._selected_cierre_date, retorno_historico=True)

    def _on_reimprimir(self):
        text = self.detalle_txt.get("0.0", "end")
        if text.strip():
            try:
                impresion_service.imprimir_ticket(text, abrir_cajon=True)
            except Exception:
                # fallback: show preview or print to console
                try:
                    print('\n[RE-IMPRESIÓN FALLBACK]')
                    print(text)
                except Exception:
                    pass

    def _on_export_csv(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            messagebox.showerror("Fecha", "Formato de fecha inválido. Use YYYY-MM-DD")
            return
        svc = ExportarService()
        initial = f"ventas_{d}_a_{h}.csv"
        path = asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile=initial)
        if not path:
            return
        ok = svc.exportar_desglose_ventas_csv(path, d + 'T00:00:00', h + 'T23:59:59')
        if ok:
            messagebox.showinfo('Exportar', f'CSV exportado: {path}')
        else:
            messagebox.showerror('Exportar', 'Error al exportar CSV')

    def _on_export_pdf(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            messagebox.showerror("Fecha", "Formato de fecha inválido. Use YYYY-MM-DD")
            return
        svc = ExportarService()
        initial = f"ventas_{d}_a_{h}.pdf"
        path = asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF','*.pdf')], initialfile=initial)
        if not path:
            return
        ok = svc.exportar_desglose_ventas_pdf(path, d + 'T00:00:00', h + 'T23:59:59')
        if ok:
            messagebox.showinfo('Exportar', f'PDF exportado: {path}')
        else:
            messagebox.showerror('Exportar', 'Error al exportar PDF')

    def _on_export_cajero_csv(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            messagebox.showerror("Fecha", "Formato de fecha inválido. Use YYYY-MM-DD")
            return
        svc = ExportarService()
        initial = f"ventas_por_cajero_{d}_a_{h}.csv"
        path = asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile=initial)
        if not path:
            return
        ok = svc.exportar_ventas_por_cajero_csv(path, d + 'T00:00:00', h + 'T23:59:59')
        if ok:
            messagebox.showinfo('Exportar', f'CSV exportado: {path}')
        else:
            messagebox.showerror('Exportar', 'Error al exportar CSV')

    def _on_export_cajero_pdf(self):
        d = self.ent_desde.get().strip()
        h = self.ent_hasta.get().strip()
        if not (self._valid_date(d) and self._valid_date(h)):
            messagebox.showerror("Fecha", "Formato de fecha inválido. Use YYYY-MM-DD")
            return
        svc = ExportarService()
        initial = f"ventas_por_cajero_{d}_a_{h}.pdf"
        path = asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF','*.pdf')], initialfile=initial)
        if not path:
            return
        ok = svc.exportar_ventas_por_cajero_pdf(path, d + 'T00:00:00', h + 'T23:59:59')
        if ok:
            messagebox.showinfo('Exportar', f'PDF exportado: {path}')
        else:
            messagebox.showerror('Exportar', 'Error al exportar PDF')

    # Export CSV removed from UI; TODO integrate with ExportarService