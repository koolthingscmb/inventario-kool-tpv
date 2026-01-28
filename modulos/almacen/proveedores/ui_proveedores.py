import sqlite3
import customtkinter as ctk
from database import connect

class PantallaProveedores(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.pack(fill="both", expand=True)

        # Grid: left list (25%), right details (75%); bottom buttons
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)

        # Left: lista proveedores (scrollable)
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(10,6), pady=10)
        self.left_frame.grid_rowconfigure(0, weight=1)

        self.scroll_lista = ctk.CTkScrollableFrame(self.left_frame, fg_color="#121212")
        self.scroll_lista.grid(row=0, column=0, sticky="nsew")

        # Right: datos proveedor
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(6,10), pady=10)
        self.right_frame.grid_rowconfigure(0, weight=1)

        # Use the right area as the data container (no placeholder title)
        self.detalle_container = ctk.CTkFrame(self.right_frame, fg_color="#151515")
        self.detalle_container.pack(fill="both", expand=True, padx=6, pady=6)

        # Buttons area
        self.bot_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bot_frame.grid(row=1, column=0, columnspan=2, pady=(0,10))

        self.btn_crear = ctk.CTkButton(self.bot_frame, text="Crear Proveedor", width=160, command=self._crear_proveedor)
        self.btn_crear.pack(side="left", padx=8, pady=8)
        self.btn_borrar = ctk.CTkButton(self.bot_frame, text="Borrar Proveedor", width=160, fg_color="#AA3333", hover_color="#CC4444", command=self._borrar_proveedor)
        self.btn_borrar.pack(side="left", padx=8, pady=8)
        self.btn_volver = ctk.CTkButton(self.bot_frame, text="Volver", width=120, command=self.controller.mostrar_submenu_almacen)
        self.btn_volver.pack(side="right", padx=8, pady=8)

        # Internal state
        self.proveedores = []  # list of (id, nombre)
        self.selected_proveedor_id = None

        # Make right area wider by changing column weights: left 1, right 6
        try:
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=6)
        except Exception:
            pass

        self._cargar_lista_proveedores()

    def _cargar_lista_proveedores(self):
        # Clear current list
        for w in self.scroll_lista.winfo_children():
            w.destroy()
        self.proveedores = []
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre FROM proveedores ORDER BY nombre")
            rows = cursor.fetchall()
            for (pid, nombre) in rows:
                self.proveedores.append((pid, nombre))
                # Show ID alongside name in the list for clarity
                btn_text = f"{nombre} ({pid})"
                btn = ctk.CTkButton(self.scroll_lista, text=btn_text, anchor="w", width=200, command=lambda p=pid: self._select_proveedor(p))
                btn.pack(fill="x", padx=4, pady=2)
        except Exception:
            # If table does not exist or other DB issue, show placeholder
            lbl = ctk.CTkLabel(self.scroll_lista, text="No hay proveedores (tabla ausente)", text_color="gray")
            lbl.pack(padx=4, pady=4)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _select_proveedor(self, proveedor_id):
        self.selected_proveedor_id = proveedor_id
        # load details
        for w in self.detalle_container.winfo_children():
            w.destroy()
        try:
            # Render the same form used for creating providers, but in edit mode
            from modulos.almacen.proveedores.crear_proveedor import CrearProveedorForm
            CrearProveedorForm(self.detalle_container, self.controller, proveedores_page=self, proveedor_id=proveedor_id).render()
        except Exception:
            ctk.CTkLabel(self.detalle_container, text="No se pueden cargar datos", text_color="#ff3333").pack(padx=6, pady=6)

    def _crear_proveedor(self):
        # Open the crear proveedor form inside the detalle container
        try:
            from modulos.almacen.proveedores.crear_proveedor import CrearProveedorForm
            CrearProveedorForm(self.detalle_container, self.controller, proveedores_page=self).render()
        except Exception as e:
            print('Error mostrando crear proveedor:', e)

    def _editar_proveedor(self, proveedor_id):
        try:
            from modulos.almacen.proveedores.crear_proveedor import CrearProveedorForm
            CrearProveedorForm(self.detalle_container, self.controller, proveedores_page=self, proveedor_id=proveedor_id).render()
        except Exception as e:
            print('Error mostrando editor proveedor:', e)

    def _borrar_proveedor(self):
        if not self.selected_proveedor_id:
            return
        try:
            conn = connect()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM proveedores WHERE id = ?', (self.selected_proveedor_id,))
            conn.commit()
            conn.close()
            self.selected_proveedor_id = None
            self._cargar_lista_proveedores()
            for w in self.detalle_container.winfo_children():
                w.destroy()
            ctk.CTkLabel(self.detalle_container, text='Proveedor borrado', text_color='#ff3333').pack(padx=6, pady=6)
        except Exception as e:
            print('Error borrando proveedor:', e)
            try:
                conn.close()
            except Exception:
                pass
