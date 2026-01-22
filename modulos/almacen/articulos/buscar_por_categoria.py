import customtkinter as ctk
import sqlite3


class BuscarPorCategoria:
    """Renderiza una fila/área de botones con las categorías encontradas en la BD.
    Uso:
        BuscarPorCategoria(parent_frame, controller).render()
    El controlador recibirá la llamada a `mostrar_todos_articulos(categoria)` cuando se pulse una categoría.
    """
    def __init__(self, parent_frame, controller):
        self.parent = parent_frame
        self.controller = controller
        self.frame = None

    def render(self):
        # limpiar si ya existía
        try:
            if self.frame and self.frame.winfo_exists():
                for w in self.frame.winfo_children():
                    w.destroy()
                self.frame.destroy()
        except Exception:
            pass

        # crear nuevo contenedor para botones de categorías
        self.frame = ctk.CTkScrollableFrame(self.parent, height=80, fg_color="transparent")
        self.frame.pack(fill="x", pady=(5, 10), padx=10)

        # cargar categorías desde la BD
        try:
            from database import connect
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT categoria FROM productos WHERE categoria IS NOT NULL AND categoria != '' ORDER BY categoria")
            categorias = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception as e:
            categorias = []
            print(f"Error cargando categorías: {e}")

        if not categorias:
            ctk.CTkLabel(self.frame, text="No hay categorías", text_color="gray").pack(pady=20)
            return

        for cat in categorias:
            btn = ctk.CTkButton(self.frame, text=cat, width=180, height=48, fg_color="#1f538d", hover_color="#2E5F9F",
                                command=lambda c=cat: self._on_categoria(c))
            btn.pack(side="left", padx=6, pady=6)

        # marcar en el controller que la zona de categorias está abierta
        try:
            self.controller.ultima_categoria_opened = True
        except Exception:
            pass

    def _on_categoria(self, categoria):
        try:
            self.controller.mostrar_todos_articulos(categoria)
        except Exception as e:
            print(f"Error al abrir lista por categoría {categoria}: {e}")
