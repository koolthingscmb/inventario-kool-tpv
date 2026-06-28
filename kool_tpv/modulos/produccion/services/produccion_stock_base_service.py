"""Servicio para la gestión del stock de bases textiles y otros materiales.

Lógica de negocio para controlar el inventario de materiales en blanco,
sincronización de SKUs y disponibilidad para el taller.
"""
from typing import List, Optional, Dict, Any
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService

logger = logging.getLogger(__name__)

class ProduccionStockBaseService:
	"""Servicio para gestionar el stock base de producción.

	Args:
		db: instancia de `Database` ya conectada.
	"""

	def __init__(self, db: Database):
		self.db = db
		self.repo = ProduccionStockBaseRepository(db)

	def listar_todo(self) -> List[Dict[str, Any]]:
		"""Obtener la lista completa de stock base."""
		return self.repo.get_todos()

	def importar_stock(self, tipo_id: int, color_id: int, talla: str, 
	                   cantidad_nueva: int, coste_nuevo_eur: float,
	                   variante_id: Optional[int] = None) -> bool:
		"""Procesa la entrada de stock calculando coste medio y generando SKU si es necesario."""
		try:
			# 1. Obtener datos actuales
			stock_actual = self.repo.get_by_params(tipo_id, color_id, talla, variante_id)
			
			cant_previa = 0
			coste_medio_previo = 0
			sku = ""
			
			if stock_actual:
				cant_previa = stock_actual['cantidad'] or 0
				coste_medio_previo = stock_actual['coste_medio'] or 0
				sku = stock_actual['sku'] or ""
			
			# 2. Calcular nuevo coste medio ponderado (en céntimos)
			cant_total = cant_previa + cantidad_nueva
			coste_nuevo_cents = int(coste_nuevo_eur * 100)
			
			if cant_total > 0:
				numerador = (cant_previa * coste_medio_previo) + (cantidad_nueva * coste_nuevo_cents)
				nuevo_coste_medio = int(numerador / cant_total)
			else:
				nuevo_coste_medio = coste_nuevo_cents

			# 3. Generar SKU si no existe
			if not sku:
				sku = self.generar_sku(tipo_id, color_id, talla, variante_id)
			
			# 4. Guardar
			return self.repo.crear_o_actualizar(
				tipo_id=tipo_id,
				color_id=color_id,
				talla=talla,
				sku=sku,
				cantidad=cant_total,
				coste_medio=nuevo_coste_medio,
				variante_id=variante_id
			)
		except Exception:
			logger.exception("Error en importar_stock del servicio")
			return False

	def generar_sku(self, tipo_id: int, color_id: int, talla: str, variante_id: Optional[int] = None) -> str:
		"""Genera un SKU único basado en el patrón TIPO-VAR-COLOR-TALLA."""
		try:
			svc_tipos = ProduccionTiposService(self.db)
			svc_colores = ProduccionColoresService(self.db)
			svc_variantes = ProduccionTiposVariantesService(self.db)
			
			tipo = svc_tipos.obtener_por_id(tipo_id)
			color = svc_colores.obtener_por_id(color_id)
			
			if not tipo or not color:
				return ""
				
			def clean(s): 
				import unicodedata
				import re
				s = s.upper()
				s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii')
				s = re.sub(r'[^A-Z0-9]', '', s)
				return s

			t = clean(tipo.nombre)[:3]
			c = clean(color.nombre)[:3]
			s = clean(talla)
			
			v = ""
			if variante_id:
				variante = svc_variantes.obtener_por_id(variante_id)
				if variante:
					v = clean(variante.nombre)[:3]
			
			return f"{t}-{v}-{c}-{s}" if v else f"{t}-{c}-{s}"
		except Exception:
			logger.exception("Error generando SKU")
			return ""

	def guardar_variante(self, tipo_id: int,
	                     color_id: Optional[int], talla: str, sku: str, cantidad: int,
	                     variante_id: Optional[int] = None, coste_medio: int = 0) -> bool:
		"""Guardar o actualizar una variante de stock.
		
		Valida que los datos mínimos estén presentes.
		"""
		if not tipo_id:
			logger.error("Falta dato obligatorio (tipo) para guardar stock base")
			return False
		
		# Limpiar strings
		talla = (talla or "").strip().upper()
		sku = (sku or "").strip().upper()
		
		return self.repo.crear_o_actualizar(tipo_id, color_id, talla, sku, cantidad, coste_medio, variante_id)

	def eliminar_variante(self, id_stock: int) -> bool:
		"""Eliminar un registro de stock."""
		return self.repo.eliminar(id_stock)

	def comprobar_disponibilidad(self, tipo_id: int,
	                           color_id: int, talla: str, cantidad_requerida: int = 1,
	                           variante_id: Optional[int] = None) -> bool:
		"""Verifica si hay stock suficiente para producir."""
		stock_actual = self.repo.obtener_cantidad(tipo_id, color_id, (talla or "").strip().upper(), variante_id)
		return stock_actual >= cantidad_requerida

	def consumir_stock(self, tipo_id: int,
	                  color_id: int, talla: str, cantidad: int,
	                  variante_id: Optional[int] = None) -> bool:
		"""Descontar stock del almacén de bases."""
		if cantidad <= 0:
			return True
		return self.repo.actualizar_cantidad(tipo_id, color_id, (talla or "").strip().upper(), -cantidad, variante_id)

	def reponer_stock(self, tipo_id: int,
	                 color_id: int, talla: str, cantidad: int,
	                 variante_id: Optional[int] = None) -> bool:
		"""Añadir stock al almacén de bases."""
		if cantidad <= 0:
			return True
		return self.repo.actualizar_cantidad(tipo_id, color_id, (talla or "").strip().upper(), cantidad, variante_id)

	def obtener_opciones_formulario(self) -> Dict[str, List[Dict[str, Any]]]:
		"""Obtener listas de tipos y colores para los selectores usando servicios."""
		svc_tipos = ProduccionTiposService(self.db)
		svc_colores = ProduccionColoresService(self.db)
		
		return {
			"tipos": svc_tipos.obtener_como_dict(solo_activos=True),
			"colores": svc_colores.obtener_como_dict(solo_activos=True)
		}
