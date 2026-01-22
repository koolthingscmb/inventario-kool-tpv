import customtkinter as ctk
import sqlite3
from database import connect
from tkinter import simpledialog


class SelectorSinCodigo:
    """Clase que renderiza categorías y productos dentro de un frame objetivo.
    No abre Toplevel; se integra en `selector_area` de `ui_ventas`.
    """
    def __init__(self, callback_agregar):
        self.callback_agregar = callback_agregar

    def cargar_categorias(self):
        try:
            conn = connect()
            cursor = conn.cursor()
            query = '''
                SELECT DISTINCT p.categoria
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                WHERE p.nombre_boton IS NOT NULL AND p.nombre_boton != '' AND pr.activo = 1
                AND p.categoria IS NOT NULL
                ORDER BY p.categoria
            '''
            cursor.execute(query)
            categorias = [row[0] for row in cursor.fetchall()]
            conn.close()
            return categorias
        except Exception as e:
            print(f"Error al cargar categorías: {e}")
            return []

    def render_in_frame(self, target_frame):
        """Renderiza en `target_frame` la lista de categorías y un área para productos."""
        # Limpiar target
        for w in target_frame.winfo_children():
            w.destroy()
        # Inicial: elegir modo de búsqueda: por Categoría o por Tipo
        modo_frame = ctk.CTkFrame(target_frame, fg_color='transparent')
        modo_frame.pack(fill='x', pady=(6,8))
        ctk.CTkButton(modo_frame, text='Por Categoría', fg_color='#FF8C42', command=lambda: self._render_categorias(target_frame)).pack(side='left', expand=True, fill='x', padx=6)
        ctk.CTkButton(modo_frame, text='Por Tipo', fg_color='#5A9BD5', command=lambda: self._render_tipos(target_frame)).pack(side='left', expand=True, fill='x', padx=6)

        # contenedor de productos (se usará más adelante)
        productos_container = ctk.CTkScrollableFrame(target_frame)
        productos_container.pack(fill='both', expand=True, pady=5)
        self.productos_container = productos_container

    def _render_categorias(self, target_frame):
        # limpiar área superior y mostrar categorías
        for w in target_frame.winfo_children():
            w.destroy()
        header = ctk.CTkFrame(target_frame, fg_color='transparent')
        header.pack(fill='x', pady=(4,6))
        ctk.CTkButton(header, text='Volver', fg_color='gray', command=lambda: self.render_in_frame(target_frame)).pack(side='left', padx=6)
        # list categories
        categorias = self.cargar_categorias()
        if not categorias:
            ctk.CTkLabel(header, text='No hay categorías con botones activos', text_color='gray').pack(pady=10)
            return
        frame_cat = ctk.CTkFrame(target_frame, fg_color='transparent')
        frame_cat.pack(fill='x', pady=(5, 10))
        for cat in categorias:
            btn = ctk.CTkButton(frame_cat, text=cat, width=140, height=40, command=lambda c=cat: self.mostrar_productos_categoria_in(target_frame, c))
            btn.pack(side='left', padx=5, pady=5)

        # Contenedor de productos
        productos_container = ctk.CTkScrollableFrame(target_frame)
        productos_container.pack(fill='both', expand=True, pady=5)
        self.productos_container = productos_container

    def cargar_tipos(self):
        try:
            conn = connect()
            cursor = conn.cursor()
            # try common tipo-like fields
            cursor.execute("SELECT DISTINCT COALESCE(tipo, '') FROM productos WHERE tipo IS NOT NULL AND tipo != '' ORDER BY tipo")
            rows = [r[0] for r in cursor.fetchall() if r and r[0]]
            conn.close()
            return rows
        except Exception as e:
            print(f"Error al cargar tipos: {e}")
            return []

    def _render_tipos(self, target_frame):
        for w in target_frame.winfo_children():
            w.destroy()
        header = ctk.CTkFrame(target_frame, fg_color='transparent')
        header.pack(fill='x', pady=(4,6))
        ctk.CTkButton(header, text='Volver', fg_color='gray', command=lambda: self.render_in_frame(target_frame)).pack(side='left', padx=6)
        tipos = self.cargar_tipos()
        if not tipos:
            ctk.CTkLabel(header, text='No hay tipos disponibles', text_color='gray').pack(pady=10)
            return
        frame_t = ctk.CTkFrame(target_frame, fg_color='transparent')
        frame_t.pack(fill='x', pady=(5,10))
        for t in tipos:
            btn = ctk.CTkButton(frame_t, text=t, width=140, height=40, command=lambda tt=t: self.mostrar_productos_tipo_in(target_frame, tt))
            btn.pack(side='left', padx=5, pady=5)

        productos_container = ctk.CTkScrollableFrame(target_frame)
        productos_container.pack(fill='both', expand=True, pady=5)
        self.productos_container = productos_container

    def mostrar_productos_tipo_in(self, target_frame, tipo):
        for w in getattr(self, 'productos_container', []).winfo_children():
            w.destroy()
        try:
            conn = connect()
            cursor = conn.cursor()
            query = '''
                SELECT p.id, p.nombre_boton, p.nombre, pr.pvp, COALESCE(p.pvp_variable,0) as pvp_variable
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                WHERE (p.tipo = ? OR p.tipo IS ?) AND pr.activo = 1
                ORDER BY p.nombre_boton
            '''
            cursor.execute("SELECT p.id, p.nombre_boton, p.nombre, pr.pvp FROM productos p JOIN precios pr ON p.id = pr.producto_id WHERE p.tipo = ? AND pr.activo = 1 ORDER BY p.nombre_boton", (tipo,))
            productos = cursor.fetchall()
            conn.close()

            if not productos:
                ctk.CTkLabel(self.productos_container, text='No hay productos en este tipo', text_color='gray').pack(pady=20)
                return

            for producto_id, nombre_boton, nombre_completo, precio in productos:
                btn = ctk.CTkButton(self.productos_container, text=f"{nombre_boton}  {precio:.2f}€", height=60, font=("Arial", 12, "bold"), fg_color="#1f538d", hover_color="#2E5F9F",
                                    command=lambda pid=producto_id, precio=precio, nombre=nombre_completo: self.callback_agregar(pid, precio, nombre))
                btn.pack(fill='x', pady=5, padx=5)

        except Exception as e:
            print(f"Error al cargar productos por tipo: {e}")

    def mostrar_productos_categoria_in(self, target_frame, categoria):
        # limpiar contenedor de productos
        for w in getattr(self, 'productos_container', []).winfo_children():
            w.destroy()

        try:
            conn = connect()
            cursor = conn.cursor()
            query = '''
                SELECT p.id, p.nombre_boton, p.nombre, pr.pvp
                FROM productos p
                JOIN precios pr ON p.id = pr.producto_id
                WHERE p.categoria = ? AND p.nombre_boton IS NOT NULL AND p.nombre_boton != '' AND pr.activo = 1
                ORDER BY p.nombre_boton
            '''
            cursor.execute(query, (categoria,))
            productos = cursor.fetchall()
            conn.close()

            if not productos:
                ctk.CTkLabel(self.productos_container, text="No hay productos en esta categoría", text_color="gray").pack(pady=20)
                return

            for producto_id, nombre_boton, nombre_completo, precio in productos:
                btn = ctk.CTkButton(self.productos_container, text=f"{nombre_boton}  {precio:.2f}€", height=60, font=("Arial", 12, "bold"), fg_color="#1f538d", hover_color="#2E5F9F",
                                    command=lambda pid=producto_id, precio=precio, nombre=nombre_completo: self.callback_agregar(pid, precio, nombre))
                btn.pack(fill="x", pady=5, padx=5)

        except Exception as e:
            print(f"Error al cargar productos: {e}")
