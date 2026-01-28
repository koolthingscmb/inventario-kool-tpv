import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Optional, Dict, Any, List

from modulos.clientes.cliente_service import ClienteService


class SelectorCliente(ctk.CTkToplevel):
    """Ventana modal para seleccionar un cliente.

    Uso típico:
        selector = SelectorCliente(parent)
        parent.wait_window(selector)
        cliente = selector.result  # dict o None
    """

    def __init__(self, master=None, titulo: str = "Seleccionar cliente"):
        super().__init__(master)
        self.title(titulo)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        self._service = ClienteService()
        self.result: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._populate([])

    def _build_ui(self):
        pad = 8
        self.columnconfigure(0, weight=1)

        # Contenedor principal
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=pad, pady=pad)
        frame.columnconfigure(0, weight=1)

        # Barra de búsqueda
        search_frame = ctk.CTkFrame(frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew")
        search_frame.columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(search_frame, text="Buscar:")
        lbl.grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.var_search = tk.StringVar()
        entry = ctk.CTkEntry(search_frame, textvariable=self.var_search, width=320)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<KeyRelease>", self._on_search_change)

        btn_search = ctk.CTkButton(search_frame, text="Buscar", width=90, command=self._on_search)
        btn_search.grid(row=0, column=2, sticky="e", padx=(6, 0))

        # Treeview
        tree_frame = ttk.Frame(frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("nombre", "telefono", "dni")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("telefono", text="Teléfono")
        self.tree.heading("dni", text="DNI")
        self.tree.column("nombre", width=260, anchor="w")
        self.tree.column("telefono", width=120, anchor="center")
        self.tree.column("dni", width=120, anchor="center")
        self.tree.bind("<Double-1>", self._on_double_click)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        btn_frame.columnconfigure((0, 1, 2), weight=1)

        self.btn_select = ctk.CTkButton(btn_frame, text="Seleccionar", command=self._on_select)
        self.btn_select.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_cancel = ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#888888", hover_color="#777777", command=self._on_cancel)
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(6, 6))

        # Ajuste visual compacto
        for child in frame.winfo_children():
            try:
                child.configure(padx=0, pady=0)
            except Exception:
                pass

    def _on_search_change(self, event=None):
        # Llamada rápida al teclear; no complicada gestión de debounce para mantener simple
        self._on_search()

    def _on_search(self):
        termino = self.var_search.get().strip()
        try:
            results = self._service.buscar_clientes(termino)
        except Exception:
            results = []
        self._populate(results)

    def _populate(self, items: List[Dict[str, Any]]):
        # Limpiar
        for r in self.tree.get_children():
            self.tree.delete(r)

        for it in items:
            display = (
                it.get("nombre") or "",
                it.get("telefono") or "",
                it.get("dni") or "",
            )
            # guardamos id en iid para recuperar luego
            iid = str(it.get("id") or "")
            self.tree.insert("", "end", iid=iid, values=display)

    def _get_selected_item(self) -> Optional[Dict[str, Any]]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        try:
            cliente_id = int(iid)
        except Exception:
            return None
        return self._service.obtener_por_id(cliente_id)

    def _on_double_click(self, event=None):
        self._on_select()

    def _on_select(self):
        cliente = self._get_selected_item()
        if cliente is None:
            return
        self.result = cliente
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


if __name__ == "__main__":
    # Pequeña prueba manual
    root = ctk.CTk()
    root.geometry("640x320")
    def abrir():
        s = SelectorCliente(root)
        root.wait_window(s)
        print("Resultado:", s.result)

    btn = ctk.CTkButton(root, text="Abrir selector", command=abrir)
    btn.pack(padx=20, pady=20)
    root.mainloop()
