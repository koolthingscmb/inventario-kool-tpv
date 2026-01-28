import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Dict, Any
import customtkinter as ctk

from modulos.configuracion.usuario_service import UsuarioService


class GestionUsuariosView(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.service = UsuarioService()
        self.selected_id: Optional[int] = None

        # Grid principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=20)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=80)

        # --- Panel izquierdo ---
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_panel.grid_rowconfigure(3, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.btn_back = ctk.CTkButton(self.left_panel, text="← Volver", command=self._on_volver)
        self.btn_back.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.btn_new = ctk.CTkButton(self.left_panel, text="➕ Nuevo Cajero", fg_color="#3498db", command=self._nuevo_cajero)
        self.btn_new.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        tree_frame = ctk.CTkFrame(self.left_panel)
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("nombre", "rol"), show="headings")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("rol", text="Rol")
        self.tree.column("nombre", anchor="w")
        self.tree.column("rol", width=100, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_select())

        # --- Separador ---
        linea = ctk.CTkFrame(self, width=2, fg_color="#444444")
        linea.grid(row=0, column=1, sticky="ns", pady=10)

        # --- Panel derecho ---
        self.right_panel = ctk.CTkFrame(self, fg_color="#f2f2f2")
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.right_panel, text="DATOS Y PERMISOS DEL CAJERO",
                                        font=("Arial", 22, "bold"), text_color="black")
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=20)

        self.placeholder = ctk.CTkLabel(self.right_panel, text="Seleccione un cajero de la lista",
                        font=("Arial", 16), text_color="black")
        self.placeholder.grid(row=1, column=0, sticky="nsew")

        # Formulario
        self.form_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self._build_form()
        self.form_frame.grid_remove()

        # Botones inferiores
        self.actions_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_save = ctk.CTkButton(self.actions_frame, text="Guardar Cambios", fg_color="#2ecc71",
                                      hover_color="#27ae60", command=self._guardar)
        self.btn_save.grid(row=0, column=0, padx=10, sticky="ew")

        self.btn_delete = ctk.CTkButton(self.actions_frame, text="Eliminar Cajero", fg_color="#e74c3c",
                                        command=self._eliminar_cajero)
        self.btn_delete.grid(row=0, column=1, padx=10, sticky="ew")

        self._load_users()

    def _build_form(self):
        inner = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10)
        inner.grid_columnconfigure((0, 1), weight=1)

        lbl_name = ctk.CTkLabel(inner, text="Nombre", text_color="black", font=("Arial", 13, "bold"))
        lbl_name.grid(row=0, column=0, sticky="w", padx=5, pady=(10, 0))
        self.entry_nombre = ctk.CTkEntry(inner, fg_color="white", text_color="black", border_color="#bdc3c7")
        self.entry_nombre.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))

        lbl_pwd = ctk.CTkLabel(inner, text="Password", text_color="black", font=("Arial", 13, "bold"))
        lbl_pwd.grid(row=0, column=1, sticky="w", padx=5, pady=(10, 0))
        self.entry_password = ctk.CTkEntry(inner, fg_color="white", text_color="black", border_color="#bdc3c7", show='*')
        self.entry_password.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))

        # Permisos frame
        perm_frame = ctk.CTkFrame(inner, fg_color="#e8e8e8")
        perm_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        perm_frame.grid_columnconfigure(0, weight=1)

        lbl_perm = ctk.CTkLabel(perm_frame, text="Permisos", text_color="black", font=("Arial", 14, "bold"))
        lbl_perm.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        # switches
        self.switch_es_admin = ctk.CTkSwitch(perm_frame, text="Es Admin", command=self._on_toggle_admin, text_color='black')
        self.switch_es_admin.grid(row=1, column=0, sticky="w", padx=20, pady=5)

        self.switch_cierre = ctk.CTkSwitch(perm_frame, text="Permiso Cierre", text_color='black')
        self.switch_cierre.grid(row=2, column=0, sticky="w", padx=20, pady=5)

        self.switch_descuento = ctk.CTkSwitch(perm_frame, text="Permiso Descuento", text_color='black')
        self.switch_descuento.grid(row=3, column=0, sticky="w", padx=20, pady=5)

        self.switch_devolucion = ctk.CTkSwitch(perm_frame, text="Permiso Devolución", text_color='black')
        self.switch_devolucion.grid(row=4, column=0, sticky="w", padx=20, pady=5)

        # permiso tickets
        self.switch_tickets = ctk.CTkSwitch(perm_frame, text="Permiso Tickets", text_color='black')
        self.switch_tickets.grid(row=5, column=0, sticky="w", padx=20, pady=5)

    def _load_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        usuarios = self.service.listar_usuarios()
        for u in usuarios:
            self.tree.insert("", "end", iid=str(u['id']), values=(u['nombre'], u.get('rol') or ''))

    def _on_select(self):
        sel = self.tree.selection()
        if sel:
            self.seleccionar_usuario(int(sel[0]))

    def seleccionar_usuario(self, uid: int):
        data = self.service.obtener_por_id(uid)
        if data:
            self.selected_id = uid
            self.placeholder.grid_remove()
            self.form_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
            self.entry_nombre.delete(0, tk.END)
            self.entry_nombre.insert(0, data.get('nombre') or '')
            # don't load password into field
            self.entry_password.delete(0, tk.END)

            is_admin = (str(data.get('rol') or '').lower() == 'admin')
            # set switches
            self.switch_es_admin.select() if is_admin else self.switch_es_admin.deselect()
            if is_admin:
                # mark all perms and disable them
                self.switch_cierre.select(); self.switch_descuento.select(); self.switch_devolucion.select()
                self.switch_tickets.select()
                self.switch_cierre.configure(state="disabled")
                self.switch_descuento.configure(state="disabled")
                self.switch_devolucion.configure(state="disabled")
                self.switch_tickets.configure(state="disabled")
            else:
                # enable switches and set according to DB
                try:
                    self.switch_cierre.configure(state="normal")
                    self.switch_descuento.configure(state="normal")
                    self.switch_devolucion.configure(state="normal")
                    self.switch_tickets.configure(state="normal")
                except Exception:
                    pass
                if data.get('permiso_cierre'):
                    self.switch_cierre.select()
                else:
                    self.switch_cierre.deselect()
                if data.get('permiso_descuento'):
                    self.switch_descuento.select()
                else:
                    self.switch_descuento.deselect()
                if data.get('permiso_devolucion'):
                    self.switch_devolucion.select()
                else:
                    self.switch_devolucion.deselect()
                if data.get('permiso_tickets'):
                    self.switch_tickets.select()
                else:
                    self.switch_tickets.deselect()

    def _nuevo_cajero(self):
        self.selected_id = None
        self.placeholder.grid_remove()
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.entry_nombre.delete(0, tk.END)
        self.entry_password.delete(0, tk.END)
        # reset switches and enable
        self.switch_es_admin.deselect()
        try:
            self.switch_cierre.configure(state="normal")
            self.switch_descuento.configure(state="normal")
            self.switch_devolucion.configure(state="normal")
            self.switch_tickets.configure(state="normal")
        except Exception:
            pass
        self.switch_cierre.deselect(); self.switch_descuento.deselect(); self.switch_devolucion.deselect()
        self.switch_tickets.deselect()

    def _on_toggle_admin(self):
        # if admin selected, mark all perms and disable them
        try:
            if self.switch_es_admin.get() == 1:
                self.switch_cierre.select(); self.switch_descuento.select(); self.switch_devolucion.select()
                self.switch_tickets.select()
                self.switch_cierre.configure(state="disabled")
                self.switch_descuento.configure(state="disabled")
                self.switch_devolucion.configure(state="disabled")
                self.switch_tickets.configure(state="disabled")
            else:
                self.switch_cierre.configure(state="normal")
                self.switch_descuento.configure(state="normal")
                self.switch_devolucion.configure(state="normal")
                self.switch_tickets.configure(state="normal")
        except Exception:
            pass

    def _guardar(self):
        nombre = self.entry_nombre.get().strip()
        pwd = self.entry_password.get()
        if not nombre:
            messagebox.showwarning('Atención', 'El nombre es obligatorio')
            return
        if self.selected_id is None and not pwd:
            messagebox.showwarning('Atención', 'La contraseña es obligatoria para un nuevo cajero')
            return

        datos: Dict[str, Any] = {}
        if self.selected_id is not None:
            datos['id'] = self.selected_id
        datos['nombre'] = nombre
        if pwd:
            datos['password'] = pwd

        # determine role from admin switch
        es_admin = bool(self.switch_es_admin.get())
        datos['rol'] = 'admin' if es_admin else 'empleado'

        datos['permiso_cierre'] = 1 if self.switch_cierre.get() else 0
        datos['permiso_descuento'] = 1 if self.switch_descuento.get() else 0
        datos['permiso_devolucion'] = 1 if self.switch_devolucion.get() else 0
        datos['permiso_tickets'] = 1 if self.switch_tickets.get() else 0

        res = self.service.guardar_usuario(datos)
        if res:
            messagebox.showinfo('Éxito', 'Usuario guardado correctamente')
            self._load_users()
            # select saved item
            try:
                self.tree.selection_set(str(res))
                self.tree.see(str(res))
            except Exception:
                pass
        else:
            messagebox.showerror('Error', 'No se pudo guardar el usuario')

    def _eliminar_cajero(self):
        if not self.selected_id:
            messagebox.showwarning('Atención', 'No hay ningún cajero seleccionado')
            return
        confirmar = messagebox.askyesno('Confirmar', '¿Deseas eliminar permanentemente este cajero?')
        if not confirmar:
            return
        ok = self.service.eliminar_usuario(self.selected_id)
        if ok:
            self._load_users()
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
            messagebox.showerror('Error', 'No se pudo eliminar el cajero')

    def _on_volver(self):
        if self.controller:
            try:
                self.controller.volver_a_configuracion()
            except Exception:
                pass
