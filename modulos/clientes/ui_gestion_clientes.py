import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Dict, Any
import customtkinter as ctk
import re

from modulos.clientes.cliente_service import ClienteService

class GestionClientesView(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.service = ClienteService()
        self.selected_id: Optional[int] = None

        # Configuración del Grid Principal (3 columnas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=35)  # Izquierda
        self.grid_columnconfigure(1, weight=0)   # Separador
        self.grid_columnconfigure(2, weight=65)  # Derecha

        # --- COLUMNA IZQUIERDA ---
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_panel.grid_rowconfigure(3, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.btn_back = ctk.CTkButton(self.left_panel, text="← Volver", command=self._on_volver)
        self.btn_back.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.left_panel, placeholder_text="Buscar cliente...")
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        self.btn_new = ctk.CTkButton(self.left_panel, text="➕ Nuevo Cliente", fg_color="#3498db", command=self._nuevo_cliente)
        self.btn_new.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # Lista de clientes (Treeview)
        tree_frame = ctk.CTkFrame(self.left_panel)
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("nombre", "telefono"), show="headings")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("telefono", text="Teléfono")
        self.tree.column("nombre", anchor="w")
        self.tree.column("telefono", width=100, anchor="w")
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_select())

        # --- SEPARADOR ---
        linea = ctk.CTkFrame(self, width=2, fg_color="#444444")
        linea.grid(row=0, column=1, sticky="ns", pady=10)

        # --- COLUMNA DERECHA ---
        self.right_panel = ctk.CTkFrame(self, fg_color="#f2f2f2") 
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1) 
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Título
        self.title_label = ctk.CTkLabel(self.right_panel, text="DATOS DEL CLIENTE", 
                                        font=("Arial", 22, "bold"), text_color="black")
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=20)

        # Placeholder
        self.placeholder = ctk.CTkLabel(self.right_panel, text="Seleccione un cliente de la lista", 
                                        font=("Arial", 16), text_color="gray")
        self.placeholder.grid(row=1, column=0, sticky="nsew")

        # Formulario (Scrollable)
        self.form_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self._build_form()
        self.form_frame.grid_remove() 

        # Botones de acción inferiores
        self.actions_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        # support three action buttons side-by-side
        self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_save = ctk.CTkButton(self.actions_frame, text="Guardar Cambios", fg_color="#2ecc71", 
                                      hover_color="#27ae60", command=self._guardar)
        self.btn_save.grid(row=0, column=0, padx=10, sticky="ew")

        self.btn_email = ctk.CTkButton(self.actions_frame, text="Enviar Email", fg_color="#95a5a6", 
                                       command=self._enviar_email)
        self.btn_email.grid(row=0, column=1, padx=10, sticky="ew")

        self.btn_delete = ctk.CTkButton(self.actions_frame, text="Eliminar Cliente", fg_color="#e74c3c", 
                        command=self._eliminar_cliente)
        self.btn_delete.grid(row=0, column=2, padx=10, sticky="ew")

        self._load_clients()

    def _build_form(self):
        self.entries = {}
        inner_container = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        inner_container.pack(fill="both", expand=True, padx=10)
        inner_container.grid_columnconfigure((0, 1), weight=1)

        def add_field(label, key, row, col, colspan=1):
            lbl = ctk.CTkLabel(inner_container, text=label, text_color="black", font=("Arial", 13, "bold"))
            lbl.grid(row=row, column=col, sticky="w", padx=5, pady=(10, 0))
            entry = ctk.CTkEntry(inner_container, fg_color="white", text_color="black", border_color="#bdc3c7")
            entry.grid(row=row+1, column=col, columnspan=colspan, sticky="ew", padx=5, pady=(0, 5))
            self.entries[key] = entry

        add_field("Nombre Completo", "nombre", 0, 0)
        add_field("DNI / CIF", "dni", 0, 1)
        add_field("Email", "email", 2, 0)
        add_field("Teléfono", "telefono", 2, 1)
        add_field("Dirección", "direccion", 4, 0, colspan=2)
        add_field("Ciudad", "ciudad", 6, 0)
        add_field("Código Postal", "cp", 6, 1)
        add_field("Etiquetas (Tags)", "tags", 8, 0, colspan=2)

        lbl_notas = ctk.CTkLabel(inner_container, text="Notas Internas", text_color="black", font=("Arial", 13, "bold"))
        lbl_notas.grid(row=10, column=0, sticky="w", padx=5, pady=(10, 0))
        self.text_notas = tk.Text(inner_container, height=5, bg="white", fg="black", font=("Arial", 12), relief="flat")
        self.text_notas.grid(row=11, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.points_frame = ctk.CTkFrame(inner_container, fg_color="#e1e1e1")
        self.points_frame.grid(row=12, column=0, columnspan=2, sticky="ew", padx=5, pady=15)
        self.lbl_puntos = ctk.CTkLabel(self.points_frame, text="Puntos de Fidelidad: 0.00", text_color="black", font=("Arial", 14, "bold"))
        self.lbl_puntos.pack(side="left", padx=20, pady=10)
        self.btn_mod_puntos = ctk.CTkButton(self.points_frame, text="Modificar Puntos", width=120, command=self._modificar_puntos)
        self.btn_mod_puntos.pack(side="right", padx=20, pady=10)

    def _load_clients(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        term = self.search_entry.get().strip()
        clientes = self.service.buscar_clientes(term) if term else self.service.obtener_todos()
        for c in clientes:
            self.tree.insert("", "end", iid=str(c['id']), values=(c['nombre'], c['telefono']))

    def _on_search(self):
        self._load_clients()

    def _on_select(self):
        sel = self.tree.selection()
        if sel: self.seleccionar_cliente(int(sel[0]))

    def seleccionar_cliente(self, cid):
        data = self.service.obtener_por_id(cid)
        if data:
            self.selected_id = cid
            self.placeholder.grid_remove()
            self.form_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
            for key, entry in self.entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(data.get(key) or ""))
            self.text_notas.delete("1.0", tk.END)
            self.text_notas.insert("1.0", data.get("notas_internas") or "")
            try:
                pval = float(data.get('puntos_fidelidad') or 0)
            except Exception:
                pval = 0.0
            self.lbl_puntos.configure(text=f"Puntos de Fidelidad: {pval:.2f}")

    def _nuevo_cliente(self):
        self.selected_id = None
        self.placeholder.grid_remove()
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        for entry in self.entries.values(): entry.delete(0, tk.END)
        self.text_notas.delete("1.0", tk.END)
        self.lbl_puntos.configure(text="Puntos de Fidelidad: 0.00")

    def _guardar(self):
        if not self.entries['nombre'].get():
            messagebox.showwarning("Atención", "El nombre es obligatorio")
            return
        datos = {k: e.get().strip() for k, e in self.entries.items()}
        datos["notas_internas"] = self.text_notas.get("1.0", tk.END).strip()
        if self.selected_id is None:
            res = self.service.crear_cliente(datos)
            if res: messagebox.showinfo("Éxito", "Cliente creado correctamente")
        else:
            res = self.service.actualizar_cliente(self.selected_id, datos)
            if res: messagebox.showinfo("Éxito", "Cliente actualizado correctamente")
        self._load_clients()

    def _modificar_puntos(self):
        if not self.selected_id: return
        puntos = ctk.CTkInputDialog(text="Puntos a sumar (o restar):", title="Puntos")
        val = puntos.get_input()
        if val:
            try:
                # accept comma as decimal separator
                cantidad = float(str(val).replace(',', '.'))
                self.service.sumar_puntos(self.selected_id, cantidad)
                self.seleccionar_cliente(self.selected_id)
            except Exception:
                messagebox.showerror("Error", "Introduce un número válido")

    def _eliminar_cliente(self):
        """Eliminar el cliente actualmente seleccionado tras confirmación."""
        if not self.selected_id:
            messagebox.showwarning('Atención', 'No hay ningún cliente seleccionado')
            return

        confirmar = messagebox.askyesno('Confirmar', '¿Deseas eliminar permanentemente este cliente?')
        if not confirmar:
            return

        try:
            ok = self.service.eliminar_cliente(self.selected_id)
            if ok:
                # refrescar lista y ocultar formulario
                self._load_clients()
                try:
                    self.form_frame.grid_remove()
                except Exception:
                    pass
                self.selected_id = None
                try:
                    self.placeholder.grid()
                except Exception:
                    pass
            else:
                messagebox.showerror('Error', 'No se pudo eliminar el cliente')
        except Exception:
            logging.exception('Error eliminando cliente id=%s', self.selected_id)
            messagebox.showerror('Error', 'Error al eliminar el cliente')

    def _enviar_email(self):
        email = self.entries['email'].get()
        if email: messagebox.showinfo("Email", f"Abriendo gestor para: {email}")
        else: messagebox.showwarning("Atención", "El cliente no tiene email")

    def _on_volver(self):
        if self.controller: self.controller.mostrar_inicio()