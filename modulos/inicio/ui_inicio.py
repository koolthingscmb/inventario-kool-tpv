import customtkinter as ctk
from datetime import datetime

class PantallaInicio(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._recently_resized = False
        try:
            # bind toplevel Configure to detect maximize/resize events
            top = self.winfo_toplevel()
            top.bind('<Configure>', self._on_configure)
        except Exception:
            pass
        self.pack(fill="both", expand=True)

        # --- CONFIGURACIÓN DE LA REJILLA (GRID) ---
        self.grid_rowconfigure(0, weight=0) 
        self.grid_rowconfigure(1, weight=0) 
        self.grid_rowconfigure(2, weight=0) 
        self.grid_rowconfigure(3, weight=1) 
        self.grid_rowconfigure(4, weight=0) 
        self.grid_columnconfigure(0, weight=1)

        # --- 1. CABECERA: RELOJ ---
        self.lbl_reloj = ctk.CTkLabel(self, text="00/00/00 00:00:00", font=("Arial", 24, "bold"), text_color="gray")
        self.lbl_reloj.grid(row=0, column=0, pady=(20, 10))
        self.actualizar_reloj()

        # --- 2. NIVEL 1: BOTONES PRINCIPALES ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=1, column=0, pady=10)

        btn_w, btn_h = 160, 80
        btn_font = ("Arial", 16, "bold")

        ctk.CTkButton(self.top_frame, text="🛒 CAJA / TPV", width=btn_w, height=btn_h, font=btn_font,
                  command=lambda: self._safe_call(self.controller.mostrar_ventas)).pack(side="left", padx=10)

        ctk.CTkButton(self.top_frame, text="📦 ALMACÉN", width=btn_w, height=btn_h, font=btn_font,
                  fg_color="green", hover_color="darkgreen",
                  command=lambda: self._safe_call(self.mostrar_submenu_almacen)).pack(side="left", padx=10)

        ctk.CTkButton(self.top_frame, text="👥 CLIENTES", width=btn_w, height=btn_h, font=btn_font,
                  fg_color="#D97B29", hover_color="#B5631E",
                  command=lambda: self._safe_call(self.mostrar_submenu_clientes)).pack(side="left", padx=10)

        ctk.CTkButton(self.top_frame, text="🛍️ SHOPIFY", width=btn_w, height=btn_h, font=btn_font,
                  fg_color="#95BF47", hover_color="#5E8E3E", text_color="black",
                  command=lambda: self._safe_call(self.mostrar_submenu_shopify)).pack(side="left", padx=10)

        ctk.CTkButton(self.top_frame, text="⚙️ CONFIG", width=btn_w, height=btn_h, font=btn_font,
                  fg_color="gray", hover_color="#444444",
                  command=lambda: self._safe_call(self.mostrar_submenu_config)).pack(side="left", padx=10)

        # --- 3. NIVEL 2: SUBMENÚ ---
        self.submenu_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=0, height=120)
        self.submenu_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)

        # --- 4. NIVEL 3: OPCIONES ---
        self.tercer_nivel_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        self.tercer_nivel_frame.grid(row=3, column=0, sticky="nsew", padx=0, pady=0)
        
        self.lbl_instruccion = ctk.CTkLabel(self.tercer_nivel_frame, text="Selecciona una opción arriba para empezar", 
                                            font=("Arial", 16), text_color="gray")
        self.lbl_instruccion.place(relx=0.5, rely=0.5, anchor="center")

        # --- 5. PIE: BOTÓN SALIR ---
        self.btn_salir = ctk.CTkButton(self, text="Cerrar Programa", fg_color="darkred", hover_color="red",
                                       command=self.controller.destroy)
        self.btn_salir.grid(row=4, column=0, pady=20)

    # --- FUNCIONES DE LIMPIEZA ---
    def limpiar_submenu(self):
        for widget in self.submenu_frame.winfo_children():
            widget.destroy()

    def limpiar_tercer_nivel(self):
        for widget in self.tercer_nivel_frame.winfo_children():
            widget.destroy()

    def _on_configure(self, event=None):
        # Called on window resize/maximize; set a short suppression window for clicks
        try:
            self._recently_resized = True
            # clear flag after 300ms
            self.after(300, lambda: setattr(self, '_recently_resized', False))
        except Exception:
            pass

    def _safe_call(self, fn):
        # Prevent accidental button activations immediately after resizing/maximizing
        try:
            if getattr(self, '_recently_resized', False):
                return
        except Exception:
            pass
        try:
            fn()
        except Exception as e:
            print(f"Error ejecutando comando seguro: {e}")

    def actualizar_reloj(self):
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_reloj.configure(text=ahora)
        self.after(1000, self.actualizar_reloj)

    # --- LÓGICA DE NAVEGACIÓN ---
    def mostrar_submenu_almacen(self):
        self.limpiar_submenu()
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.submenu_frame, text="GESTIÓN DE ALMACÉN", font=("Arial", 18, "bold"), text_color="white").pack(pady=10)
        frame_botones = ctk.CTkFrame(self.submenu_frame, fg_color="transparent")
        frame_botones.pack(pady=5)
        ctk.CTkButton(frame_botones, text="PROVEEDORES", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray").grid(row=0, column=0, padx=10)
        ctk.CTkButton(frame_botones, text="PROVEEDORES", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray", command=self.mostrar_proveedores).grid(row=0, column=0, padx=10)
        ctk.CTkButton(frame_botones, text="ARTÍCULOS", width=150, height=50, font=("Arial", 14, "bold"), fg_color="#1f538d", 
                      command=self.mostrar_opciones_articulos).grid(row=0, column=1, padx=10)
        ctk.CTkButton(frame_botones, text="ALBARANES", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray",
                      command=self.mostrar_opciones_albaranes).grid(row=0, column=2, padx=10)
        ctk.CTkButton(frame_botones, text="INVENTARIOS", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray").grid(row=0, column=3, padx=10)

    def mostrar_opciones_articulos(self):
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.tercer_nivel_frame, text="OPCIONES DE ARTÍCULOS", font=("Arial", 14, "bold"), text_color="#1f538d").pack(pady=20)
        frame_opciones = ctk.CTkFrame(self.tercer_nivel_frame, fg_color="transparent")
        frame_opciones.pack(pady=10)
        ctk.CTkButton(frame_opciones, text="➕ AÑADIR\nNUEVO", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#228B22", hover_color="green", command=self.controller.mostrar_crear_producto).grid(row=0, column=0, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="📂 BUSCAR X\nCATEGORÍA", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#555555", command=self.mostrar_buscar_por_categoria).grid(row=0, column=1, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="||| BUSCAR X\nEAN (Barras)", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#555555", command=self.mostrar_buscar_por_ean).grid(row=0, column=2, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="TODOS", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#555555", command=self.controller.mostrar_todos_articulos).grid(row=0, column=3, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="CATEGORÍA &\nTIPO", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#5A9BD5", command=self.mostrar_categoria_tipo).grid(row=0, column=4, padx=20, pady=20)
        # Si el usuario tenía la fila de categorías abierta, restaurarla
        try:
            if getattr(self.controller, 'ultima_categoria_opened', False):
                self.mostrar_buscar_por_categoria()
        except Exception:
            pass
        # Si venimos desde una búsqueda por EAN que abrió un producto, restaurar esa pantalla
        try:
            if getattr(self.controller, 'ultima_buscar_por_ean_active', False):
                # Mostrar y luego limpiar la bandera
                self.mostrar_buscar_por_ean()
                try:
                    self.controller.ultima_buscar_por_ean_active = False
                except Exception:
                    pass
        except Exception:
            pass

    def mostrar_buscar_por_categoria(self):
            # Delegar renderizado al módulo de artículos (buscar_por_categoria)
            try:
                from modulos.almacen.articulos.buscar_por_categoria import BuscarPorCategoria
                BuscarPorCategoria(self.tercer_nivel_frame, self.controller).render()
            except Exception as e:
                print(f"Error mostrando buscar por categoría: {e}")

    def mostrar_proveedores(self):
        try:
            from modulos.almacen.proveedores.ui_proveedores import PantallaProveedores
            self.limpiar_tercer_nivel()
            PantallaProveedores(self.tercer_nivel_frame, self.controller)
        except Exception as e:
            print(f"Error mostrando proveedores: {e}")

    def mostrar_opciones_albaranes(self):
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.tercer_nivel_frame, text="OPCIONES DE ALBARANES", font=("Arial", 14, "bold"), text_color="gray").pack(pady=20)
        frame_opciones = ctk.CTkFrame(self.tercer_nivel_frame, fg_color="transparent")
        frame_opciones.pack(pady=10)
        ctk.CTkButton(frame_opciones, text="COMPRA", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#228B22", hover_color="green").grid(row=0, column=0, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="SALIDA", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#FF4500").grid(row=0, column=1, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="CONSULTAR", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#555555").grid(row=0, column=2, padx=20, pady=20)
        ctk.CTkButton(frame_opciones, text="IMPORTAR", width=180, height=80, font=("Arial", 15, "bold"), fg_color="#555555").grid(row=0, column=3, padx=20, pady=20)

    def mostrar_buscar_por_ean(self):
        # Delegar renderizado al módulo de artículos (buscar_por_ean)
        try:
            from modulos.almacen.articulos.buscar_por_ean import BuscarPorEAN
            # Limpiar tercer nivel y delegar
            self.limpiar_tercer_nivel()
            BuscarPorEAN(self.tercer_nivel_frame, self.controller).render()
        except Exception as e:
            print(f"Error mostrando buscar por EAN: {e}")

    def mostrar_categoria_tipo(self):
        self.limpiar_tercer_nivel()
        try:
            from modulos.almacen.articulos.categorias_tipos import PantallaCategoriasTipos
            PantallaCategoriasTipos(self.tercer_nivel_frame, self.controller)
        except Exception as e:
            print(f"Error mostrando Categoría & Tipo: {e}")

    def mostrar_submenu_clientes(self):
        self.limpiar_submenu()
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.submenu_frame, text="GESTIÓN DE CLIENTES", font=("Arial", 18, "bold"), text_color="#D97B29").pack(pady=10)
        frame_botones = ctk.CTkFrame(self.submenu_frame, fg_color="transparent")
        frame_botones.pack(pady=6)

        # botones grandes estilo Almacén
        btn_w, btn_h = 240, 110
        btn_font = ("Arial", 16, "bold")

        ctk.CTkButton(frame_botones, text="📇 GESTIÓN\nCLIENTES", width=btn_w, height=btn_h, font=btn_font,
                      fg_color="#D97B29", hover_color="#B5631E",
                      command=lambda: self._safe_call(lambda: self.controller.mostrar_gestion_clientes())).grid(row=0, column=0, padx=12, pady=6)

        # botón de ranking: por ahora sólo imprime en consola
        ctk.CTkButton(frame_botones, text="🏆 RANKING\nY ESTADÍSTICAS", width=btn_w, height=btn_h, font=btn_font,
                      fg_color="#777777", hover_color="#666666",
                      command=lambda: print('Ranking - pendiente')).grid(row=0, column=1, padx=12, pady=6)

        # botón configuración fidelización: pendiente
        ctk.CTkButton(frame_botones, text="⚙️ CONFIG\nFIDELIZACIÓN", width=btn_w, height=btn_h, font=btn_font,
                      fg_color="#777777", hover_color="#666666",
                      command=lambda: print('Config fidelización - pendiente')).grid(row=0, column=2, padx=12, pady=6)

    def mostrar_submenu_shopify(self):
        self.limpiar_submenu()
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.submenu_frame, text="CONEXIÓN SHOPIFY", font=("Arial", 18, "bold"), text_color="#95BF47").pack(pady=10)
        frame_botones = ctk.CTkFrame(self.submenu_frame, fg_color="transparent")
        frame_botones.pack(pady=5)
        ctk.CTkButton(frame_botones, text="SINCRONIZAR\nSTOCK", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray").grid(row=0, column=0, padx=10)
        ctk.CTkButton(frame_botones, text="DESCARGAR\nPEDIDOS", width=150, height=50, font=("Arial", 14, "bold"), fg_color="gray").grid(row=0, column=1, padx=10)

    def mostrar_submenu_config(self):
        self.limpiar_submenu()
        self.limpiar_tercer_nivel()
        ctk.CTkLabel(self.submenu_frame, text="CONFIGURACIÓN", font=("Arial", 18, "bold"), text_color="gray").pack(pady=20)
        frame_bot = ctk.CTkFrame(self.submenu_frame, fg_color='transparent')
        frame_bot.pack(pady=5)
        # Botón EXPORTAR principal
        ctk.CTkButton(frame_bot, text='EXPORTAR', width=160, height=44, fg_color='#3399FF', command=self._toggle_export_options).pack()
        # Botón REINICIAR CONTADORES (para pruebas)
        try:
            ctk.CTkButton(frame_bot, text='REINICIAR', width=160, height=44, fg_color='darkred', command=self._reset_counters).pack(pady=(8,0))
        except Exception:
            pass
        # espacio para botones desplegables
        try:
            self._export_options_frame.destroy()
        except Exception:
            pass
        self._export_options_frame = ctk.CTkFrame(self.submenu_frame, fg_color='transparent')
        self._export_options_frame.pack(pady=8)

    def _toggle_export_options(self):
        # Muestra u oculta los botones Artículos / Clientes
        frame = getattr(self, '_export_options_frame', None)
        if not frame:
            return
        # Si ya tiene botones, limpiamos (toggle off)
        if frame.winfo_children():
            for w in frame.winfo_children():
                w.destroy()
            return
        # Crear botones
        ctk.CTkButton(frame, text='Artículos', width=140, height=40, fg_color='#1f538d', command=self._export_articulos).pack(side='left', padx=6)
        ctk.CTkButton(frame, text='Clientes', width=140, height=40, fg_color='#D97B29', command=self._export_clientes).pack(side='left', padx=6)

    def _export_articulos(self):
        # Abrir diálogo de exportación de artículos
        try:
            from modulos.configuracion.ui_config import DialogExportArticulos
            dlg = DialogExportArticulos(self)
            try:
                dlg.grab_set()
            except Exception:
                pass
        except Exception as e:
            print(f"Error abriendo exportar artículos: {e}")

    def _export_clientes(self):
        # Placeholder: por ahora solo mensaje
        try:
            import tkinter.messagebox as mb
            mb.showinfo('Exportar Clientes', 'Funcionalidad no implementada todavía.')
        except Exception:
            pass

    def _reset_counters(self):
        """Handler para reiniciar los contadores de tickets tras confirmación del usuario."""
        try:
            import tkinter.messagebox as mb
            ok = mb.askyesno('Reiniciar contadores', '¿Estás seguro? Esto reseteará los contadores de tickets (solo sqlite_sequence).')
            if not ok:
                return
        except Exception:
            # si falla el diálogo, seguimos intentando
            ok = True
        # Ejecutar el script `scripts/clear_tickets.py` (contiene la lógica destructiva)
        try:
            import os, sys, subprocess, tkinter.messagebox as mb2
            script_path = os.path.join(os.getcwd(), 'scripts', 'clear_tickets.py')
            if not os.path.exists(script_path):
                try:
                    mb2.showerror('Error', f'No se encontró el script: {script_path}')
                except Exception:
                    print('No se encontró el script:', script_path)
                return

            # Ejecutar el script con el intérprete actual
            try:
                res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
                output = (res.stdout or '') + (res.stderr or '')
                if res.returncode == 0:
                    try:
                        mb2.showinfo('Reiniciado', 'Tickets y contadores reiniciados correctamente.')
                    except Exception:
                        print('Tickets y contadores reiniciados correctamente.')
                    try:
                        print(output)
                    except Exception:
                        pass
                else:
                    try:
                        mb2.showerror('Error', f'El script devolvió código {res.returncode}. Revisa la salida en consola.')
                    except Exception:
                        print('Error ejecutando script, returncode:', res.returncode)
                    try:
                        print(output)
                    except Exception:
                        pass
            except Exception as e:
                try:
                    mb2.showerror('Error', f'No se pudo ejecutar el script: {e}')
                except Exception:
                    print('No se pudo ejecutar el script:', e)
        except Exception:
            # en caso de cualquier fallo en el flujo anterior, informar por consola
            try:
                print('Fallo al intentar reiniciar contadores.')
            except Exception:
                pass