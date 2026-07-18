from customtkinter import CTkFrame, CTkLabel, CTkEntry, CTkTextbox
import logging
from typing import List, Dict, Optional, Any

import customtkinter as ctk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.config_loader import load_layout_config
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.notificaciones import show_success, show_warning, show_error

# Servicios REPOS (obligatorio, sin queries directas)
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.repositories.produccion_colecciones_repository import ProduccionColeccionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_sufijos_repository import ProduccionSufijosRepository
from kool_tpv.modulos.produccion.repositories.produccion_relaciones_repository import ProduccionRelacionesRepository
from kool_tpv.modulos.produccion.repositories.variante_producto_repository import VarianteProductoRepository

from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore

logger = logging.getLogger(__name__)


class ReposicionFormUI(CTkFrame):
    """Formulario de reposición siguiendo estrictamente las zonas definidas por el usuario."""

    def __init__(self, parent, db, carrito_service=None, view=None, productos_pendientes=None, ticket_id=None, callback_finalizar=None, linea_existente=None):
        super().__init__(parent)

        self.db = db
        self.carrito_service = carrito_service
        self.view = view
        self.productos_pendientes = productos_pendientes or []
        self.ticket_id = ticket_id
        self.callback_finalizar = callback_finalizar
        self.linea_existente = linea_existente
        self._linea_edit_id = linea_existente.get("id") if linea_existente else None

        self.indice_actual = 0
        self.producto_actual = None
        self.tipo_actual = None
        self.diseno_seleccionado = None

        # Servicios (SOLO repos)
        self.producto_service = ProductoService(db)
        self.tipos_service = ProduccionTiposService(db)
        self.variantes_service = ProduccionTiposVariantesService(db)
        self.tallas_service = ProduccionTallasService(db)
        self.colores_service = ProduccionColoresService(db)
        self.disenos_service = ProduccionDisenosService(db)
        self.colecciones_repo = ProduccionColeccionesRepository(db)
        self.sufijos_repo = ProduccionSufijosRepository(db)
        self.relaciones_repo = ProduccionRelacionesRepository(db)
        self.variante_producto_repo = VarianteProductoRepository(db)

        # Keyboard manager
        root = self.winfo_toplevel()
        self.keyboard_manager = getattr(root, 'keyboard_manager', None)

        # Header
        self.header_frame = CTkFrame(self)
        self.header_frame.pack(side="top", fill="x", padx=20, pady=10)

        nombre_inicial = ""
        if self.productos_pendientes:
            nombre_inicial = self.productos_pendientes[0].get('nombre', '')
        self.lbl_titulo = CTkLabel(
            self.header_frame,
            text=f"Reposición de '{nombre_inicial}'",
            font=("Roboto", 20, "bold")
        )
        self.lbl_titulo.pack(side="left", padx=10)

        # Body
        self.body_frame = CTkFrame(self)
        self.body_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        self._setup_ui()
        self._setup_tab_navigation()
        self._cargar_siguiente_producto()

    def _setup_ui(self):
        # ZONA 1: grid 6x1 - Producto + Tipo + Encargo
        zona1 = CTkFrame(self.body_frame, fg_color="transparent")
        zona1.pack(fill="x", padx=10, pady=(5, 10))
        for c in range(6):
            zona1.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0)

        CTkLabel(zona1, text="Producto", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.entry_producto = CTkEntry(zona1, height=32)
        self.entry_producto.grid(row=0, column=1, padx=(0, 12), sticky="ew")
        self.entry_producto.configure(state="readonly")

        CTkLabel(zona1, text="Tipo", font=("Roboto", 14, "bold")).grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.entry_tipo = CTkEntry(zona1, height=32)
        self.entry_tipo.grid(row=0, column=3, padx=(0, 12), sticky="ew")
        self.entry_tipo.configure(state="readonly")

        CTkLabel(zona1, text="Encargo:", font=("Roboto", 14, "bold")).grid(row=0, column=4, padx=(0, 6), sticky="w")
        self.check_encargo = ctk.CTkCheckBox(zona1, text="", width=24, height=24)
        self.check_encargo.grid(row=0, column=5, padx=(0, 0), sticky="w")

        # ZONA 2: grid 6x1 - Variante + Talla + Color (condicionales)
        zona2 = CTkFrame(self.body_frame, fg_color="transparent")
        zona2.pack(fill="x", padx=10, pady=5)
        for c in range(6):
            zona2.grid_columnconfigure(c, weight=1 if c in (1, 3, 5) else 0)

        CTkLabel(zona2, text="Variante", font=("Roboto", 14, "bold")).grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.combo_variante = SearchableCombo(
            zona2,
            placeholder="Selecciona variante...",
            width=220,
            command=self._on_variante_changed
        )
        self.combo_variante.grid(row=0, column=1, padx=(0, 12), sticky="ew")

        self.lbl_color = CTkLabel(zona2, text="Color", font=("Roboto", 14, "bold"))
        self.lbl_color.grid(row=0, column=2, padx=(0, 6), sticky="w")
        self.combo_color = SearchableCombo(
            zona2,
            placeholder="Color...",
            width=160,
            command=self._on_color_changed
        )
        self.combo_color.grid(row=0, column=3, padx=(0, 12), sticky="ew")

        self.lbl_talla = CTkLabel(zona2, text="Talla", font=("Roboto", 14, "bold"))
        self.lbl_talla.grid(row=0, column=4, padx=(0, 6), sticky="w")
        self.combo_talla = SearchableCombo(
            zona2,
            placeholder="Talla...",
            width=160,
            command=self._on_talla_changed
        )
        self.combo_talla.grid(row=0, column=5, padx=(0, 0), sticky="ew")

        # ZONA 3: Comentarios (full width) + Escudo a la derecha
        zona3 = CTkFrame(self.body_frame, fg_color="transparent")
        zona3.pack(fill="x", padx=10, pady=(10, 5))
        fila_comentarios = CTkFrame(zona3, fg_color="transparent")
        fila_comentarios.pack(fill="x", pady=(0, 4))
        CTkLabel(fila_comentarios, text="Comentarios", font=("Roboto", 14, "bold")).pack(side="left")
        escudo_frame = CTkFrame(fila_comentarios, fg_color="transparent")
        escudo_frame.pack(side="right")
        CTkLabel(escudo_frame, text="Escudo:", font=("Roboto", 14, "bold")).pack(side="left", padx=(0, 4))
        self.check_escudo = ctk.CTkCheckBox(escudo_frame, text="", width=24, height=24, command=self._toggle_escudo)
        self.check_escudo.pack(side="left", padx=(0, 6))
        self.entry_escudo = CTkEntry(escudo_frame, width=180, height=28, font=("Roboto", 13), placeholder_text="Texto del escudo...")
        self.entry_escudo.pack(side="left")
        self.entry_escudo.configure(state="disabled")
        self.text_comentarios = CTkTextbox(zona3, height=60, font=("Roboto", 14))
        self.text_comentarios.pack(fill="x", expand=False)

        # ZONA 4: Nav list diseños (exactamente como en diseño_nuevo)
        zona4 = CTkFrame(self.body_frame, fg_color="transparent")
        zona4.pack(fill="both", expand=True, padx=10, pady=5)

        CTkLabel(zona4, text="Diseños", font=("Roboto", 14, "bold")).pack(anchor="w", pady=(0, 4))

        self.entry_buscar_diseno = CTkEntry(zona4, placeholder_text="Buscar diseño (código, nombre, colección)...", height=32)
        self.entry_buscar_diseno.pack(fill="x", pady=(0, 4))
        self.entry_buscar_diseno.bind("<Return>", self._on_buscar_diseno_enter)
        self.entry_buscar_diseno.bind("<KP_Enter>", self._on_buscar_diseno_enter)

        columns = [
            ("codigo", 100, "Código"),
            ("nombre", 220, "Nombre"),
            ("coleccion_nombre", 140, "Colección"),
            ("sufijo_nombre", 100, "Sufijo"),
            ("tipos_nombres", 140, "Tipos"),
            ("total_producido", 70, "Uds."),
        ]
        self.design_list = SearchablePaginatedNavList(
            parent=zona4,
            columns=columns,
            search_function=self._buscar_disenos,
            map_function=self._map_diseno,
            module_name="tpv",
            page_limit=50,
            on_double_click=self._on_diseno_double_click,
            keyboard_manager=self.keyboard_manager,
            layout_config=load_layout_config(),
        )
        self.design_list.pack(fill="both", expand=True)

        nav = getattr(self.design_list, 'nav_list', None)
        if nav and hasattr(nav, 'bind_return'):
            nav.bind_return(self._on_diseno_return)

        # ZONA 5: Diseño seleccionado (readonly)
        zona5 = CTkFrame(self.body_frame, fg_color="transparent")
        zona5.pack(fill="x", padx=10, pady=(5, 5))
        CTkLabel(zona5, text="Diseño escogido", font=("Roboto", 14, "bold")).pack(anchor="w", pady=(0, 4))
        self.entry_diseno = CTkEntry(zona5, height=32)
        self.entry_diseno.pack(fill="x")
        self.entry_diseno.configure(state="readonly")

        # ZONA 6: Cantidad + Botones
        zona6 = CTkFrame(self.body_frame, fg_color="transparent")
        zona6.pack(fill="x", padx=10, pady=(10, 5))

        CTkLabel(zona6, text="Cantidad", font=("Roboto", 14, "bold")).pack(side="left", padx=(0, 6))
        self.entry_cantidad = CTkEntry(zona6, width=80, height=32)
        self.entry_cantidad.pack(side="left", padx=(0, 20))

        self.btn_guardar = ButtonFactory.create_button(
            zona6,
            text="GUARDAR Y CONTINUAR",
            style_key="action_success",
            command=self._on_guardar
        )
        self.btn_guardar.pack(side="right", padx=6)

        self.btn_cancelar = ButtonFactory.create_button(
            zona6,
            text="CANCELAR",
            style_key="action_danger",
            command=self._on_cancelar
        )
        self.btn_cancelar.pack(side="right", padx=6)

    def _setup_tab_navigation(self):
        """Configura navegación Tab/Shift+Tab entre los campos en orden lógico."""
        self._tab_order = [
            self.combo_variante,
            self.combo_color,
            self.combo_talla,
            self.text_comentarios,
            self.entry_escudo,
            self.entry_buscar_diseno,
            self.entry_cantidad,
            self.btn_guardar,
            self.btn_cancelar,
        ]

        self._widget_map = {}
        for w in self._tab_order:
            if hasattr(w, 'entry') and hasattr(w.entry, '_entry'):
                self._widget_map[str(w.entry._entry)] = w
            elif hasattr(w, '_entry'):
                self._widget_map[str(w._entry)] = w
            elif hasattr(w, '_canvas'):
                self._widget_map[str(w._canvas)] = w
                if hasattr(w, '_text_label'):
                    self._widget_map[str(w._text_label)] = w
            else:
                self._widget_map[str(w)] = w

        def on_tab(event):
            current_tk = str(event.widget)
            current_obj = self._widget_map.get(current_tk)

            if current_obj in self._tab_order:
                idx = self._tab_order.index(current_obj)

                if event.state & 0x1:
                    next_idx = (idx - 1) % len(self._tab_order)
                else:
                    next_idx = (idx + 1) % len(self._tab_order)

                next_obj = self._tab_order[next_idx]

                if hasattr(next_obj, 'entry'):
                    next_obj.entry.focus_set()
                    try: next_obj.entry._entry.selection_range(0, 'end')
                    except: pass
                elif hasattr(next_obj, '_entry'):
                    next_obj.focus_set()
                    try: next_obj._entry.selection_range(0, 'end')
                    except: pass
                else:
                    next_obj.focus_set()

                return 'break'
            return None

        for w in self._tab_order:
            if hasattr(w, 'entry'):
                w.entry._entry.bind('<Tab>', on_tab)
                w.entry._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_entry'):
                w._entry.bind('<Tab>', on_tab)
                w._entry.bind('<Shift-Tab>', on_tab)
            elif hasattr(w, '_canvas'):
                w._canvas.bind('<Tab>', on_tab)
                w._canvas.bind('<Shift-Tab>', on_tab)
                if hasattr(w, '_text_label'):
                    w._text_label.bind('<Tab>', on_tab)
                    w._text_label.bind('<Shift-Tab>', on_tab)
            else:
                w.bind('<Tab>', on_tab)
                w.bind('<Shift-Tab>', on_tab)

        import tkinter as _tk
        def disable_frame_focus(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ctk.CTkFrame, _tk.Frame)):
                    try: child.configure(takefocus=0)
                    except: pass
                    disable_frame_focus(child)
        disable_frame_focus(self)

    # ----------------- Carga y estado -----------------

    def _cargar_siguiente_producto(self):
        if self.indice_actual >= len(self.productos_pendientes):
            self._finalizar()
            return

        self.producto_actual = self.productos_pendientes[self.indice_actual]
        nombre = self.producto_actual.get('nombre', '')
        self.lbl_titulo.configure(text=f"Reposición de '{nombre}'")

        # Limpiar selecciones previas
        self.diseno_seleccionado = None
        self.entry_diseno.configure(state="normal")
        self.entry_diseno.delete(0, "end")
        self.entry_diseno.configure(state="readonly")
        self.text_comentarios.delete("1.0", "end")
        self.check_encargo.deselect()
        self.check_escudo.deselect()
        self.entry_escudo.delete(0, "end")
        self.entry_escudo.configure(state="disabled")

        # Producto y Tipo vía servicios (sin queries directas aquí)
        prod_id = self.producto_actual.get('producto_id')
        tipo_id = None
        tipo_nombre = ""
        try:
            full = self.producto_service.get_producto_completo(prod_id) if prod_id else None
            if full:
                tipo_id = full.get('tipo')
                tipo_nombre = full.get('tipo_nombre') or ""
        except Exception:
            logger.exception("Error obteniendo producto completo via service")

        self.tipo_actual = self.tipos_service.obtener_por_id(tipo_id) if tipo_id else None

        # Rellenar nombre producto (readonly)
        self.entry_producto.configure(state="normal")
        self.entry_producto.delete(0, "end")
        self.entry_producto.insert(0, nombre.upper())
        self.entry_producto.configure(state="readonly")

        # Rellenar tipo (readonly)
        self.entry_tipo.configure(state="normal")
        self.entry_tipo.delete(0, "end")
        if self.tipo_actual:
            self.entry_tipo.insert(0, self.tipo_actual.nombre.upper())
        else:
            self.entry_tipo.insert(0, (tipo_nombre or "SIN TIPO").upper())
        self.entry_tipo.configure(state="readonly")

        # Variantes FILTRADAS por la tabla produccion_variantes_productos para este producto
        if self.tipo_actual:
            try:
                # Obtener variantes vinculadas a este producto TPV
                links = self.variante_producto_repo.get_por_producto_combinacion(prod_id)
                
                if links:
                    # Usar solo las variantes vinculadas
                    opciones = []
                    for l in links:
                        # Necesitamos el nombre de la variante (ya viene en el link o lo buscamos)
                        nombre_v = l.variante_nombre
                        if not nombre_v:
                            v_obj = self.variantes_service.obtener_por_id(l.variante_id)
                            nombre_v = v_obj.nombre if v_obj else f"ID {l.variante_id}"
                        opciones.append((l.variante_id, nombre_v))
                    self.combo_variante.set_options(opciones)
                else:
                    # Si no hay links específicos, fallback a todas las del tipo (opcional, 
                    # pero según el usuario debería filtrar, así que mejor vacío o aviso)
                    variantes = self.variantes_service.obtener_por_tipo(self.tipo_actual.id)
                    self.combo_variante.set_options([(v.id, v.nombre) for v in variantes])
            except Exception:
                logger.exception("Error cargando variantes por producto")
                self.combo_variante.set_options([])
        else:
            self.combo_variante.set_options([])

        self.combo_variante.clear()
        self.combo_talla.clear()
        self.combo_color.clear()

        # Talla / Color condicionales + carga inicial (vacía hasta elegir variante)
        self._actualizar_opciones_tipo()

        # Auto-selección de variante única (después de _actualizar_opciones_tipo para no borrar colores)
        variantes_opciones = self.combo_variante._opts if hasattr(self.combo_variante, '_opts') else []
        if len(variantes_opciones) == 1:
            self.combo_variante.set_by_id(variantes_opciones[0][0])
            self._on_variante_changed(variantes_opciones[0][1])

        # Cantidad
        self.entry_cantidad.delete(0, "end")
        self.entry_cantidad.insert(0, str(int(self.producto_actual.get('cantidad', 1))))

        # Refrescar lista de diseños
        try:
            self.design_list.search("")
        except Exception:
            pass

        # Pre-cargar datos si es edición de línea existente
        if self.linea_existente:
            self._pre_cargar_linea_existente()

        # FOCO en Variante
        self.after(120, self._enfocar_variante)

    def _enfocar_variante(self):
        try:
            if hasattr(self.combo_variante, 'entry') and hasattr(self.combo_variante.entry, 'focus_set'):
                self.combo_variante.entry.focus_set()
            elif hasattr(self.combo_variante, 'focus_set'):
                self.combo_variante.focus_set()
        except Exception:
            pass

    def _pre_cargar_linea_existente(self):
        le = self.linea_existente
        if not le: return
        if le.get("variante_id"):
            self.combo_variante.set_by_id(le["variante_id"])
            self._on_variante_changed(None)
        if le.get("color_id"):
            self.combo_color.set_by_id(le["color_id"])
            self._on_color_changed(None)
        if le.get("talla_id"):
            self.combo_talla.set_by_id(le["talla_id"])
        dc = le.get("diseno_codigo")
        if dc:
            try:
                d = self.disenos_service.obtener_por_codigo(dc)
                if d:
                    self.diseno_seleccionado = d
                    self.entry_diseno.configure(state="normal")
                    self.entry_diseno.delete(0, "end")
                    self.entry_diseno.insert(0, f"{d.codigo} - {d.nombre}")
                    self.entry_diseno.configure(state="readonly")
            except Exception: pass
        if le.get("comentarios"):
            self.text_comentarios.insert("1.0", le["comentarios"])
        if le.get("encargo"):
            self.check_encargo.select()
        if le.get("escudo"):
            self.check_escudo.select()
            self.entry_escudo.configure(state="normal")
            self.entry_escudo.insert(0, le["escudo"])

    def _on_variante_changed(self, value):
        """Al cambiar variante, filtramos colores por tipo + variante usando Matriz 3D (libro recetas)."""
        if not self.tipo_actual:
            return

        variante_id = self.combo_variante.get_id()
        if not variante_id:
            self.combo_color.set_options([])
            self.combo_talla.set_options([])
            return

        try:
            # Obtener IDs de colores permitidos en la matriz 3D (produccion_tipo_color_tallas)
            color_ids = self.relaciones_repo.get_colores_id_por_tipo_3d(self.tipo_actual.id, variante_id)
            
            if color_ids:
                colores_obj = []
                for cid in color_ids:
                    c = self.colores_service.obtener_por_id(cid)
                    if c: colores_obj.append(c)
                # Ordenar por nombre
                colores_obj.sort(key=lambda x: x.nombre)
                self.combo_color.set_options([(c.id, c.nombre) for c in colores_obj])
            else:
                self.combo_color.set_options([])
            
            # Limpiar tallas hasta que elijan color (no hace falta clear() del texto si está vacío)
            self.combo_talla.set_options([])
            
            self.update_idletasks()
        except Exception:
            logger.exception("Error actualizando colores por variante (3D)")

    def _on_color_changed(self, value):
        """Al cambiar color, filtramos tallas por tipo + variante + color usando Matriz 3D."""
        if not self.tipo_actual:
            return

        variante_id = self.combo_variante.get_id()
        color_id = self.combo_color.get_id()

        if not variante_id or not color_id:
            self.combo_talla.set_options([])
            return

        try:
            # Obtener IDs de tallas permitidas en la matriz 3D
            talla_ids = self.relaciones_repo.get_tallas_id_por_tipo_color_3d(self.tipo_actual.id, color_id, variante_id)
            
            if talla_ids:
                tallas_obj = []
                for tid in talla_ids:
                    t = self.tallas_service.repository.get_por_id(tid) 
                    if t: tallas_obj.append(t)
                # Ordenar por orden de la talla
                tallas_obj.sort(key=lambda x: x.orden)
                self.combo_talla.set_options([(t.id, t.nombre) for t in tallas_obj])
            else:
                self.combo_talla.set_options([])
            
            self.update_idletasks()
        except Exception:
            logger.exception("Error actualizando tallas por color (3D)")

    def _on_talla_changed(self, value):
        pass

    def _toggle_escudo(self):
        if self.check_escudo.get():
            self.entry_escudo.configure(state="normal")
            self.entry_escudo.focus_set()
        else:
            self.entry_escudo.delete(0, "end")
            self.entry_escudo.configure(state="disabled")

    def _actualizar_opciones_tipo(self):
        """Ajusta visibilidad de combos Talla/Color según el tipo del producto."""
        requiere_talla = bool(getattr(self.tipo_actual, 'requiere_talla', False)) if self.tipo_actual else False
        requiere_color = bool(getattr(self.tipo_actual, 'requiere_color', False)) if self.tipo_actual else False

        if requiere_talla:
            self.lbl_talla.grid()
            self.combo_talla.grid()
        else:
            self.lbl_talla.grid_remove()
            self.combo_talla.grid_remove()
        
        self.combo_talla.set_options([])
        self.combo_talla.clear()

        if requiere_color:
            self.lbl_color.grid()
            self.combo_color.grid()
        else:
            self.lbl_color.grid_remove()
            self.combo_color.grid_remove()
            
        self.combo_color.set_options([])
        self.combo_color.clear()

    # ----------------- Búsqueda y selección de diseños -----------------

    def _buscar_disenos(self, texto: str) -> List[Any]:
        try:
            if texto and texto.strip():
                return self.disenos_service.buscar(texto.strip())
            return self.disenos_service.obtener_activos()
        except Exception:
            return []

    def _map_diseno(self, d: Any) -> dict:
        try:
            col = self.colecciones_repo.get_por_id(d.coleccion_id)
            suf = self.sufijos_repo.get_por_id(d.sufijo_id) if getattr(d, 'sufijo_id', None) else None
            tipos_nombres = ""
            try:
                # Si el modelo tiene lista de tipos, mostramos nombres básicos
                if getattr(d, 'tipos', None):
                    # Intentamos resolver nombres rápidos (evitamos queries pesadas aquí)
                    tipos_nombres = ", ".join([str(tid) for tid in d.tipos])
            except Exception:
                tipos_nombres = ""
            return {
                "codigo": getattr(d, 'codigo', '') or "",
                "nombre": getattr(d, 'nombre', '') or "",
                "coleccion_nombre": col.nombre if col else "",
                "sufijo_nombre": suf.nombre if suf else "",
                "tipos_nombres": tipos_nombres,
                "total_producido": 0,
                "_obj": d,
            }
        except Exception:
            return {"codigo": "", "nombre": str(d), "coleccion_nombre": "", "sufijo_nombre": "", "tipos_nombres": "", "total_producido": 0, "_obj": d}

    def _on_buscar_diseno_enter(self, event=None):
        texto = self.entry_buscar_diseno.get()
        try:
            self.design_list.search(texto)
        except Exception:
            pass
        try:
            nav = getattr(self.design_list, 'nav_list', None)
            if nav:
                nav._canvas.focus_set()
        except Exception:
            pass
        return "break"

    def _on_diseno_double_click(self, data: dict):
        diseno = data.get("_obj") if data else None
        if not diseno:
            return
        self.diseno_seleccionado = diseno
        display = f"{getattr(diseno, 'codigo', '')} - {getattr(diseno, 'nombre', '')}".strip(" -")
        self.entry_diseno.configure(state="normal")
        self.entry_diseno.delete(0, "end")
        self.entry_diseno.insert(0, display)
        self.entry_diseno.configure(state="readonly")

    def _on_diseno_return(self):
        nav = getattr(self.design_list, 'nav_list', None)
        if nav:
            data = nav.get_selected_data()
            if data:
                self._on_diseno_double_click(data)

    # ----------------- Guardar / Cancelar -----------------

    def _on_guardar(self):
        if not self.producto_actual:
            return

        # Validaciones mínimas
        variante_id = self.combo_variante.get_id()
        if not variante_id:
            show_warning(self.winfo_toplevel(), "DEBES SELECCIONAR UNA VARIANTE")
            return

        # El diseño es opcional: si no se selecciona, se guarda como None
        # (el usuario puede añadir comentarios describiendo el diseño pendiente)

        try:
            cantidad = int(self.entry_cantidad.get().strip() or "1")
            if cantidad <= 0:
                raise ValueError()
        except Exception:
            show_warning(self.winfo_toplevel(), "CANTIDAD INVÁLIDA")
            return

        requiere_talla = bool(getattr(self.tipo_actual, 'requiere_talla', False)) if self.tipo_actual else False
        requiere_color = bool(getattr(self.tipo_actual, 'requiere_color', False)) if self.tipo_actual else False

        talla_id = self.combo_talla.get_id() if requiere_talla else None
        color_id = self.combo_color.get_id() if requiere_color else None

        diseno_codigo = getattr(self.diseno_seleccionado, 'codigo', None)

        comentarios = self.text_comentarios.get("1.0", "end").strip()

        escudo_texto = ""
        if self.check_escudo.get():
            escudo_texto = self.entry_escudo.get().strip()

        datos = {
            "producto_id": self.producto_actual.get("producto_id"),
            "nombre": self.producto_actual.get("nombre"),
            "tipo_id": self.tipo_actual.id if self.tipo_actual else None,
            "variante_id": variante_id,
            "talla_id": talla_id,
            "color_id": color_id,
            "diseno_codigo": diseno_codigo,
            "cantidad": cantidad,
            "comentarios": comentarios,
            "encargo": bool(self.check_encargo.get()),
            "escudo": escudo_texto,
            "ticket_id": self.ticket_id,
        }

        try:
            store = ReposicionStore()
            if self._linea_edit_id:
                store.borrar(self._linea_edit_id)
            ok = store.añadir(datos)
            if not ok:
                show_error(self.winfo_toplevel(), "ERROR AL GUARDAR EN REPOS (JSON)")
                return
            # Borrar del temporal si estaba pendiente
            store.borrar_pendiente_temp(datos["producto_id"], self.ticket_id)
        except Exception:
            logger.exception("Error guardando en ReposicionStore")
            show_error(self.winfo_toplevel(), "ERROR AL GUARDAR")
            return

        show_success(self.winfo_toplevel(), "REPOSICIÓN ANOTADA")

        # Siguiente o fin (con pequeño retraso para que el toast sea visible)
        self.indice_actual += 1
        self.after(400, self._cargar_siguiente_producto)

    def _on_cancelar(self):
        # Guardar productos restantes en el temporal
        restantes = self.productos_pendientes[self.indice_actual:]
        if restantes:
            try:
                store = ReposicionStore()
                store.guardar_pendientes_temp(self.ticket_id, restantes)
            except Exception:
                logger.exception("Error guardando restantes en temp")
        self._finalizar()

    def _finalizar(self):
        if self.callback_finalizar:
            try:
                self.callback_finalizar()
            except Exception:
                pass
        if self.view and hasattr(self.view, "pop_subview"):
            try:
                self.view.pop_subview()
            except Exception:
                pass
        else:
            try:
                self.destroy()
            except Exception:
                pass

