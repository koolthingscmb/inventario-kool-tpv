"""Servicio para la gestión del stock de bases textiles y otros materiales.

Lógica de negocio para controlar el inventario de materiales en blanco,
sincronización de SKUs y disponibilidad para el taller.
"""
from typing import List, Optional, Dict, Any, Tuple
import logging

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
from kool_tpv.modulos.produccion.repositories.produccion_relaciones_repository import ProduccionRelacionesRepository
from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import ProduccionTallasRepository
from kool_tpv.modulos.produccion.services.produccion_tipos_service import ProduccionTiposService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.base_datos.money_adapter import prepare_for_db

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

	def obtener_tipos_con_stock(self) -> List[int]:
		"""Obtener IDs de tipos que tienen al menos un registro de stock base."""
		return self.repo.get_tipos_con_stock()

	def obtener_stock_por_tipo_color(self, tipo_id: int, color_id: int,
	                                 variante_id: Optional[int] = None) -> Dict[str, int]:
		"""Obtener dict {talla: cantidad} para una combinación tipo+color+variante."""
		return self.repo.get_stock_por_tipo_color(tipo_id, color_id, variante_id)

	def obtener_coste_medio_variante(self, tipo_id: int,
	                                 variante_id: Optional[int] = None) -> float:
		"""Obtener el coste medio ponderado de una variante desde el stock."""
		return self.repo.get_coste_medio_variante(tipo_id, variante_id)

	def obtener_cantidad(self, tipo_id: int, color_id: Optional[int], talla: str, 
	                     variante_id: Optional[int] = None) -> int:
		"""Obtener la cantidad exacta de stock disponible."""
		# Normalizar talla: si es vacío o None, usar None para que el repo use IS NULL
		talla_norm = (talla or "").strip().upper()
		if not talla_norm:
			talla_norm = None
		return self.repo.obtener_cantidad(tipo_id, color_id, talla_norm, variante_id)

	def get_by_sku(self, sku: str, cur=None) -> Optional[Dict[str, Any]]:
		"""Obtener un registro de stock por su SKU."""
		return self.repo.get_by_sku(sku, cur=cur)

	def crear_o_actualizar(self, tipo_id: int, color_id: Optional[int], talla: str, 
	                      sku: str, cantidad: int, coste_medio: int = 0,
	                      variante_id: Optional[int] = None, talla_id: Optional[int] = None,
	                      cur=None) -> bool:
		ok = self.repo.crear_o_actualizar(tipo_id, color_id, talla, sku, cantidad, coste_medio, variante_id, talla_id, cur=cur)
		
		# Hook de Sincronización Automática
		if ok:
			self._trigger_async_sync(tipo_id, color_id, talla, variante_id, cantidad)
			
		return ok

	def _trigger_async_sync(self, tipo_id, color_id, talla, variante_id, cantidad, motivo: str = "Actualización manual"):
		"""Dispara la sincronización con Shopify en segundo plano si está activa."""
		try:
			from kool_tpv.modulos.shopify.services.shopify_config_service import ShopifyConfigService
			if ShopifyConfigService(self.db).get_config().get("sync_active"):
				sku = self.generar_sku(tipo_id, color_id, talla, variante_id)
				import threading
				from kool_tpv.modulos.shopify.services.shopify_sync_service import ShopifySyncService
				def _async():
					try:
						sync_svc = ShopifySyncService(self.db)
						res = sync_svc.sync_stock_by_sku_prefix(sku, cantidad, reason=motivo)
						
						# Mostrar Toast si la sincronización fue exitosa
						if res.get("success"):
							from kool_tpv.utils.widgets.notificaciones.toast_widget import ToastWidget
							import tkinter as tk
							try:
								# Intentamos obtener cualquier ventana activa para el toast
								def _find_root():
									# 1. Intentar por el root por defecto
									try:
										if hasattr(tk, '_default_root') and tk._default_root:
											return tk._default_root
									except: pass
									# 2. Intentar buscar en todas las ventanas abiertas
									try:
										from tkinter import _default_root
										if _default_root: return _default_root
									except: pass
									return None

								root = _find_root()
								if root:
									root.after(0, lambda: ToastWidget.show(root, f"Shopify: {sku} actualizado", tipo='success'))
							except Exception: pass
					except Exception: pass
				threading.Thread(target=_async, daemon=True).start()
		except Exception:
			logger.exception("Error en _trigger_async_sync")

	def importar_stock(self, tipo_id: int, color_id: int, talla: str, 
	                   cantidad_nueva: int, coste_nuevo_eur: float,
	                   variante_id: Optional[int] = None,
	                   talla_id: Optional[int] = None,
	                   sku_manual: Optional[str] = None,
	                   cur=None) -> bool:
		"""Procesa la entrada de stock calculando coste medio y generando SKU si es necesario."""
		try:
			# 1. Obtener datos actuales
			stock_actual = self.repo.get_by_params(tipo_id, color_id, talla, variante_id, cur=cur)
			
			cant_previa = 0
			coste_medio_previo = 0
			sku = sku_manual or ""
			
			if stock_actual:
				cant_previa = stock_actual['cantidad'] or 0
				coste_medio_previo = stock_actual['coste_medio'] or 0
				if not sku:
					sku = stock_actual['sku'] or ""
				if not talla_id:
					talla_id = stock_actual.get('talla_id')
			
			# Intentar resolver talla_id si sigue siendo None pero hay nombre de talla
			if not talla_id and talla:
				try:
					from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import ProduccionTallasRepository
					repo_t = ProduccionTallasRepository(self.db)
					# Búsqueda robusta (ignora espacios y mayúsculas)
					t_obj = repo_t.get_por_nombre_robusto(talla)
					if t_obj:
						talla_id = t_obj.id
				except Exception:
					pass
			
			# 2. Calcular nuevo coste medio ponderado (en céntimos)
			cant_total = cant_previa + cantidad_nueva
			coste_nuevo_cents = prepare_for_db(coste_nuevo_eur)
			
			if cant_total > 0:
				numerador = (cant_previa * coste_medio_previo) + (cantidad_nueva * coste_nuevo_cents)
				nuevo_coste_medio = int(numerador / cant_total)
			else:
				nuevo_coste_medio = coste_nuevo_cents

			# 3. Generar SKU si no existe
			if not sku:
				sku = self.generar_sku(tipo_id, color_id, talla, variante_id)
			
			# 4. Guardar (Usamos el repo directamente para evitar doble sync si lo pusimos en crear_o_actualizar)
			ok = self.repo.crear_o_actualizar(
				tipo_id=tipo_id,
				color_id=color_id,
				talla=talla,
				sku=sku,
				cantidad=cant_total,
				coste_medio=nuevo_coste_medio,
				variante_id=variante_id,
				talla_id=talla_id,
				cur=cur
			)
			
			# 5. Sincronizar con Shopify
			if ok:
				self._trigger_async_sync(tipo_id, color_id, talla, variante_id, cant_total, motivo="Entrada de Albarán")
				# 6. Auto-poblar la matriz si la combinación no existe
				self._asegurar_matriz(tipo_id, color_id, talla, variante_id, cur=cur)
			
			return ok
		except Exception:
			logger.exception("Error en importar_stock del servicio")
			return False

	def _asegurar_matriz(self, tipo_id: int, color_id: int, talla: str, variante_id: Optional[int] = None, cur=None):
		"""Auto-poblar la matriz produccion_tipo_color_tallas al importar stock."""
		try:
			repo_tallas = ProduccionTallasRepository(self.db)
			talla_id = None
			if talla:
				talla_obj = repo_tallas.get_por_nombre_robusto(talla)
				if talla_obj:
					talla_id = talla_obj.id
				else:
					logger.warning(f"Auto-matriz: talla '{talla}' no encontrada en catálogo oficial, se insertará como NULL")

			repo_rel = ProduccionRelacionesRepository(self.db)
			repo_rel.asegurar_relacion(tipo_id, color_id, talla_id, variante_id, cur=cur)
		except Exception:
			logger.exception("Error auto-poblando matriz")

	def generar_sku(self, tipo_id: int, color_id: Optional[int], talla: str, variante_id: Optional[int] = None) -> str:
		"""Genera un SKU único basado en el patrón para Shopify: TIPO-COLOR-VAR-TALLA.
		Ejemplo: CAM-NEGRO-HOMBRE-S
		"""
		try:
			svc_tipos = ProduccionTiposService(self.db)
			svc_colores = ProduccionColoresService(self.db)
			svc_variantes = ProduccionTiposVariantesService(self.db)
			
			tipo = svc_tipos.obtener_por_id(tipo_id)
			if not tipo:
				return ""
				
			def clean(s): 
				import unicodedata
				import re
				if not s: return ""
				s = s.upper().strip()
				# Cambiar barra por guion para tallas infantiles (Shopify style)
				s = s.replace('/', '-')
				s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('ascii')
				# Permitir letras, números y el guion que acabamos de poner
				s = re.sub(r'[^A-Z0-9-]', '', s)
				return s

			# 1. Prefijo de tipo (Especial para Camiseta: CAM)
			tipo_nom = tipo.nombre.upper()
			t = "CAM" if "CAMISETA" in tipo_nom else clean(tipo.nombre)[:4]
			
			# 2. Color (Nombre completo)
			c = ""
			if color_id:
				color = svc_colores.obtener_por_id(color_id)
				if color:
					c = clean(color.nombre)
			
			# 3. Variante/Público (Nombre completo: HOMBRE, MUJER, INFANTIL)
			v = ""
			if variante_id:
				variante = svc_variantes.obtener_por_id(variante_id)
				if variante:
					v = clean(variante.nombre)
			
			# 4. Talla
			s = clean(talla)
			
			# Construir partes siguiendo el orden de Shopify: TIPO-COLOR-VAR-TALLA
			parts = [t]
			if c: parts.append(c)
			if v: parts.append(v)
			if s: parts.append(s)
			
			sku_base = "-".join(parts)
			return sku_base

		except Exception:
			logger.exception("Error generando SKU")
			return ""

	def guardar_variante(self, tipo_id: int,
	                     color_id: Optional[int], talla: str, sku: str, cantidad: int,
	                     variante_id: Optional[int] = None, coste_medio: int = 0,
	                     talla_id: Optional[int] = None) -> bool:
		"""Guardar o actualizar una variante de stock.
		
		Valida que los datos mínimos estén presentes.
		"""
		if not tipo_id:
			logger.error("Falta dato obligatorio (tipo) para guardar stock base")
			return False
		
		# Limpiar strings
		talla = (talla or "").strip().upper()
		# Unificar ausencia de talla a None: el repo trata NULL y '' como equivalentes,
		# pero almacena None para mantener consistencia con el script de importación.
		if not talla or talla == "-":
			talla = None
		sku = (sku or "").strip().upper()
		
		return self.repo.crear_o_actualizar(tipo_id, color_id, talla, sku, cantidad, coste_medio, variante_id, talla_id)

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
	                  variante_id: Optional[int] = None, cur=None) -> bool:
		"""Descontar stock del almacén de bases."""
		if cantidad <= 0:
			return True
		return self.actualizar_cantidad(tipo_id, color_id, (talla or "").strip().upper(), -cantidad, variante_id, cur=cur)

	def reponer_stock(self, tipo_id: int,
	                 color_id: int, talla: str, cantidad: int,
	                 variante_id: Optional[int] = None, cur=None) -> bool:
		"""Añadir stock al almacén de bases."""
		if cantidad <= 0:
			return True
		return self.actualizar_cantidad(tipo_id, color_id, (talla or "").strip().upper(), cantidad, variante_id, cur=cur)

	def actualizar_cantidad(self, tipo_id: int,
	                        color_id: Optional[int], talla: str, delta: int,
	                        variante_id: Optional[int] = None, cur=None, motivo: str = "Actualización manual") -> bool:
		"""Sumar o restar cantidad al stock (ej: -1 al producir)."""
		ok = self.repo.actualizar_cantidad(tipo_id, color_id, (talla or "").strip().upper(), delta, variante_id, cur=cur)
		
		# Hook de Sincronización Automática con Shopify
		if ok and delta != 0:
			# Obtenemos la cantidad actual para enviar el estado real
			cantidad_actual = self.repo.obtener_cantidad(tipo_id, color_id, (talla or "").strip().upper(), variante_id)
			self._trigger_async_sync(tipo_id, color_id, talla, variante_id, cantidad_actual, motivo=motivo)

		return ok

	def obtener_opciones_formulario(self) -> Dict[str, List[Dict[str, Any]]]:
		"""Obtener listas de tipos y colores para los selectores usando servicios."""
		svc_tipos = ProduccionTiposService(self.db)
		svc_colores = ProduccionColoresService(self.db)
		
		return {
			"tipos": svc_tipos.obtener_como_dict(solo_activos=True),
			"colores": svc_colores.obtener_como_dict(solo_activos=True)
		}

	def migrar_skus_a_formato_shopify(self) -> Tuple[int, int]:
		"""MIGRACIÓN TEMPORAL: Actualiza todos los SKUs de camisetas al nuevo formato Pro.
		
		Returns:
			Tuple[int, int]: (actualizados, errores)
		"""
		try:
			# Solo para tipo Camiseta (ID 1)
			tipo_id_camiseta = 1
			
			# 1. Obtener todos los registros de camisetas
			query = "SELECT id, sku, color_id, talla, variante_id FROM produccion_stock_colores_tallas WHERE tipo_id = ?"
			rows = self.db.fetch_all(query, (tipo_id_camiseta,))
			
			if not rows:
				return 0, 0
				
			updated = 0
			errors = 0
			
			with self.db.transaction() as cur:
				for row in rows:
					row_id, old_sku, color_id, talla, variante_id = row
					
					# Generar nuevo SKU con el motor Pro actualizado
					nuevo_sku = self.generar_sku(tipo_id_camiseta, color_id, talla, variante_id)
					
					if nuevo_sku and nuevo_sku != old_sku:
						cur.execute("UPDATE produccion_stock_colores_tallas SET sku = ? WHERE id = ?", (nuevo_sku, row_id))
						updated += 1
					elif not nuevo_sku:
						errors += 1
						
			return updated, errors
		except Exception:
			logger.exception("Error en migración masiva de SKUs")
			return 0, 0
