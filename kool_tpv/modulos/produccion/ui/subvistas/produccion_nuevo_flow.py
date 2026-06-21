"""Orquestador del flujo de nueva producción.

Contiene la clase `NuevoProduccionFlow` que gestiona la navegación entre
subvistas, el estado de la selección y la lógica de saltar pasos según
el tipo de producto (requiere_talla, requiere_color).

Flujo:
1. Producto (tipo) → 2. Talla (si requiere_talla) → 3. Color (si requiere_color)
→ 4. Diseño → 5. Cantidad → 6. Resumen

Desde Resumen: AÑADIR vuelve al paso 1, CONFIRMAR guarda la orden.
"""
import tkinter as tk
from typing import Callable, List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipos_model import ProduccionTipo
from kool_tpv.modulos.produccion.models.produccion_color_model import ProduccionColor
from kool_tpv.modulos.produccion.models.produccion_diseno_model import ProduccionDiseno
from kool_tpv.modulos.produccion.services.produccion_disenos_service import ProduccionDisenosService
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion import NuevaProduccionView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_talla import NuevaProduccionTallaView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_color import NuevaProduccionColorView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_diseno import NuevaProduccionDisenoView
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_cantidad import NuevaProduccionCantidadView, CantidadSeleccion
from kool_tpv.modulos.produccion.ui.subvistas.produccion_nueva_produccion_resumen import NuevaProduccionResumenView, ItemProduccion

# Pasos del flujo
PASO_PRODUCTO = 0
PASO_TALLA = 1
PASO_COLOR = 2
PASO_DISENO = 3
PASO_CANTIDAD = 4
PASO_RESUMEN = 5


