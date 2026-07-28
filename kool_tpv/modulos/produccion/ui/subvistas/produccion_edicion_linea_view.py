"""Subvista para la edición completa de una línea de producción existente.

Permite modificar todos los campos de una línea ya guardada, incluyendo la
búsqueda y cambio de diseño, cantidad, tipo, talla, color, variante,
método de impresión, extras y modo mixto.
"""
import tkinter as tk
import customtkinter as ctk
import logging
from typing import Callable, Optional, Dict, Any, List

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.produccion_ordenes_service import ProduccionOrdenesService
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font, get_nav_button_config, get_nav_button_style
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList

class ProduccionEdicionLineaView:
    def __init__(self, parent, db: Database, linea_id: int, on_volver: Optional[Callable] = None):
        self.parent = parent
        self.db = db
        self.linea_id = linea_id
        self.on_volver = on_volver
        
        # Servicios
        self.service = ProduccionOrdenesService(db)
        self.disenos_service = ProduccionDisenosService(db)
        
        # Cargar configuración y colores
        self.config = cargar_config_produccion()
        self._colors = self.config.get("colors", {})
        self._bg = self._colors.get("background", "#2c3e50")
        self._text = self._colors.get("text", "#ecf0f1")
        self._accent = self._colors.get("primary", "#3498db")
        self._secondary_bg = "#34495e"

        # Cargar datos de la línea
        self.linea = self.service.get_linea_por_id(linea_id)
        if not self.linea:
            ToastWidget.show(self.parent, f"Error: No se encontró la línea {linea_id}", tipo='error')
            if on_volver: on_volver()
            return

        # Frame principal
        self.frame = tk.Frame(parent, bg=self._bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._build_ui()
        self._load_initial_data()
        
        # Foco inicial en el buscador de diseños
        self.e_buscar_dis.focus_set()

    def _get_font(self, key: str) -> tuple:
        return get_font(self.config, key)

    def _build_ui(self):
        # 1. HEADER: Colección - Sufijo | Diseño
        self.header_frame = ctk.CTkFrame(self.frame, fg_color=self._secondary_bg, corner_radius=0, height=60)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.lbl_header = ctk.CTkLabel(
            self.header_frame, text="CARGANDO DATOS...",
            font=self._get_font("title"), text_color=self._text
        )
        self.lbl_header.pack(expand=True)

        # Contenedor Central Scrollable
        container = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # 2. BUSCADOR DE DISEÑOS
        search_frame = ctk.CTkFrame(container, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(search_frame, text="BUSCAR DISEÑO:", font=self._get_font("label"), text_color=self._text).pack(side="left", padx=10)
        self.e_buscar_dis = ctk.CTkEntry(search_frame, width=300, font=self._get_font("entry"))
        self.e_buscar_dis.pack(side="left", padx=10)
        self.e_buscar_dis.bind("<Return>", lambda e: self._on_buscar_diseno())

        self.btn_buscar = ctk.CTkButton(
            search_frame, text="BUSCAR", width=100,
            command=self._on_buscar_diseno,
            fg_color=self._accent, hover_color="#2980b9"
        )
        self.btn_buscar.pack(side="left", padx=10)

        # NavList de resultados (máximo 5 filas)
        list_cols = [("CÓDIGO", 100), ("NOMBRE", 250), ("COLECCIÓN", 150), ("SUFIJO", 100)]
        self.nav_disenos = VirtualNavList(
            container, columns=list_cols, height=180, 
            on_double_click=self._on_diseno_selected,
            module_name='produccion'
        )
        self.nav_disenos.pack(fill="x", pady=(0, 20))

        # 3. GRID DE EDICIÓN (4 Columnas: Label | Field | Label | Field)
        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10)
        grid_frame.columnconfigure((1, 3), weight=1)

        # Fila 1: Cantidad y Tipo
        ctk.CTkLabel(grid_frame, text="CANTIDAD:", font=self._get_font("label"), text_color=self._text).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.e_cantidad = ctk.CTkEntry(grid_frame, font=self._get_font("entry"))
        self.e_cantidad.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(grid_frame, text="TIPO PRODUCTO:", font=self._get_font("label"), text_color=self._text).grid(row=0, column=2, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.almacen.tipo_repository import TipoRepository
        repo_tipo = TipoRepository(self.db)
        tipos_opts = [(t['id'], t['nombre']) for t in repo_tipo.get_all()]
        self.cb_tipo = SearchableCombo(grid_frame, options=tipos_opts, placeholder="Seleccionar tipo...")
        self.cb_tipo.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        # Fila 2: Talla y Color
        ctk.CTkLabel(grid_frame, text="TALLA:", font=self._get_font("label"), text_color=self._text).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import ProduccionTallasRepository
        repo_tallas = ProduccionTallasRepository(self.db)
        tallas_opts = [(t.nombre, t.nombre) for t in repo_tallas.get_todas()]
        self.cb_talla = SearchableCombo(grid_frame, options=tallas_opts, placeholder="Seleccionar talla...")
        self.cb_talla.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(grid_frame, text="COLOR:", font=self._get_font("label"), text_color=self._text).grid(row=1, column=2, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.produccion.repositories.produccion_colores_repository import ProduccionColoresRepository
        repo_colores = ProduccionColoresRepository(self.db)
        colores_opts = [(c.id, c.nombre) for c in repo_colores.get_todos()]
        self.cb_color = SearchableCombo(grid_frame, options=colores_opts, placeholder="Seleccionar color...")
        self.cb_color.grid(row=1, column=3, padx=10, pady=10, sticky="ew")

        # Fila 3: Variante y Método
        ctk.CTkLabel(grid_frame, text="VARIANTE:", font=self._get_font("label"), text_color=self._text).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.produccion.repositories.produccion_tipos_variantes_repository import ProduccionTiposVariantesRepository
        self.repo_var = ProduccionTiposVariantesRepository(self.db)
        self.cb_variante = SearchableCombo(grid_frame, options=[], placeholder="Seleccionar variante...")
        self.cb_variante.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(grid_frame, text="MÉTODO IMPRESIÓN:", font=self._get_font("label"), text_color=self._text).grid(row=2, column=2, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.produccion.repositories.produccion_metodos_repository import ProduccionMetodosRepository
        self.repo_met = ProduccionMetodosRepository(self.db)
        self.cb_metodo = SearchableCombo(grid_frame, options=[], placeholder="Seleccionar método...")
        self.cb_metodo.grid(row=2, column=3, padx=10, pady=10, sticky="ew")

        # Fila 4: Coste Base y Coste Método
        ctk.CTkLabel(grid_frame, text="COSTE BASE (€):", font=self._get_font("label"), text_color=self._text).grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.e_coste_base = ctk.CTkEntry(grid_frame, font=self._get_font("entry"), state="readonly", fg_color="#34495e")
        self.e_coste_base.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(grid_frame, text="COSTE MÉTODO (€):", font=self._get_font("label"), text_color=self._text).grid(row=3, column=2, padx=10, pady=10, sticky="e")
        self.e_coste_metodo = ctk.CTkEntry(grid_frame, font=self._get_font("entry"), state="readonly", fg_color="#34495e")
        self.e_coste_metodo.grid(row=3, column=3, padx=10, pady=10, sticky="ew")

        # Fila 5: Extra y Coste Extra
        ctk.CTkLabel(grid_frame, text="EXTRA:", font=self._get_font("label"), text_color=self._text).grid(row=4, column=0, padx=10, pady=10, sticky="e")
        from kool_tpv.modulos.produccion.repositories.produccion_extras_repository import ProduccionExtrasRepository
        self.repo_extra = ProduccionExtrasRepository(self.db)
        extra_opts = [(e.id, e.nombre) for e in self.repo_extra.get_todos()]
        self.cb_extra = SearchableCombo(grid_frame, options=[(None, "NINGUNO")] + extra_opts, placeholder="Sin extra")
        self.cb_extra.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(grid_frame, text="COSTE EXTRA (€):", font=self._get_font("label"), text_color=self._text).grid(row=4, column=2, padx=10, pady=10, sticky="e")
        self.e_coste_extra = ctk.CTkEntry(grid_frame, font=self._get_font("entry"), state="readonly", fg_color="#34495e")
        self.e_coste_extra.grid(row=4, column=3, padx=10, pady=10, sticky="ew")

        # Fila 6: Mixta
        ctk.CTkLabel(grid_frame, text="PROD. MIXTA:", font=self._get_font("label"), text_color=self._text).grid(row=5, column=0, padx=10, pady=10, sticky="e")
        self.cb_mixta = ctk.CTkComboBox(grid_frame, values=["NO", "SÍ"], font=self._get_font("entry"))
        self.cb_mixta.grid(row=5, column=1, padx=10, pady=10, sticky="w")

        # Fila 7: Total Unitario (Destacado)
        total_frame = ctk.CTkFrame(container, fg_color=self._secondary_bg, height=50)
        total_frame.pack(fill="x", padx=10, pady=15)
        
        ctk.CTkLabel(total_frame, text="COSTE UNITARIO TOTAL:", font=self._get_font("title"), text_color=self._accent).pack(side="left", padx=20)
        self.lbl_total_unitario = ctk.CTkLabel(total_frame, text="0.00 €", font=(self._get_font("title")[0], 24, "bold"), text_color="#2ecc71")
        self.lbl_total_unitario.pack(side="right", padx=20)

        # 4. FOOTER: Botones
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=40, pady=20)

        nav_volver = get_nav_button_config(self.config, "volver")
        style_volver = get_nav_button_style(self.config, nav_volver.get("style_key", "volver"))
        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="CANCELAR",
            font=self._get_font("button"),
            fg_color=style_volver.get("bg", "#e74c3c"),
            hover_color=style_volver.get("hover", "#c0392b"),
            width=150, height=45,
            command=self._on_volver_click
        )
        self.btn_cancelar.pack(side="left")

        self.btn_guardar = ctk.CTkButton(
            btn_frame, text="GUARDAR CAMBIOS",
            font=self._get_font("button"),
            fg_color="#27ae60",
            hover_color="#2ecc71",
            width=200, height=45,
            command=self._on_guardar_click
        )
        self.btn_guardar.pack(side="right")

    def _load_initial_data(self):
        """Cargar datos de la línea en los widgets."""
        # 1. Header y Diseño
        self._update_header(self.linea.diseno_codigo)
        self._update_metodo_options(self.linea.diseno_codigo)
        
        # 2. Cantidad
        self.e_cantidad.insert(0, str(self.linea.cantidad))
        
        # 3. Combos (IDs)
        self.cb_tipo.set_by_id(self.linea.tipo_id)
        self._on_tipo_changed(self.linea.tipo_id) # Cargar variantes para este tipo
        
        if self.linea.talla:
            self.cb_talla.set(self.linea.talla)
        
        if self.linea.color_id:
            self.cb_color.set_by_id(self.linea.color_id)
            
        if self.linea.variante_id:
            self.cb_variante.set_by_id(self.linea.variante_id)
            
        if self.linea.metodo_id:
            self.cb_metodo.set_by_id(self.linea.metodo_id)
            
        if self.linea.extra_id:
            self.cb_extra.set_by_id(self.linea.extra_id)
        else:
            self.cb_extra.set_by_id(None)
            
        self.cb_mixta.set("SÍ" if self.linea.produccion_mixta else "NO")
        
        # 4. Cargar costes iniciales
        self._update_base_coste_display()
        self._update_metodo_coste_display()
        self._update_extra_coste_display()
        self._update_total_unitario_display()

        # Vincular cambios para recargar datos dinámicos
        self.cb_tipo.on_selection_change = lambda item: [self._on_tipo_changed(item[0]), self._update_base_coste_display()]
        self.cb_color.on_selection_change = lambda item: self._update_base_coste_display()
        self.cb_talla.on_selection_change = lambda item: self._update_base_coste_display()
        self.cb_variante.on_selection_change = lambda item: self._update_base_coste_display()
        self.cb_metodo.on_selection_change = lambda item: self._update_metodo_coste_display()
        self.cb_extra.on_selection_change = lambda item: self._update_extra_coste_display()

    def _update_header(self, diseno_codigo: str):
        """Actualizar el label de cabecera con los datos del diseño."""
        dis = self.disenos_service.obtener_por_codigo(diseno_codigo)
        if dis:
            # Obtener nombres de colección y sufijo
            from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
            from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
            
            repo_col = ProduccionColeccionesRepository(self.db)
            repo_suf = ProduccionSufijosRepository(self.db)
            
            col = repo_col.get_por_id(dis.coleccion_id)
            suf = repo_suf.get_por_id(dis.sufijo_id) if dis.sufijo_id else None
            
            txt_col = col.nombre if col else "SIN COL."
            txt_suf = f" - {suf.nombre}" if suf else ""
            self.lbl_header.configure(text=f"{txt_col}{txt_suf} | {dis.nombre} ({diseno_codigo})")
            self.linea.diseno_codigo = diseno_codigo
        else:
            self.lbl_header.configure(text=f"DISEÑO DESCONOCIDO ({diseno_codigo})")

    def _update_metodo_options(self, diseno_codigo: str):
        """Actualizar las opciones del combo de métodos."""
        try:
            metodos = self.repo_met.get_activos()
            opts = [(m.id, m.nombre) for m in metodos]
            self.cb_metodo.set_options(opts)
            self._update_metodo_coste_display()
        except Exception:
            logging.exception("Error actualizando opciones de métodos")

    def _update_metodo_coste_display(self):
        """Actualizar el Entry de coste del método."""
        try:
            metodo_id = self.cb_metodo.get_id()
            coste = 0
            if metodo_id:
                costes = self.repo_met.get_costes_por_diseno(self.linea.diseno_codigo)
                coste = costes.get(metodo_id, 0)
            
            self.e_coste_metodo.configure(state="normal")
            self.e_coste_metodo.delete(0, "end")
            self.e_coste_metodo.insert(0, f"{coste/100:.2f}")
            self.e_coste_metodo.configure(state="readonly")
            self._update_total_unitario_display()
        except Exception:
            pass

    def _update_extra_coste_display(self):
        """Actualizar el Entry de coste del extra."""
        try:
            extra_id = self.cb_extra.get_id()
            coste = 0
            if extra_id:
                extra = self.repo_extra.get_por_id(extra_id)
                coste = extra.coste if extra else 0
            
            self.e_coste_extra.configure(state="normal")
            self.e_coste_extra.delete(0, "end")
            self.e_coste_extra.insert(0, f"{coste/100:.2f}")
            self.e_coste_extra.configure(state="readonly")
            self._update_total_unitario_display()
        except Exception:
            pass

    def _update_base_coste_display(self):
        """Actualizar el Entry de coste base (prenda)."""
        try:
            from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
            repo_stock = ProduccionStockBaseRepository(self.db)
            
            tipo_id = self.cb_tipo.get_id()
            color_id = self.cb_color.get_id()
            talla = self.cb_talla.get()
            variante_id = self.cb_variante.get_id()
            
            stock_data = repo_stock.get_by_params(tipo_id, color_id, talla, variante_id)
            coste_base = stock_data['coste_medio'] if stock_data else 0
            
            self.e_coste_base.configure(state="normal")
            self.e_coste_base.delete(0, "end")
            self.e_coste_base.insert(0, f"{coste_base/100:.2f}")
            self.e_coste_base.configure(state="readonly")
            self._update_total_unitario_display()
        except Exception:
            pass

    def _update_total_unitario_display(self):
        """Calcular y mostrar el coste unitario total (Base + Método + Extra)."""
        try:
            def to_cents(entry):
                val = entry.get().replace(',', '.')
                return int(float(val) * 100) if val else 0

            c_base = to_cents(self.e_coste_base)
            c_metodo = to_cents(self.e_coste_metodo)
            c_extra = to_cents(self.e_coste_extra)
            
            total = (c_base + c_metodo + c_extra) / 100
            self.lbl_total_unitario.configure(text=f"{total:.2f} €")
        except Exception:
            self.lbl_total_unitario.configure(text="0.00 €")

    def _on_tipo_changed(self, tipo_id: int):
        """Recargar el combo de variantes al cambiar el tipo."""
        vars = self.repo_var.get_por_tipo(tipo_id)
        opts = [(v.id, v.nombre) for v in vars]
        self.cb_variante.set_options(opts)
        if opts:
            self.cb_variante.set_by_id(opts[0][0])
        else:
            self.cb_variante.set_by_id(None)

    def _on_buscar_diseno(self):
        """Ejecutar búsqueda de diseños y poblar la nav_list."""
        filtro = self.e_buscar_dis.get().strip()
        if not filtro:
            return
            
        disenos = self.disenos_service.buscar(filtro)
        data = []
        
        # Necesitamos nombres de colecciones y sufijos para la lista
        from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
        from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
        repo_col = ProduccionColeccionesRepository(self.db)
        repo_suf = ProduccionSufijosRepository(self.db)
        
        for d in disenos:
            col = repo_col.get_por_id(d.coleccion_id)
            suf = repo_suf.get_por_id(d.sufijo_id) if d.sufijo_id else None
            data.append({
                "CÓDIGO": d.codigo,
                "NOMBRE": d.nombre,
                "COLECCIÓN": col.nombre if col else "-",
                "SUFIJO": suf.nombre if suf else "-",
                "_codigo": d.codigo
            })
        
        self.nav_disenos.set_items(data)
        if not data:
            ToastWidget.show(self.frame, "No se encontraron diseños", tipo='warning')

    def _on_diseno_selected(self, item_data: dict):
        """Cambiar el diseño de la línea al hacer doble clic en la lista."""
        codigo = item_data.get("_codigo")
        if codigo:
            self._update_header(codigo)
            self._update_metodo_options(codigo)
            ToastWidget.show(self.frame, f"Diseño cambiado a: {codigo}", tipo='success')

    def _on_volver_click(self):
        if self.on_volver:
            self.on_volver()
        self.frame.destroy()

    def _on_guardar_click(self):
        try:
            # 1. Validar Diseño
            if not self.linea.diseno_codigo:
                ToastWidget.show(self.frame, "Debe seleccionar un diseño", tipo='warning')
                return

            # 2. Validar cantidad
            try:
                cantidad = int(self.e_cantidad.get())
                if cantidad <= 0: raise ValueError()
            except ValueError:
                ToastWidget.show(self.frame, "Cantidad inválida", tipo='warning')
                return

            # 3. Validar Tipo (Obligatorio en BD)
            tipo_id = self.cb_tipo.get_id()
            if not tipo_id:
                ToastWidget.show(self.frame, "Debe seleccionar un tipo de producto", tipo='warning')
                return

            # 4. Recoger resto de datos
            metodo_id = self.cb_metodo.get_id()
            if not metodo_id:
                ToastWidget.show(self.frame, "Debe seleccionar un método de impresión", tipo='warning')
                return

            nuevos_datos = {
                'diseno_codigo': self.linea.diseno_codigo,
                'cantidad': cantidad,
                'tipo_id': tipo_id,
                'talla': self.cb_talla.get() if self.cb_talla.get() not in ("", "NINGUNO") else None,
                'color_id': self.cb_color.get_id(),
                'variante_id': self.cb_variante.get_id(),
                'metodo_id': metodo_id,
                'extra_id': self.cb_extra.get_id(),
                'produccion_mixta': 1 if self.cb_mixta.get() == "SÍ" else 0
            }

            logging.info(f"Guardando cambios en línea {self.linea_id}: {nuevos_datos}")

            if self.service.actualizar_linea(self.linea_id, nuevos_datos):
                ToastWidget.show(self.frame.winfo_toplevel(), "Línea actualizada y stock ajustado", tipo='success')
                # Pequeño delay para que el usuario vea el toast antes de volver
                self.frame.after(600, self._on_volver_click)
            else:
                ToastWidget.show(self.frame.winfo_toplevel(), "Error al actualizar la línea", tipo='error')

        except Exception:
            logging.exception("Error guardando cambios en línea de producción")
            ToastWidget.show(self.frame.winfo_toplevel(), "Error inesperado al guardar", tipo='error')

    def destruir(self):
        self.frame.destroy()
