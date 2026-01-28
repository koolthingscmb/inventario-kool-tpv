import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
from typing import Optional, Dict, Any

from modulos.configuracion.config_service import ConfigService

class UIConfigFidelizacion(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        print(">>> [LOG] CARGANDO INTERFAZ MAESTRA 20/80 CORREGIDA <<<")
        self.controller = controller
        self.service = ConfigService()
        
        self.cat_entries = {}
        self.tipo_entries = {}
        self.selected_promo_id = None

        # Configuración del Grid Principal (20% / 80%)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=20) # Menú
        self.grid_columnconfigure(1, weight=80) # Detalle

        # --- COLUMNA IZQUIERDA (Menú Lateral) ---
        self.menu_panel = ctk.CTkFrame(self, fg_color="#2c3e50") # Azul oscuro profesional
        self.menu_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        ctk.CTkButton(self.menu_panel, text="← Volver", fg_color="#e74c3c", command=self._on_volver).pack(fill="x", padx=15, pady=20)
        
        ctk.CTkLabel(self.menu_panel, text="MENÚ DE CONTROL", font=("Arial", 16, "bold"), text_color="white").pack(pady=(10,20))

        # Botones de navegación
        opts = {"anchor": "w", "height": 45, "font": ("Arial", 13)}
        self.btn_gen = ctk.CTkButton(self.menu_panel, text="⚙️ Ajustes Generales", command=lambda: self._mostrar_seccion("general"), **opts)
        self.btn_gen.pack(fill="x", padx=10, pady=5)

        self.btn_cat = ctk.CTkButton(self.menu_panel, text="📊 Categorías y Tipos", command=lambda: self._mostrar_seccion("categorias"), **opts)
        self.btn_cat.pack(fill="x", padx=10, pady=5)

        self.btn_promo = ctk.CTkButton(self.menu_panel, text="🎁 Promociones", command=lambda: self._mostrar_seccion("promos"), **opts)
        self.btn_promo.pack(fill="x", padx=10, pady=5)

        # (Reset moved to dedicated Maintenance UI)

        # --- COLUMNA DERECHA (Contenido) ---
        self.main_panel = ctk.CTkFrame(self, fg_color="#f2f2f2")
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(1, weight=1)

        # Título superior
        self.header_frame = ctk.CTkFrame(self.main_panel, fg_color="white", height=70, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.title_label = ctk.CTkLabel(self.header_frame, text="CONFIGURACIÓN DE FIDELIZACIÓN", 
                                        font=("Arial", 22, "bold"), text_color="black")
        self.title_label.pack(side="left", padx=30, pady=20)

        # Contenedor dinámico
        self.content_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        # Iniciar en la sección general
        self._mostrar_seccion("general")

    def _limpiar_panel(self):
        for w in self.content_frame.winfo_children(): w.destroy()

    def _mostrar_seccion(self, seccion):
        self._limpiar_panel()
        if seccion == "general": self._render_general()
        elif seccion == "categorias": self._render_categorias_tipos()
        elif seccion == "promos": self._render_promociones()
        

    

    # --- SECCIÓN: GENERAL ---
    def _render_general(self):
        container = ctk.CTkFrame(self.content_frame, fg_color="white", corner_radius=15)
        container.pack(fill="both", expand=True, padx=40, pady=40)
        
        f_activa = self.service.get_valor("fide_activa", "1")
        self.var_activa = tk.IntVar(value=int(f_activa))
        
        ctk.CTkLabel(container, text="Estado del Sistema", font=("Arial", 16, "bold"), text_color="black").pack(pady=(30,10))
        ctk.CTkSwitch(container, text="Fidelización Activada", variable=self.var_activa, text_color="black", font=("Arial", 14)).pack(pady=10)

        ctk.CTkLabel(container, text="Porcentaje de puntos general (%)", text_color="black").pack(pady=(20,0))
        self.ent_pct = ctk.CTkEntry(container, width=200, fg_color="#f2f2f2", text_color="black")
        self.ent_pct.insert(0, self.service.get_valor("fide_porcentaje_general", "5"))
        self.ent_pct.pack(pady=5)

        ctk.CTkButton(container, text="Guardar Cambios", fg_color="#2ecc71", command=self._guardar_general).pack(pady=40)

    # --- SECCIÓN: CATEGORÍAS Y TIPOS (Mosaico) ---
    def _render_categorias_tipos(self):
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def crear_mosaico(titulo, datos, storage):
            ctk.CTkLabel(scroll, text=titulo, font=("Arial", 18, "bold"), text_color="black").pack(anchor="w", pady=(20,10))
            grid = ctk.CTkFrame(scroll, fg_color="transparent")
            grid.pack(fill="x")
            grid.grid_columnconfigure((0,1,2,3), weight=1)
            for i, d in enumerate(datos):
                cell = ctk.CTkFrame(grid, fg_color="white", corner_radius=10, border_width=1, border_color="#ddd")
                cell.grid(row=i//4, column=i%4, padx=8, pady=8, sticky="nsew")
                ctk.CTkLabel(cell, text=d['nombre'], text_color="black", font=("Arial", 11, "bold")).pack(pady=(10,0))
                ent = ctk.CTkEntry(cell, width=70, placeholder_text="%", fg_color="#f9f9f9", text_color="black", justify="center")
                ent.insert(0, str(d['fide_porcentaje'] or ""))
                ent.pack(pady=10)
                storage[d['id']] = ent

        self.cat_entries = {}
        self.tipo_entries = {}
        crear_mosaico("PUNTOS POR CATEGORÍA", self.service.listar_categorias_fide(), self.cat_entries)
        crear_mosaico("PUNTOS POR TIPO DE PRODUCTO", self.service.listar_tipos_fide(), self.tipo_entries)
        
        ctk.CTkButton(scroll, text="💾 Guardar todos los porcentajes", fg_color="#2ecc71", height=50, 
                      command=self._guardar_mosaico).pack(pady=30, fill="x", padx=50)

    # --- SECCIÓN: PROMOCIONES ---
    def _render_promociones(self):
        self.content_frame.grid_columnconfigure(0, weight=40); self.content_frame.grid_columnconfigure(1, weight=60)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Izquierda: Lista
        list_f = ctk.CTkFrame(self.content_frame, fg_color="white")
        list_f.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        self.tree = ttk.Treeview(list_f, columns=("n","m"), show="headings")
        self.tree.heading("n", text="Evento"); self.tree.heading("m", text="Mult.")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_promo)
        ctk.CTkButton(list_f, text="+ Nueva Promoción", command=self._nueva_promo).pack(fill="x", padx=10, pady=10)

        # Derecha: Form
        self.p_form = ctk.CTkFrame(self.content_frame, fg_color="white", corner_radius=15)
        self.p_form.grid(row=0, column=1, sticky="nsew")
        
        def add_p(label, row):
            ctk.CTkLabel(self.p_form, text=label, text_color="black", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", padx=30, pady=(15,0))
            e = ctk.CTkEntry(self.p_form, width=300, fg_color="#f2f2f2", text_color="black")
            e.grid(row=row+1, column=0, sticky="w", padx=30, pady=5)
            return e

        self.en_p_nom = add_p("Nombre del Evento (ej: Halloween)", 0)
        
        # (Volver button already in menu_panel)
        self.en_p_ini = add_p("Fecha Inicio (AAAA-MM-DD)", 2)
        self.en_p_fin = add_p("Fecha Fin (AAAA-MM-DD)", 4)
        self.en_p_mul = add_p("Multiplicador (ej: 2.0)", 6)

        btn_f = ctk.CTkFrame(self.p_form, fg_color="transparent")
        btn_f.grid(row=8, column=0, sticky="w", padx=30, pady=30)
        ctk.CTkButton(btn_f, text="Guardar", fg_color="#2ecc71", command=self._guardar_promo).pack(side="left", padx=5)
        ctk.CTkButton(btn_f, text="Eliminar", fg_color="#e74c3c", command=self._eliminar_promo).pack(side="left", padx=5)
        self._cargar_promos_list()

    # --- LÓGICA DE GUARDADO ---
    def _guardar_general(self):
        self.service.set_valor("fide_activa", str(self.var_activa.get()))
        self.service.set_valor("fide_porcentaje_general", self.ent_pct.get())
        messagebox.showinfo("Éxito", "Ajustes generales actualizados")

    def _guardar_mosaico(self):
        try:
            for cid, ent in self.cat_entries.items():
                v = ent.get().strip()
                self.service.actualizar_porcentaje_categoria(cid, float(v) if v else None)
            for tid, ent in self.tipo_entries.items():
                v = ent.get().strip()
                self.service.actualizar_porcentaje_tipo(tid, float(v) if v else None)
            messagebox.showinfo("Éxito", "Porcentajes actualizados correctamente")
        except ValueError: messagebox.showerror("Error", "Por favor, introduce solo números")

    def _cargar_promos_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for p in self.service.listar_promociones():
            self.tree.insert("", "end", iid=str(p['id']), values=(p['nombre'], p['multiplicador']))

    def _on_select_promo(self, e):
        sel = self.tree.selection()
        if sel:
            p = next((x for x in self.service.listar_promociones() if str(x['id']) == sel[0]), None)
            if p:
                self.selected_promo_id = p['id']
                self.en_p_nom.delete(0, tk.END); self.en_p_nom.insert(0, p['nombre'])
                self.en_p_ini.delete(0, tk.END); self.en_p_ini.insert(0, p['fecha_inicio'] or "")
                self.en_p_fin.delete(0, tk.END); self.en_p_fin.insert(0, p['fecha_fin'] or "")
                self.en_p_mul.delete(0, tk.END); self.en_p_mul.insert(0, str(p['multiplicador']))

    def _nueva_promo(self):
        self.selected_promo_id = None
        for e in [self.en_p_nom, self.en_p_ini, self.en_p_fin, self.en_p_mul]: e.delete(0, tk.END)

    def _guardar_promo(self):
        try:
            d = {"id": self.selected_promo_id, "nombre": self.en_p_nom.get(), "fecha_inicio": self.en_p_ini.get(),
                 "fecha_fin": self.en_p_fin.get(), "multiplicador": float(self.en_p_mul.get() or 1.0), "activa": 1}
            self.service.guardar_promocion(d); self._cargar_promos_list()
            messagebox.showinfo("Éxito", "Promoción guardada")
        except: messagebox.showerror("Error", "Revisa los datos de la promoción")

    def _eliminar_promo(self):
        if self.selected_promo_id and messagebox.askyesno("Confirmar", "¿Eliminar promoción?"):
            self.service.eliminar_promocion(self.selected_promo_id)
            self._cargar_promos_list(); self._nueva_promo()

    def _on_volver(self):
        if self.controller:
            try:
                self.controller.volver_a_configuracion()
            except Exception:
                try:
                    self.controller.volver_a_configuracion()
                except Exception:
                    return
            # intentar restaurar el submenu previo si el controller lo guardó
            try:
                # esperar un momento para que la vista de inicio se instancie
                self.after(120, lambda: getattr(self.controller, 'restaurar_inicio_submenu', lambda: None)())
            except Exception:
                pass