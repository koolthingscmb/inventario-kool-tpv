import customtkinter as ctk
import sqlite3
from database import connect
from tkinter import messagebox

# --- CLASE PRINCIPAL DEL MENÚ ALMACÉN ---
class MenuAlmacen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # Este frame es solo un contenedor lógico para las herramientas de almacén
        # Realmente el menú se dibuja en el HUB, pero aquí pondremos las pantallas
        # específicas como "Añadir Producto", "Ver Lista", etc.
    
    # Aquí iremos añadiendo las pantallas de Proveedores, Albaranes, etc.

# --- PANTALLA ANTIGUA DE AÑADIR/VER PRODUCTOS ---
class PantallaGestionArticulos(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # BARRA LATERAL
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.btn_volver = ctk.CTkButton(self.sidebar, text="⬅ Volver al Inicio", 
                                        fg_color="transparent", border_width=1,
                                        command=self.controller.mostrar_inicio)
        self.btn_volver.pack(pady=20, padx=20)

        ctk.CTkLabel(self.sidebar, text="AÑADIR PRODUCTO", font=("Arial", 16, "bold")).pack(pady=10)
        self.entry_nombre = ctk.CTkEntry(self.sidebar, placeholder_text="Nombre")
        self.entry_nombre.pack(pady=5, padx=20)
        self.entry_sku = ctk.CTkEntry(self.sidebar, placeholder_text="SKU")
        self.entry_sku.pack(pady=5, padx=20)
        self.entry_stock = ctk.CTkEntry(self.sidebar, placeholder_text="Stock")
        self.entry_stock.pack(pady=5, padx=20)
        
        self.btn_guardar = ctk.CTkButton(self.sidebar, text="Guardar", command=self.guardar_producto)
        self.btn_guardar.pack(pady=20, padx=20)

        # Botón para gestionar Categoría & Tipo (placeholder)
        self.btn_categoria_tipo = ctk.CTkButton(self.sidebar, text="Categoría & Tipo", fg_color="#5A9BD5", command=self.abrir_categoria_tipo)
        self.btn_categoria_tipo.pack(pady=6, padx=20)

        # ZONA DERECHA
        self.main_content = ctk.CTkFrame(self)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.main_content, text="LISTADO DE STOCK", font=("Arial", 20, "bold")).pack(pady=10)
        self.btn_consultar = ctk.CTkButton(self.main_content, text="🔄 Actualizar Lista", command=self.consultar_db)
        self.btn_consultar.pack(pady=10)
        self.resultado_texto = ctk.CTkTextbox(self.main_content, width=500, height=400)
        self.resultado_texto.pack(pady=10, padx=10)

    def guardar_producto(self):
        nombre = self.entry_nombre.get()
        sku = self.entry_sku.get()
        stock = self.entry_stock.get()
        if nombre and sku:
            conn = connect()
            cursor = conn.cursor()
            try:
                # Nota: Volvemos a la versión simple sin IVA por ahora para evitar errores si no actualizaste la DB
                # Si ya la actualizaste, avísame y ponemos aquí el campo IVA
                cursor.execute("INSERT INTO productos (nombre, sku, stock_local) VALUES (?, ?, ?)", 
                               (nombre, sku, int(stock) if stock else 0))
                conn.commit()
                self.entry_nombre.delete(0, 'end')
                self.entry_sku.delete(0, 'end')
                self.entry_stock.delete(0, 'end')
                self.consultar_db()
            except Exception as e:
                print(f"Error: {e}")
            finally:
                conn.close()

    def consultar_db(self):
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, sku, stock_local FROM productos")
        productos = cursor.fetchall()
        conn.close()
        self.resultado_texto.delete("0.0", "end")
        for p in productos:
            self.resultado_texto.insert("end", f"📦 {p[0]} | SKU: {p[1]} | Stock: {p[2]}\n")

    def abrir_categoria_tipo(self):
        try:
            # import local to avoid circular imports at module load
            from modulos.almacen.articulos.categorias_tipos import PantallaCategoriasTipos
            # replace main content with the new manager
            for w in self.main_content.winfo_children():
                w.destroy()
            PantallaCategoriasTipos(self.main_content, self.controller if hasattr(self, 'controller') else self)
        except Exception as e:
            print(f"Error abriendo gestor Categoría & Tipo: {e}")
            try:
                messagebox.showinfo("Categoría & Tipo", "Funcionalidad pendiente: abrir gestor de Categorías y Tipos.")
            except Exception:
                pass