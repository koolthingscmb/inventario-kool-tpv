"""Diálogo para añadir o editar una variante de stock base."""
import customtkinter as ctk
import logging
from typing import Optional, Dict, List, Any

from kool_tpv.utils.dialogs.base_dialog import BaseDialog
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.factories.button_factory import ButtonFactory

logger = logging.getLogger(__name__)

class StockBaseDialog(BaseDialog):
	"""Formulario para gestionar una variante de stock base."""

	def __init__(self, parent, db, opciones: Dict[str, List[Dict[str, Any]]], 
	             item_data: Optional[Dict[str, Any]] = None, callback=None):
		self.db = db
		self.opciones = opciones
		self.item_data = item_data
		
		titulo = "EDITAR STOCK BASE" if item_data else "NUEVO STOCK BASE"
		super().__init__(parent, tipo='info', titulo=titulo, callback=callback)

	def _crear_contenido(self, container):
		"""Implementar el contenido del formulario."""
		# Frame principal del formulario
		form_frame = ctk.CTkFrame(container, fg_color="transparent")
		form_frame.pack(fill="both", expand=True, padx=20, pady=20)
		
		# Fuentes
		label_font = ("Courier New", 14, "bold")
		entry_font = ("Courier New", 14)

		# 1. Producto (Artículo)
		ctk.CTkLabel(form_frame, text="ARTÍCULO (PRODUCTO TPV):", font=label_font).grid(row=0, column=0, sticky="w", pady=(10, 0))
		opts_prod = [(p["id"], p["nombre"]) for p in self.opciones["productos"]]
		self.combo_prod = SearchableCombo(form_frame, options=opts_prod, width=350, placeholder="Selecciona artículo...")
		self.combo_prod.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))

		# 2. Género
		ctk.CTkLabel(form_frame, text="GÉNERO:", font=label_font).grid(row=2, column=0, sticky="w", pady=(10, 0))
		opts_gen = [(g["id"], g["nombre"]) for g in self.opciones["generos"]]
		self.combo_gen = SearchableCombo(form_frame, options=opts_gen, width=170, placeholder="Selecciona género...")
		self.combo_gen.grid(row=3, column=0, sticky="we", pady=(0, 10), padx=(0, 5))

		# 3. Color
		ctk.CTkLabel(form_frame, text="COLOR:", font=label_font).grid(row=2, column=1, sticky="w", pady=(10, 0))
		opts_col = [(c["id"], c["nombre"]) for c in self.opciones["colores"]]
		self.combo_col = SearchableCombo(form_frame, options=opts_col, width=170, placeholder="Selecciona color...")
		self.combo_col.grid(row=3, column=1, sticky="we", pady=(0, 10), padx=(5, 0))

		# 4. Talla y SKU
		ctk.CTkLabel(form_frame, text="TALLA:", font=label_font).grid(row=4, column=0, sticky="w", pady=(10, 0))
		self.entry_talla = ctk.CTkEntry(form_frame, font=entry_font, placeholder_text="Ej: XL, L, 40...")
		self.entry_talla.grid(row=5, column=0, sticky="we", pady=(0, 10), padx=(0, 5))

		ctk.CTkLabel(form_frame, text="SKU SHOPIFY:", font=label_font).grid(row=4, column=1, sticky="w", pady=(10, 0))
		self.entry_sku = ctk.CTkEntry(form_frame, font=entry_font, placeholder_text="SKU-XXX")
		self.entry_sku.grid(row=5, column=1, sticky="we", pady=(0, 10), padx=(5, 0))

		# 5. Cantidad
		ctk.CTkLabel(form_frame, text="CANTIDAD EN STOCK:", font=label_font).grid(row=6, column=0, sticky="w", pady=(10, 0))
		self.entry_cantidad = ctk.CTkEntry(form_frame, font=entry_font)
		self.entry_cantidad.grid(row=7, column=0, sticky="we", pady=(0, 20), padx=(0, 5))
		self.entry_cantidad.insert(0, "0")

		# Botones de acción
		actions = ctk.CTkFrame(form_frame, fg_color="transparent")
		actions.grid(row=8, column=0, columnspan=2, pady=10)
		
		self.btn_guardar = ButtonFactory.create_button(actions, text="GUARDAR", command=self._on_guardar, style_key="action_success")
		self.btn_guardar.pack(side="left", padx=10)
		
		self.btn_cancelar = ButtonFactory.create_button(actions, text="CANCELAR", command=self.destroy, style_key="action_secondary")
		self.btn_cancelar.pack(side="left", padx=10)

		# Cargar datos si es edición
		if self.item_data:
			self._cargar_datos_edicion()

	def _cargar_datos_edicion(self):
		"""Rellenar el formulario con los datos del item a editar."""
		d = self.item_data
		self.combo_prod.set_id(d.get("producto_id"))
		self.combo_gen.set_id(d.get("genero_id"))
		self.combo_col.set_id(d.get("color_id"))
		self.entry_talla.delete(0, "end")
		self.entry_talla.insert(0, d.get("talla", ""))
		self.entry_sku.delete(0, "end")
		self.entry_sku.insert(0, d.get("sku", ""))
		self.entry_cantidad.delete(0, "end")
		self.entry_cantidad.insert(0, str(d.get("cantidad", 0)))

	def _on_guardar(self):
		"""Validar y retornar datos."""
		prod_id = self.combo_prod.get_id()
		color_id = self.combo_col.get_id()
		
		if not prod_id or not color_id:
			from kool_tpv.utils.dialogs import show_error
			show_error(self, "Error", "Debes seleccionar al menos un producto y un color.")
			return

		try:
			cantidad = int(self.entry_cantidad.get())
		except ValueError:
			cantidad = 0

		data = {
			"producto_id": prod_id,
			"genero_id": self.combo_gen.get_id(),
			"color_id": color_id,
			"talla": self.entry_talla.get().strip(),
			"sku": self.entry_sku.get().strip(),
			"cantidad": cantidad
		}
		
		self.result = data
		if self.callback:
			self.callback(data)
		self.destroy()
