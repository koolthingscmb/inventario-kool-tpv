import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from modulos.exportar_importar.exportar_service import ExportarService
from datetime import datetime
exportador = None

class DialogExportArticulos(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Exportar Artículos')
        self.geometry('700x500')
        self.parent = parent

        # filtros
        frame_filters = ctk.CTkFrame(self)
        frame_filters.pack(fill='x', padx=10, pady=10)

        ctk.CTkLabel(frame_filters, text='Buscar nombre o SKU:', anchor='w').pack(anchor='w')
        self.entry_search = ctk.CTkEntry(frame_filters)
        self.entry_search.pack(fill='x', pady=4)

        ctk.CTkLabel(frame_filters, text='Categorías (selecciona):', anchor='w').pack(anchor='w', pady=(8,0))
        self.cats_frame = ctk.CTkFrame(self)
        self.cats_frame.pack(fill='both', expand=True, padx=10, pady=4)

        # carga categorías
        self.cat_vars = []
        if exportador:
            cats = exportador.listar_categorias()
        else:
            cats = []  # exportador removed; categories will be provided by ExportarService in future
        for i, c in enumerate(cats):
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(self.cats_frame, text=c, variable=var, anchor='w')
            cb.pack(anchor='w')
            self.cat_vars.append((c, var))

        # botones
        frame_btns = ctk.CTkFrame(self)
        frame_btns.pack(fill='x', padx=10, pady=10)
        ctk.CTkButton(frame_btns, text='Seleccionar todo', command=self._select_all).pack(side='left', padx=6)
        ctk.CTkButton(frame_btns, text='Limpiar', command=self._clear_all).pack(side='left', padx=6)
        ctk.CTkButton(frame_btns, text='Dry-run (contar)', fg_color='#3399FF', command=self._dry_run).pack(side='right', padx=6)
        ctk.CTkButton(frame_btns, text='Exportar CSV', fg_color='green', command=self._export).pack(side='right', padx=6)

    def _select_all(self):
        for _, v in self.cat_vars:
            v.set(1)

    def _clear_all(self):
        for _, v in self.cat_vars:
            v.set(0)

    def _gather_filters(self):
        cats = [c for c,v in self.cat_vars if v.get()]
        s = self.entry_search.get().strip()
        return cats or None, s or None

    def _dry_run(self):
        cats, s = self._gather_filters()
        svc = ExportarService()
        rows = svc.exportar_articulos_csv(nombre_archivo=None, categorias=cats, search=s, dry_run=True)
        messagebox.showinfo('Dry-run', f'Se exportarían {len(rows)} filas (máx 10000).')

    def _export(self):
        cats, s = self._gather_filters()
        svc = ExportarService()
        # pedir ruta al usuario
        from tkinter import filedialog
        today = datetime.now().date().isoformat()
        default_name = f"articulos_{today}_a_{today}.csv"
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV','*.csv')], initialfile=default_name)
        if not path:
            return
        ok = svc.exportar_articulos_csv(nombre_archivo=path, categorias=cats, search=s, dry_run=False)
        if ok:
            messagebox.showinfo('Exportado', f'CSV guardado en: {path}')
        else:
            messagebox.showerror('Exportado', 'Error exportando CSV. Revisa logs.')
