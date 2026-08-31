"""Vista de gestión de Stock Base para producción.

Permite ver y editar el inventario de materiales en blanco (camisetas, tazas, etc.)
con sus SKUs de Shopify, colores, tallas y variantes.
"""
import logging
import customtkinter as ctk
from typing import List, Dict, Any, Optional

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.virtual_nav_list import VirtualNavList
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.utils.dialogs import show_error
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion, get_font

logger = logging.getLogger(__name__)

class ProduccionStockBaseView:
	"""UI para gestionar el stock base de producción."""

	def __init__(self, parent, db, on_cerrar=None, owner=None):
		self.parent = parent
		self.db = db
		self.on_cerrar = on_cerrar
		self.owner = owner
		self.service = ProduccionStockBaseService(db)
		self.tipos_service = ProduccionTiposService(db)
		
		# Cargar configuración visual
		self.config = cargar_config_produccion()
		self.colors = self.config.get("colores", {})
		self._chip_cfg = self.config.get("chips", {}).get("diseno", {})
		self._selected_chip = None
		self._tipo_filtro = None
		self._sort_column = None
		self._sort_direction = 'asc'
		
		# Estado de la vista: 'lista' o 'formulario'
		self._view_state = 'lista'
		self._current_content = None
		
		self.container = ctk.CTkFrame(parent, fg_color="transparent")
		self.container.pack(fill="both", expand=True)

		# Vincular botón Power/Esc: la ProduccionView busca _volver en los hijos directos de central_area.
		# Como self.container es el hijo directo, le asignamos un manejador persistente que delega según el estado.
		self.container._volver = self._on_volver_proxied
		
		self.show_lista()

	def _destruir_current(self):
		"""Destruir el contenido actual (lista frame o flow)."""
		if self._current_content:
			try:
				self._current_content.destroy()
			except AttributeError:
				self._current_content.destruir()

	def show_lista(self):
		"""Mostrar la tabla de stock."""
		self._destruir_current()
		
		self._view_state = 'lista'
		if self.owner and hasattr(self.owner, 'actualizar_ruta'):
			self.owner.actualizar_ruta('PRODUCCIÓN / STOCK BASES')
		
		# Frame para la lista
		lista_frame = ctk.CTkFrame(self.container, fg_color="transparent")
		lista_frame.pack(fill="both", expand=True)
		self._current_content = lista_frame

		# Header
		header = ctk.CTkFrame(lista_frame, fg_color="transparent")
		header.pack(fill="x", padx=20, pady=(10, 5))
		
		titulo = ctk.CTkLabel(
			header, 
			text="STOCK BASES (MATERIAL EN BLANCO)", 
			font=("Courier New", 24, "bold"),
			text_color=self.colors.get("texto_principal", "#FFFFFF")
		)
		titulo.pack(side="left")
		
		# Botones de acción arriba
		btn_frame = ctk.CTkFrame(header, fg_color="transparent")
		btn_frame.pack(side="right")
		
		self.btn_nuevo = ButtonFactory.create_button(
			btn_frame, 
			text="+ NUEVA BASE", 
			command=self.show_formulario,
			module="produccion",
			palette_key="secondary",
			style_key="action_secondary"
		)
		self.btn_nuevo.pack(side="left", padx=5)

		self.btn_export_pdf = ButtonFactory.create_button(
			btn_frame,
			text="Exportar PDF",
			command=self._on_exportar_pdf,
			module="produccion",
			palette_key="secondary",
			style_key="action_secondary"
		)
		self.btn_export_pdf.pack(side="left", padx=5)

		self.btn_costes = ButtonFactory.create_button(
			btn_frame,
			text="COSTES",
			command=self.show_costes,
			module="produccion",
			palette_key="secondary",
			style_key="action_secondary"
		)
		self.btn_costes.pack(side="left", padx=5)

		# Fila de chips de tipos
		self._crear_chips_tipos(lista_frame)

		# Tabla de stock
		columnas = [
			("ARTÍCULO", 150),
			("VARIANTE", 144),
			("COLOR", 112),
			("TALLA", 80),
			("SKU SHOPIFY", 162, True),
			("CANTIDAD", 100)
		]
		
		root = lista_frame.winfo_toplevel()
		km = getattr(root, 'keyboard_manager', None)

		self.tabla = VirtualNavList(
			lista_frame,
			columns=columnas,
			module_name="produccion",
			keyboard_manager=km,
			on_double_click=self._on_item_double_click
		)
		self.tabla.pack(fill="both", expand=True, padx=20, pady=10)
		
		self._cargar_datos()

	def _crear_chips_tipos(self, parent_frame):
		"""Crear fila de chips para filtrar por tipo."""
		chips_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
		chips_frame.pack(fill="x", padx=20, pady=(0, 5))

		tipos = self.tipos_service.obtener_activos()
		tipos_con_stock = set(self.service.obtener_tipos_con_stock())
		tipos = [t for t in tipos if t.id in tipos_con_stock]
		self._chip_buttons = []

		default_cfg = self._chip_cfg.get("default", {})
		selected_cfg = self._chip_cfg.get("selected", {})
		cols = 10

		container = ctk.CTkFrame(chips_frame, fg_color="transparent")
		container.pack(fill="x")
		for c in range(cols):
			container.grid_columnconfigure(c, weight=1)

		# Chip TODOS
		is_todos_selected = (self._tipo_filtro is None)
		cfg_todos = selected_cfg if is_todos_selected else default_cfg
        
		btn_todos = ctk.CTkButton(
			container, text="TODOS",
			width=0, height=32, corner_radius=16,
			fg_color=cfg_todos.get("bg", "#552583" if is_todos_selected else "#1a1a2e"),
			text_color=cfg_todos.get("text", "#ffffff" if is_todos_selected else "#e0e0e0"),
			border_color=cfg_todos.get("border", "#C77BFF" if is_todos_selected else "#552583"),
			border_width=cfg_todos.get("border_width", 2 if is_todos_selected else 1),
			hover_color=cfg_todos.get("hover", "#8e44ad" if is_todos_selected else "#C77BFF"),
			font=get_font(self.config, "button_small") if "button_small" in self.config.get("fonts", {}) else (None, 12),
			cursor="hand2"
		)
		btn_todos.grid(row=0, column=0, padx=3, pady=3, sticky="ew")
		btn_todos.bind("<Button-1>", lambda e, b=btn_todos: self._on_chip_click(b, None))
		self._chip_buttons.append(btn_todos)
		if is_todos_selected:
			self._selected_chip = btn_todos

		for idx, tipo in enumerate(tipos, start=1):
			is_selected = (self._tipo_filtro == tipo.id)
			cfg = selected_cfg if is_selected else default_cfg
            
			btn = ctk.CTkButton(
				container, text=tipo.nombre,
				width=0, height=32, corner_radius=16,
				fg_color=cfg.get("bg", "#552583" if is_selected else "#1a1a2e"),
				text_color=cfg.get("text", "#ffffff" if is_selected else "#e0e0e0"),
				border_color=cfg.get("border", "#C77BFF" if is_selected else "#552583"),
				border_width=cfg.get("border_width", 2 if is_selected else 1),
				hover_color=cfg.get("hover", "#8e44ad" if is_selected else "#C77BFF"),
				font=get_font(self.config, "button_small") if "button_small" in self.config.get("fonts", {}) else (None, 12),
				cursor="hand2"
			)
			row = idx // cols
			col = idx % cols
			btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
			btn.bind("<Button-1>", lambda e, b=btn, t=tipo: self._on_chip_click(b, t))
			self._chip_buttons.append(btn)
			if is_selected:
				self._selected_chip = btn

	def _on_chip_click(self, btn, tipo):
		"""Filtrar la tabla por tipo al pulsar un chip."""
		default_cfg = self._chip_cfg.get("default", {})
		selected_cfg = self._chip_cfg.get("selected", {})
		if self._selected_chip is not None:
			try:
				self._selected_chip.configure(
					fg_color=default_cfg.get("bg", "#1a1a2e"),
					text_color=default_cfg.get("text", "#e0e0e0"),
					border_color=default_cfg.get("border", "#552583"),
					hover_color=default_cfg.get("hover", "#C77BFF"),
					border_width=default_cfg.get("border_width", 1)
				)
			except Exception:
				pass
		self._selected_chip = btn
		self._tipo_filtro = tipo.id if tipo else None
		try:
			btn.configure(
				fg_color=selected_cfg.get("bg", "#552583"),
				text_color=selected_cfg.get("text", "#ffffff"),
				border_color=selected_cfg.get("border", "#C77BFF"),
				hover_color=selected_cfg.get("hover", "#8e44ad"),
				border_width=selected_cfg.get("border_width", 2)
			)
		except Exception:
			pass
		self._cargar_datos()

	def show_formulario(self, item_data=None):
		"""Mostrar el flow de entrada de stock con chips."""
		self._destruir_current()

		self._view_state = 'flow'

		from .stock_base.stock_base_flow import StockBaseFlow
		self._current_content = StockBaseFlow(
			self.container,
			db=self.db,
			on_cerrar=self.show_lista,
			on_guardado=self._on_guardado_flow,
			item_data=item_data
		)

	def show_costes(self):
		"""Mostrar la consulta de costes por variante."""
		self._destruir_current()
		
		self._view_state = 'costes'
		if self.owner and hasattr(self.owner, 'actualizar_ruta'):
			self.owner.actualizar_ruta('PRODUCCIÓN / STOCK BASES / COSTES')
		
		from .produccion_stock_variante_costes import ProduccionStockVarianteCostesView
		self.costes_view = ProduccionStockVarianteCostesView(
			self.container,
			db=self.db,
			on_cerrar=self.show_lista
		)
		self._current_content = self.costes_view.frame

	def _on_volver_proxied(self):
		"""Manejador centralizado de volver que delega según el estado de la vista."""
		if self._view_state == 'costes' and hasattr(self, 'costes_view'):
			self.show_lista()
		elif self._view_state == 'flow' and self._current_content:
			# El flow suele tener su propia lógica de volver, si no, cerramos
			if hasattr(self._current_content, '_on_volver_flow'):
				self._current_content._on_volver_flow()
			else:
				self.show_lista()
		else:
			# Por defecto (lista), cerramos la vista completa (vuelve al menú principal)
			self.destruir()

	def _on_guardado_flow(self):
		"""Refrescar la lista tras guardar una variante desde el flow."""
		self.show_lista()

	def _cargar_datos(self):
		"""Cargar los datos del servicio en la tabla persistiendo el orden."""
		try:
			# 1. Preservar estado de ordenación actual si existe
			if hasattr(self, 'tabla'):
				self._sort_column = self.tabla._sort_column
				self._sort_direction = self.tabla._sort_direction

			items = self.service.listar_todo()
			if self._tipo_filtro is not None:
				items = [it for it in items if it.get("tipo_id") == self._tipo_filtro]
			self._items_filtrados = items
			rows = []
			for it in items:
				rows.append({
					"ARTÍCULO": it["tipo"],
					"VARIANTE": it.get("variante", "-"),
					"COLOR": it["color"],
					"TALLA": it["talla"],
					"_sort_TALLA": it.get("talla_orden", 999),
					"SKU SHOPIFY": it["sku"],
					"CANTIDAD": str(it["cantidad"]),
					"_raw": it
				})
			
			self.tabla.set_items(rows)
			
			# 2. Restaurar ordenación
			if self._sort_column:
				self.tabla._sort_column = self._sort_column
				self.tabla._sort_direction = self._sort_direction
				self.tabla._sort_data()
				self.tabla._update_header_indicators()
				self.tabla._refresh_ui()

		except Exception:
			logger.exception("Error cargando tabla de stock base")

	def _on_exportar_pdf(self):
		"""Exportar la lista actual (filtrada o completa) a PDF."""
		try:
			items = getattr(self, '_items_filtrados', None)
			if not items:
				ToastWidget.show(self.container, "No hay datos para exportar", tipo='warning')
				return

			from datetime import datetime
			from kool_tpv.modulos.informes.exportadores.exportador_pdf_informes import ExportadorPDFInformes

			titulo = 'STOCK BASE - PRODUCCIÓN'
			if self._tipo_filtro is not None:
				nombre_tipo = next((it['tipo'] for it in items if it.get('tipo_id') == self._tipo_filtro), '')
				if nombre_tipo:
					titulo = f'STOCK BASE - {nombre_tipo.upper()}'

			rows = []
			for it in items:
				rows.append([
					it.get('tipo', ''),
					it.get('variante', '-'),
					it.get('color', '-'),
					it.get('talla', '-'),
					it.get('sku', ''),
					str(it.get('cantidad', 0))
				])

			report_data = {
				'title': titulo,
				'generated_at': datetime.now().strftime('%d-%m-%Y %H:%M'),
				'sections': [{
					'type': 'table',
					'headers': ['Artículo', 'Variante', 'Color', 'Talla', 'SKU Shopify', 'Cantidad'],
					'rows': rows
				}]
			}

			exportador = ExportadorPDFInformes(self.db)
			resultado = exportador.exportar(report_data, self.container.winfo_toplevel())

			if resultado:
				ToastWidget.show(self.container, 'PDF exportado correctamente', tipo='success', duracion_ms=2500)
		except Exception:
			logger.exception('Error exportando PDF de stock base')
			ToastWidget.show(self.container, 'Error al exportar PDF', tipo='error')

	def _on_item_double_click(self, item_data):
		"""Acción al hacer doble clic en una fila (editar variante)."""
		raw_data = item_data.get("_raw")
		self.show_formulario(item_data=raw_data)

	def destruir(self):
		"""Cerrar la vista."""
		if self.on_cerrar:
			self.on_cerrar()
		self.container.destroy()

	def get_widget(self):
		return self.container
