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
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion

logger = logging.getLogger(__name__)

class ProduccionStockBaseView:
	"""UI para gestionar el stock base de producción."""

	def __init__(self, parent, db, on_cerrar=None):
		self.parent = parent
		self.db = db
		self.on_cerrar = on_cerrar
		self.service = ProduccionStockBaseService(db)
		
		# Cargar configuración visual
		self.config = cargar_config_produccion()
		self.colors = self.config.get("colores", {})
		
		# Estado de la vista: 'lista' o 'formulario'
		self._view_state = 'lista'
		self._current_content = None
		
		self.container = ctk.CTkFrame(parent, fg_color="transparent")
		self.container.pack(fill="both", expand=True)
		
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
			style_key="action_success"
		)
		self.btn_nuevo.pack(side="left", padx=5)

		# Tabla de stock
		columnas = [
			("ARTÍCULO", 200),
			("VARIANTE", 120),
			("COLOR", 150),
			("TALLA", 80),
			("SKU SHOPIFY", 180),
			("CANTIDAD", 100)
		]
		
		self.tabla = VirtualNavList(
			lista_frame,
			columns=columnas,
			module_name="produccion",
			on_double_click=self._on_item_double_click
		)
		self.tabla.pack(fill="both", expand=True, padx=20, pady=10)
		
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

	def _on_guardado_flow(self):
		"""Refrescar la lista tras guardar una variante desde el flow."""
		self.show_lista()

	def _cargar_datos(self):
		"""Cargar los datos del servicio en la tabla."""
		try:
			items = self.service.listar_todo()
			rows = []
			for it in items:
				rows.append({
					"ARTÍCULO": it["tipo"],
					"VARIANTE": it.get("variante", "-"),
					"COLOR": it["color"],
					"TALLA": it["talla"],
					"SKU SHOPIFY": it["sku"],
					"CANTIDAD": str(it["cantidad"]),
					"_raw": it
				})
			self.tabla.set_items(rows)
		except Exception:
			logger.exception("Error cargando tabla de stock base")

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