class NuevoProduccionFlow:
	"""Orquestador del flujo de nueva producción.

	Args:
		parent: Widget padre donde se mostrará el flujo.
		db: Instancia de `Database` ya conectada.
		on_cerrar: Callback cuando se cierra el flujo (al confirmar o cancelar).
	"""

	def __init__(self, parent, db: Database, on_cerrar: Optional[Callable] = None):
		self.parent = parent
		self.db = db
		self.on_cerrar = on_cerrar

		# Servicios
		self._tipos_service = ProduccionTiposService(db)
		self._disenos_service = ProduccionDisenosService(db)

		# Estado del flujo
		self._paso_actual = PASO_PRODUCTO
		self._paso_anterior = PASO_PRODUCTO
		self._tipo: Optional[ProduccionTipo] = None
		self._talla: Optional[str] = None
		self._color: Optional[ProduccionColor] = None
		self._diseno: Optional[ProduccionDiseno] = None
		self._cantidad: Optional[CantidadSeleccion] = None
		self._items: List[ItemProduccion] = []

		# Vista activa
		self._vista_actual = None

		# Frame contenedor
		self.frame = tk.Frame(parent, bg="#2c3e50")
		self.frame.pack(fill=tk.BOTH, expand=True)

		# Iniciar en el primer paso
		self._mostrar_paso(PASO_PRODUCTO)

	# --- Navegación entre pasos ---

	def _mostrar_paso(self, paso: int):
		"""Mostrar la subvista correspondiente al paso."""
		# Destruir vista anterior
		if self._vista_actual is not None:
			try:
				self._vista_actual.destruir()
			except Exception:
				pass
			self._vista_actual = None

		self._paso_anterior = self._paso_actual
		self._paso_actual = paso

		if paso == PASO_PRODUCTO:
			self._vista_actual = NuevaProduccionView(
				self.frame,
				db=self.db,
				on_siguiente=self._on_producto_siguiente,
				on_volver=self._on_volver_flow
			)

		elif paso == PASO_TALLA:
			self._vista_actual = NuevaProduccionTallaView(
				self.frame,
				on_siguiente=self._on_talla_siguiente,
				on_volver=lambda: self._mostrar_paso(PASO_PRODUCTO)
			)

		elif paso == PASO_COLOR:
			self._vista_actual = NuevaProduccionColorView(
				self.frame,
				db=self.db,
				on_siguiente=self._on_color_siguiente,
				on_volver=self._on_color_volver
			)

		elif paso == PASO_DISENO:
			self._vista_actual = NuevaProduccionDisenoView(
				self.frame,
				db=self.db,
				on_siguiente=self._on_diseno_siguiente,
				on_volver=self._on_diseno_volver
			)

		elif paso == PASO_CANTIDAD:
			mostrar_mixta = self._es_tipo_camiseta()
			self._vista_actual = NuevaProduccionCantidadView(
				self.frame,
				on_siguiente=self._on_cantidad_siguiente,
				on_volver=self._on_cantidad_volver,
				mostrar_mixta=mostrar_mixta
			)

		elif paso == PASO_RESUMEN:
			self._vista_actual = NuevaProduccionResumenView(
				self.frame,
				on_anadir=self._on_resumen_anadir,
				on_confirmar=self._on_resumen_confirmar,
				on_volver=lambda: self._mostrar_paso(PASO_CANTIDAD)
			)
			# Si ya hay items (venimos de AÑADIR), cargarlos
			for item in self._items:
				self._vista_actual.anadir_item(item)

	# --- Callbacks de cada paso ---

	def _on_producto_siguiente(self, tipo: ProduccionTipo):
		"""Producto seleccionado → decidir siguiente paso."""
		self._tipo = tipo
		if tipo.requiere_talla == 1:
			self._mostrar_paso(PASO_TALLA)
		elif tipo.requiere_color == 1:
			self._mostrar_paso(PASO_COLOR)
		else:
			self._mostrar_paso(PASO_DISENO)

	def _on_talla_siguiente(self, talla: str):
		"""Talla seleccionada → decidir siguiente paso."""
		self._talla = talla
		if self._tipo and self._tipo.requiere_color == 1:
			self._mostrar_paso(PASO_COLOR)
		else:
			self._mostrar_paso(PASO_DISENO)

	def _on_color_volver(self):
		"""Volver desde color → ir a talla si existe, si no a producto."""
		if self._tipo and self._tipo.requiere_talla == 1:
			self._mostrar_paso(PASO_TALLA)
		else:
			self._mostrar_paso(PASO_PRODUCTO)

	def _on_color_siguiente(self, color: ProduccionColor):
		"""Color seleccionado → ir a diseño."""
		self._color = color
		self._mostrar_paso(PASO_DISENO)

	def _on_diseno_volver(self):
		"""Volver desde diseño → ir a color si existe, si no a talla, si no a producto."""
		if self._tipo and self._tipo.requiere_color == 1:
			self._mostrar_paso(PASO_COLOR)
		elif self._tipo and self._tipo.requiere_talla == 1:
			self._mostrar_paso(PASO_TALLA)
		else:
			self._mostrar_paso(PASO_PRODUCTO)

	def _on_diseno_siguiente(self, diseno: ProduccionDiseno):
		"""Diseño seleccionado → ir a cantidad."""
		self._diseno = diseno
		self._mostrar_paso(PASO_CANTIDAD)

	def _on_cantidad_volver(self):
		"""Volver desde cantidad → ir a diseño."""
		self._mostrar_paso(PASO_DISENO)

	def _on_cantidad_siguiente(self, cantidad: CantidadSeleccion):
		"""Cantidad seleccionada → crear ítem y ir a resumen."""
		self._cantidad = cantidad
		self._crear_item()
		self._mostrar_paso(PASO_RESUMEN)

	def _on_resumen_anadir(self):
		"""AÑADIR desde resumen → resetear selección y volver al paso 1."""
		self._tipo = None
		self._talla = None
		self._color = None
		self._diseno = None
		self._cantidad = None
		self._mostrar_paso(PASO_PRODUCTO)

	def _on_resumen_confirmar(self, items: List[ItemProduccion]):
		"""CONFIRMAR desde resumen → guardar orden y cerrar flujo."""
		self._items = items
		# TODO: Guardar la orden en BD via ProduccionOrdenesService
		# Por ahora solo cerramos el flujo
		self._cerrar_flow()

	def _on_volver_flow(self):
		"""VOLVER desde el paso 1 → cerrar flujo."""
		self._cerrar_flow()

	# --- Lógica de costes ---

	def _crear_item(self):
		"""Crear un ItemProduccion con los datos acumulados y calcular costes."""
		if not self._tipo:
			return

		# Coste base del tipo (en euros)
		coste_base = self._tipo.coste_base or 0.0

		# Coste del diseño para este tipo (en céntimos → euros)
		coste_diseno = 0.0
		if self._diseno:
			coste_diseno_cent = self._disenos_service.obtener_coste_por_tipo(
				self._diseno.codigo, self._tipo.nombre
			)
			coste_diseno = coste_diseno_cent / 100.0

		coste_unitario = coste_base + coste_diseno
		cantidad = self._cantidad.cantidad if self._cantidad else 0
		coste_total = coste_unitario * cantidad

		item = ItemProduccion(
			tipo_nombre=self._tipo.nombre,
			tipo_id=self._tipo.id,
			talla=self._talla,
			color_nombre=self._color.nombre if self._color else None,
			color_id=self._color.id if self._color else None,
			diseno_codigo=self._diseno.codigo if self._diseno else None,
			diseno_nombre=self._diseno.nombre if self._diseno else None,
			cantidad=cantidad,
			produccion_mixta=self._cantidad.produccion_mixta if self._cantidad else False,
			coste_unitario=coste_unitario,
			coste_total=coste_total
		)
		self._items.append(item)

	# --- Utilidades ---

	def _es_tipo_camiseta(self) -> bool:
		"""Comprobar si el tipo seleccionado es camiseta (para producción mixta)."""
		if not self._tipo:
			return False
		return self._tipo.nombre.lower() in ("camiseta", "camisetas")

	def _cerrar_flow(self):
		"""Cerrar el flujo y notificar al callback."""
		try:
			if self._vista_actual:
				self._vista_actual.destruir()
		except Exception:
			pass
		self.frame.destroy()
		if self.on_cerrar:
			self.on_cerrar()

	def destruir(self):
		"""Destruir el flujo y limpiar recursos."""
		try:
			if self._vista_actual:
				self._vista_actual.destruir()
		except Exception:
			pass
		self.frame.destroy()
