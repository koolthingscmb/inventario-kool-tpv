"""Vista de formulario para añadir o editar una variante de stock base."""
import logging
import customtkinter as ctk
from typing import Optional, Dict, List, Any

from kool_tpv.utils.factories.button_factory import ButtonFactory
from kool_tpv.utils.widgets.searchable_combo import SearchableCombo
from kool_tpv.utils.dialogs import show_error
from kool_tpv.utils.widgets.notificaciones import ToastWidget
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.modulos.produccion.ui.subvistas.config_helper import cargar_config_produccion

logger = logging.getLogger(__name__)

class ProduccionStockBaseFormView:
	"""Formulario integrado para gestionar una variante de stock base."""

	def __init__(self, parent, db, on_guardar_success=None, on_cancelar=None, item_data: Optional[Dict[str, Any]] = None):
		self.parent = parent
		self.db = db
		self.on_guardar_success = on_guardar_success
		self.on_cancelar = on_cancelar
		self.item_data = item_data
		self.service = ProduccionStockBaseService(db)
		
		# Cargar configuración visual
		self.config = cargar_config_produccion()
		self.colors = self.config.get("colores", {})
		
		self.container = ctk.CTkFrame(parent, fg_color="transparent")
		self.container.pack(fill="both", expand=True)
		
		self._setup_ui()
		if self.item_data:
			self._cargar_datos_edicion()

	def _setup_ui(self):
		"""Configurar los elementos de la interfaz."""
		# Título y botones de cabecera
		header = ctk.CTkFrame(self.container, fg_color="transparent")
		header.pack(fill="x", padx=20, pady=(10, 20))
		
		titulo_texto = "EDITAR VARIANTE DE STOCK" if self.item_data else "AÑADIR NUEVA VARIANTE DE STOCK"
		titulo = ctk.CTkLabel(
			header, 
			text=titulo_texto, 
			font=("Courier New", 22, "bold"),
			text_color=self.colors.get("texto_principal", "#FFFFFF")
		)
		titulo.pack(side="left")
		
		# Cuerpo del formulario (centrado)
		form_container = ctk.CTkFrame(self.container, fg_color="#1a1a1a", corner_radius=10)
		form_container.pack(pady=20, padx=20, fill="both", expand=True)
		
		# Grid para los campos
		form_inner = ctk.CTkFrame(form_container, fg_color="transparent")
		form_inner.place(relx=0.5, rely=0.4, anchor="center")
		
		label_font = ("Courier New", 14, "bold")
		entry_font = ("Courier New", 16)
		
		# Cargar opciones para los combos
		opciones = self.service.obtener_opciones_formulario()

		# 1. Producto
		ctk.CTkLabel(form_inner, text="ARTÍCULO / PRODUCTO:", font=label_font).grid(row=0, column=0, sticky="w", pady=(10, 0))
		opts_prod = [(p["id"], p["nombre"]) for p in opciones["productos"]]
		self.combo_prod = SearchableCombo(form_inner, options=opts_prod, width=400, placeholder="Selecciona el artículo base...")
		self.combo_prod.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 15))

		# 2. Género y Color (en la misma fila)
		ctk.CTkLabel(form_inner, text="GÉNERO:", font=label_font).grid(row=2, column=0, sticky="w", pady=(5, 0))
		opts_gen = [(g["id"], g["nombre"]) for g in opciones["generos"]]
		self.combo_gen = SearchableCombo(form_inner, options=opts_gen, width=195, placeholder="Género...")
		self.combo_gen.grid(row=3, column=0, sticky="we", pady=(0, 15), padx=(0, 5))

		ctk.CTkLabel(form_inner, text="COLOR:", font=label_font).grid(row=2, column=1, sticky="w", pady=(5, 0))
		opts_col = [(c["id"], c["nombre"]) for c in opciones["colores"]]
		self.combo_col = SearchableCombo(form_inner, options=opts_col, width=195, placeholder="Color...")
		self.combo_col.grid(row=3, column=1, sticky="we", pady=(0, 15), padx=(5, 0))

		# 3. Talla y SKU
		ctk.CTkLabel(form_inner, text="TALLA:", font=label_font).grid(row=4, column=0, sticky="w", pady=(5, 0))
		self.entry_talla = ctk.CTkEntry(form_inner, font=entry_font, height=35, placeholder_text="XL, L, 40...")
		self.entry_talla.grid(row=5, column=0, sticky="we", pady=(0, 15), padx=(0, 5))

		ctk.CTkLabel(form_inner, text="SKU SHOPIFY:", font=label_font).grid(row=4, column=1, sticky="w", pady=(5, 0))
		self.entry_sku = ctk.CTkEntry(form_inner, font=entry_font, height=35, placeholder_text="SKU-XXX")
		self.entry_sku.grid(row=5, column=1, sticky="we", pady=(0, 15), padx=(5, 0))

		# 4. Cantidad
		ctk.CTkLabel(form_inner, text="CANTIDAD EN ALMACÉN:", font=label_font).grid(row=6, column=0, sticky="w", pady=(5, 0))
		self.entry_cantidad = ctk.CTkEntry(form_inner, font=entry_font, height=35)
		self.entry_cantidad.grid(row=7, column=0, sticky="we", pady=(0, 30), padx=(0, 5))
		self.entry_cantidad.insert(0, "0")

		# Botones de acción (Abajo)
		btn_frame = ctk.CTkFrame(form_inner, fg_color="transparent")
		btn_frame.grid(row=8, column=0, columnspan=2, pady=10)
		
		self.btn_guardar = ButtonFactory.create_button(
			btn_frame, 
			text="GUARDAR CAMBIOS" if self.item_data else "CREAR VARIANTE", 
			command=self._on_guardar,
			style_key="action_success"
		)
		self.btn_guardar.pack(side="left", padx=10)
		
		self.btn_cancelar = ButtonFactory.create_button(
			btn_frame, 
			text="CANCELAR", 
			command=self._on_cancelar_click,
			style_key="action_secondary"
		)
		self.btn_cancelar.pack(side="left", padx=10)

	def _cargar_datos_edicion(self):
		"""Rellenar el formulario con los datos del item a editar."""
		d = self.item_data
		self.combo_prod.set_id(d.get("producto_id"))
		self.combo_gen.set_id(d.get("genero_id"))
		self.combo_col.set_id(d.get("color_id"))
		self.entry_talla.delete(0, "end")
		self.entry_talla.insert(0, d.get("talla", "") if d.get("talla") != "-" else "")
		self.entry_sku.delete(0, "end")
		self.entry_sku.insert(0, d.get("sku", ""))
		self.entry_cantidad.delete(0, "end")
		self.entry_cantidad.insert(0, str(d.get("cantidad", 0)))

	def _on_guardar(self):
		"""Validar y guardar los datos."""
		prod_id = self.combo_prod.get_id()
		color_id = self.combo_col.get_id()
		
		if not prod_id or not color_id:
			show_error(self.container, "Faltan datos", "Debes seleccionar un artículo y un color.")
			return

		try:
			cantidad = int(self.entry_cantidad.get())
		except ValueError:
			cantidad = 0

		success = self.service.guardar_variante(
			producto_id=prod_id,
			genero_id=self.combo_gen.get_id(),
			color_id=color_id,
			talla=self.entry_talla.get().strip(),
			sku=self.entry_sku.get().strip(),
			cantidad=cantidad
		)

		if success:
			ToastWidget.show(self.parent, "Variante guardada con éxito", tipo="success")
			if self.on_guardar_success:
				self.on_guardar_success()
		else:
			show_error(self.container, "Error", "No se pudo guardar la información en la base de datos.")

	def _on_cancelar_click(self):
		"""Cancelar y volver a la lista."""
		if self.on_cancelar:
			self.on_cancelar()

	def destruir(self):
		"""Eliminar el contenedor."""
		self.container.destroy()
