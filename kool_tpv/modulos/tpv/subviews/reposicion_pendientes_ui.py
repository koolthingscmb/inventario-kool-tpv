import customtkinter as ctk
import logging
from typing import List, Dict, Optional, Any

from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore
from kool_tpv.utils.widgets.notificaciones import show_success, show_error, show_info
from kool_tpv.base_datos.producto_service import ProductoService

from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService

logger = logging.getLogger(__name__)

class ReposicionPendientesUI(ctk.CTkFrame):
    def __init__(self, parent, db, carrito_service=None, view=None):
        super().__init__(parent)
        self.db = db
        self.carrito_service = carrito_service
        self.view = view # TpvView
        
        self.store = ReposicionStore()
        self.producto_service = ProductoService(db)
        self.variantes_service = ProduccionTiposVariantesService(db)
        self.tallas_service = ProduccionTallasService(db)
        self.colores_service = ProduccionColoresService(db)
        self.disenos_service = ProduccionDisenosService(db)
        self.selected_items = []  # Lista para multi-select
        
        self._setup_ui()
        self.refrescar()

    def _setup_ui(self):
        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header.pack(side="top", fill="x", padx=10, pady=5)
        self.header.pack_propagate(False)
        
        ctk.CTkLabel(self.header, text="REPOSICIONES PENDIENTES", font=("Roboto", 20, "bold")).pack(side="left", padx=10)
        
        # Leyenda de iconos
        leyenda = ctk.CTkLabel(
            self.header,
            text="⚠️ Faltan datos   ◆ Escudo   📝 Revisar diseño   📦 Encargo",
            font=("Roboto", 14),
            text_color="gray60"
        )
        leyenda.pack(side="left", padx=(20, 0))

        # NavList
        # Ajustamos anchos para que quepan bien
        columns = [
            ("FECHA", 78),
            ("PRODUCTO VENDIDO", 226),
            ("VARIANTE", 99),
            ("COLOR", 77),
            ("TALLA", 54),
            ("DISEÑO", 364),
            ("ℹ️", 60),
        ]
        
        self.nav_list = VirtualNavList(
            self,
            columns=columns,
            on_selection_change=self._on_selection_change,
            on_double_click=self._on_double_click,
            module_name="produccion", # Colores morados
            multi_select=True
        )
        self.nav_list.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Botón Borrar (después de nav_list para poder referenciarlo)
        self.btn_borrar = ButtonFactory.create_button(
            parent=self.header,
            text="ELIMINAR",
            command=self._on_borrar,
            style_key="action_danger",
            width=150,
            height=40
        )
        self.btn_borrar.pack(side="right", padx=10)
        self.btn_borrar.configure(state="disabled")

        # Botón Seleccionar Todo (después de nav_list para poder referenciar su método)
        self.btn_select_all = ButtonFactory.create_button(
            parent=self.header,
            text="TODO",
            command=self.nav_list.select_all,
            style_key="action_primary",
            width=80,
            height=40
        )
        self.btn_select_all.pack(side="right", padx=5)

        # Bindings de teclado para borrar (usamos bind en lugar de bind_all)
        self.nav_list.bind("<Delete>", lambda e: self._on_borrar())
        self.nav_list.bind("<BackSpace>", lambda e: self._on_borrar())
        self.bind("<Delete>", lambda e: self._on_borrar())
        self.bind("<BackSpace>", lambda e: self._on_borrar())

    def refrescar(self):
        # 1. Cargar configurados (Drafts)
        configurados = self.store.cargar()
        # 2. Cargar sin configurar (Temp)
        pendientes_temp = self.store.cargar_pendientes_temp()

        if not configurados and not pendientes_temp:
            # Si no hay nada, intentamos cerrar
            if self.view and hasattr(self.view, "pop_subview"):
                self.view.pop_subview()
            return

        data = []
        
        # Procesar configurados (SI repuestos)
        for p in configurados:
            producto_id = p.get("producto_id")
            
            # Resolver nombres
            v_nombre = ""
            if p.get("variante_id"):
                v = self.variantes_service.obtener_por_id(p.get("variante_id"))
                if v: v_nombre = v.nombre
                
            c_nombre = ""
            if p.get("color_id"):
                c = self.colores_service.obtener_por_id(p.get("color_id"))
                if c: c_nombre = c.nombre
                
            t_nombre = ""
            if p.get("talla_id"):
                t = self.tallas_service.obtener_por_id(p.get("talla_id"))
                if t: t_nombre = t.nombre

            # Resolver diseño
            d_nombre = p.get("diseno_codigo", "")
            if d_nombre:
                try:
                    diseno = self.disenos_service.obtener_por_codigo(d_nombre)
                    if diseno: d_nombre = diseno.nombre
                except Exception: pass

            fecha_raw = p.get("fecha", "")
            fecha_str = ""
            if fecha_raw and len(fecha_raw) >= 10:
                partes = fecha_raw[:10].split("-")
                if len(partes) == 3:
                    fecha_str = f"{partes[2]}/{partes[1]}/{partes[0][2:]}"

            comentarios = p.get("comentarios", "")
            if d_nombre and comentarios:
                diseno_display = d_nombre
            elif not d_nombre and comentarios:
                diseno_display = comentarios
            else:
                diseno_display = d_nombre

            indic = ""
            if p.get("escudo"):
                indic += "◆"
            if comentarios:
                indic += "📝"
            if p.get("encargo"):
                indic += "📦"

            row = {
                "id": p.get("id"), # UUID del draft
                "producto_id": producto_id,
                "ticket_id": p.get("ticket_id"),
                "FECHA": fecha_str,
                "PRODUCTO VENDIDO": p.get("nombre", ""),
                "VARIANTE": v_nombre,
                "COLOR": c_nombre,
                "TALLA": t_nombre,
                "DISEÑO": diseno_display,
                "ℹ️": indic,
                "_es_temp": False
            }
            data.append(row)

        # Procesar sin configurar (NO repuestos)
        for p in pendientes_temp:
            producto_id = p.get("producto_id")
            
            # Intentar sacar el tipo del producto si podemos
            tipo_nombre = ""
            try:
                prod_data = self.producto_service.get_producto_completo(producto_id)
                if prod_data and 'tipo_nombre' in prod_data:
                    tipo_nombre = prod_data['tipo_nombre']
            except Exception:
                pass

            fecha_raw = p.get("fecha", "")
            fecha_str = ""
            if fecha_raw and len(fecha_raw) >= 10:
                partes = fecha_raw[:10].split("-")
                if len(partes) == 3:
                    fecha_str = f"{partes[2]}/{partes[1]}/{partes[0][2:]}"

            comentarios_temp = p.get("comentarios", "")
            diseno_display_temp = comentarios_temp if comentarios_temp else ""

            indic_temp = "⚠️"
            if p.get("escudo"):
                indic_temp += "◆"
            if comentarios_temp:
                indic_temp += "📝"

            row = {
                "id": p.get('temp_id') or f"temp_{producto_id}_{p.get('ticket_id')}", 
                "temp_id": p.get('temp_id'),
                "producto_id": producto_id,
                "ticket_id": p.get("ticket_id"),
                "FECHA": fecha_str,
                "PRODUCTO VENDIDO": p.get("nombre", ""),
                "VARIANTE": "",
                "COLOR": "",
                "TALLA": "",
                "DISEÑO": diseno_display_temp,
                "ℹ️": indic_temp,
                "_es_temp": True
            }
            data.append(row)
        
        self.nav_list.set_items(data)
        self.selected_items = []
        self.btn_borrar.configure(state="disabled")

    def _on_selection_change(self, indices: List[int]):
        """Handler para cambios en la selección múltiple."""
        self.selected_items = self.nav_list.get_selected_items()
        if self.selected_items:
            self.btn_borrar.configure(state="normal")
        else:
            self.btn_borrar.configure(state="disabled")

    def _on_double_click(self, item):
        if not item: return
        
        # Abrir ReposicionFormUI para este producto
        from kool_tpv.modulos.tpv.subviews.reposicion_form_ui import ReposicionFormUI
        
        producto_id = item.get("producto_id")
        ticket_id = item.get("ticket_id")
        es_temp = item.get("_es_temp", False)
        
        linea_existente = None
        if es_temp:
            for p in self.store.cargar_pendientes_temp():
                if p.get("producto_id") == producto_id and p.get("ticket_id") == ticket_id:
                    linea_existente = p
                    break
        else:
            for p in self.store.cargar():
                if p.get("id") == item.get("id"):
                    linea_existente = p
                    break

        cantidad = linea_existente.get("cantidad", 1) if linea_existente else 1

        producto_individual = {
            "producto_id": producto_id,
            "temp_id": item.get("temp_id"),
            "nombre": item.get("PRODUCTO VENDIDO"),
            "cantidad": cantidad,
        }

        form = ReposicionFormUI(
            parent=self.master,
            db=self.db,
            carrito_service=self.carrito_service,
            view=self.view,
            productos_pendientes=[producto_individual],
            ticket_id=ticket_id,
            callback_finalizar=self.refrescar,
            linea_existente=linea_existente,
        )
        
        if self.view and hasattr(self.view, "push_subview"):
            self.view.push_subview(form, f"REPOSICIÓN: {item.get('PRODUCTO VENDIDO')}")

    def _on_borrar(self):
        if not self.selected_items:
            return
            
        count = len(self.selected_items)
        if count == 1:
            item = self.selected_items[0]
            mensaje = f"¿Estás seguro de que deseas eliminar '{item.get('PRODUCTO VENDIDO')}' de la lista de pendientes?"
        else:
            mensaje = f"¿Estás seguro de que deseas eliminar {count} productos de la lista de pendientes?"
            
        from kool_tpv.utils.dialogs import MessageDialog as CustomDialog
        
        def confirmar_borrado(result):
            if result:
                success_count = 0
                for item in self.selected_items:
                    producto_id = item.get("producto_id")
                    ticket_id = item.get("ticket_id")
                    es_temp = item.get("_es_temp", False)
                    item_id = item.get("id")
                    
                    if es_temp:
                        if self.store.borrar_pendiente_temp_by_ids(producto_id, ticket_id):
                            success_count += 1
                    else:
                        if self.store.borrar(item_id):
                            success_count += 1
                
                if success_count > 0:
                    msg = "PRODUCTO ELIMINADO" if success_count == 1 else f"{success_count} PRODUCTOS ELIMINADOS"
                    show_success(self.winfo_toplevel(), msg)
                    self.refrescar()
                else:
                    show_error(self.winfo_toplevel(), "ERROR AL ELIMINAR")

        CustomDialog(
            self.winfo_toplevel(),
            titulo="ELIMINAR",
            mensaje=mensaje,
            tipo="warning",
            confirm=True,
            callback=confirmar_borrado
        )
