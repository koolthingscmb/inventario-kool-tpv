"""Servicio para gestionar las órdenes de producción.

Contiene la lógica para guardar las órdenes y actualizar el stock de diseños.
"""
import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.money_adapter import prepare_for_db
from kool_tpv.modulos.produccion.models.produccion_orden_model import ProduccionOrden
from kool_tpv.modulos.produccion.models.produccion_linea_model import ProduccionLinea
from kool_tpv.modulos.produccion.repositories.produccion_ordenes_repository import ProduccionOrdenesRepository
from kool_tpv.modulos.produccion.repositories.produccion_stock_base_repository import ProduccionStockBaseRepository
from kool_tpv.modulos.produccion.services.variante_producto_service import VarianteProductoService

@dataclass
class ItemProduccion:
    tipo_nombre: str
    tipo_id: int
    talla: Optional[str]
    color_nombre: Optional[str]
    color_id: Optional[int]
    diseno_codigo: str
    diseno_nombre: str
    cantidad: int
    produccion_mixta: bool
    coste_unitario: float
    coste_total: float
    extra_id: Optional[int] = None
    extra_coste: float = 0.0
    extra_nombre: Optional[str] = None
    variante_nombre: Optional[str] = None
    variante_id: Optional[int] = None
    diseno_coleccion: Optional[str] = None
    diseno_sufijo: Optional[str] = None
    metodo_id: Optional[int] = None
    metodo_nombre: Optional[str] = None
    origen: str = "KOOL"
    usuario_nombre: Optional[str] = None

class ProduccionOrdenesService:
    def __init__(self, db: Database):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.repo_ordenes = ProduccionOrdenesRepository(db)
        self.repo_stock_base = ProduccionStockBaseRepository(db)
        self.link_service = VarianteProductoService(db)

    def guardar_orden(self, items: List[ItemProduccion], usuario_id: Optional[int] = None) -> bool:
        """Guardar una orden de producción completa y actualizar el stock."""
        if not items:
            return False

        try:
            # Determinamos el origen de la orden (del primer ítem o KOOL por defecto)
            origen_orden = items[0].origen if items else 'KOOL'

            # Usamos el manager de transacciones de db_wrapper
            with self.db.transaction() as cur:
                # 1. Crear la cabecera de la orden
                orden = ProduccionOrden(
                    usuario_id=usuario_id,
                    estado='COMPLETADA',
                    origen=origen_orden,
                    fecha_hora=datetime.now()
                )
                orden_id = self.repo_ordenes.crear(orden)
                
                if not orden_id:
                    raise Exception("No se pudo crear la cabecera de la orden")

                # 2. Guardar cada línea y actualizar stock
                for item in items:
                    # Guardar línea usando el repo profesionalmente
                    linea = ProduccionLinea(
                        orden_id=orden_id,
                        diseno_codigo=item.diseno_codigo,
                        tipo_id=item.tipo_id,
                        talla=item.talla,
                        color_id=item.color_id,
                        cantidad=item.cantidad,
                        produccion_mixta=1 if item.produccion_mixta else 0,
                        extra_id=item.extra_id,
                        extra_coste=int(prepare_for_db(item.extra_coste)),
                        usuario_produccion_id=usuario_id,
                        coste_unitario=int(prepare_for_db(item.coste_unitario)),
                        coste_total=int(prepare_for_db(item.coste_total)),
                        variante_id=item.variante_id,
                        metodo_id=item.metodo_id,
                        origen=item.origen or 'KOOL'
                    )
                    
                    linea_id = self.repo_ordenes.crear_linea(linea)
                    if not linea_id:
                        raise Exception(f"No se pudo crear la línea para el diseño {item.diseno_codigo}")

                    # 3. Actualizar stock de bases (descontar el material en blanco)
                    # Usamos el repo de stock base que ya soporta variantes
                    ok_stock_base = self.repo_stock_base.actualizar_cantidad(
                        tipo_id=item.tipo_id,
                        color_id=item.color_id,
                        talla=item.talla,
                        delta=-item.cantidad,
                        variante_id=item.variante_id
                    )
                    if not ok_stock_base:
                        self.logger.warning(f"No se pudo descontar stock de base para tipo {item.tipo_id}, variante {item.variante_id}")

                    # 4. Actualizar stock acumulado de diseños (incluyendo variante)
                    self._actualizar_stock_diseno(item)

                    # 5. INTEGRACIÓN TPV: Sumar stock al producto TPV vinculado
                    if item.variante_id:
                        self._actualizar_stock_tpv_vinculado(item)

            return True

        except Exception:
            self.logger.exception("Error al guardar la orden de producción")
            return False

    def _actualizar_stock_diseno(self, item: ItemProduccion):
        """Actualizar la tabla produccion_disenos_stock incluyendo variante_id."""
        try:
            # Intentar insertar o actualizar incluyendo variante_id para no mezclar stocks
            query = """
                INSERT INTO produccion_disenos_stock 
                (diseno_codigo, tipo_id, color_id, talla, cantidad, variante_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(diseno_codigo, tipo_id, color_id, talla, variante_id) 
                DO UPDATE SET cantidad = cantidad + excluded.cantidad
            """
            self.db.execute_query(query, (
                item.diseno_codigo, item.tipo_id, item.color_id, 
                item.talla, item.cantidad, item.variante_id
            ))
        except Exception:
            self.logger.exception(f"Error actualizando stock para diseño {item.diseno_codigo}")

    def _actualizar_stock_tpv_vinculado(self, item: ItemProduccion):
        """Si la variante está vinculada a un producto TPV, sumar el stock correspondiente."""
        try:
            link = self.link_service.get_por_variante(item.variante_id)
            if link and link.producto_id:
                # Calcular cantidad a sumar según el ratio (por defecto 1)
                ratio = link.ratio if link.ratio and link.ratio > 0 else 1
                cantidad_tpv = item.cantidad * ratio
                
                # Ejecutar el update directamente en la base de datos
                # Esto se ejecuta dentro de la misma transacción que el resto de la orden
                query = "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?"
                self.db.execute_query(query, (cantidad_tpv, link.producto_id))
                
                self.logger.info(f"VINCULACIÓN TPV: Sumado +{cantidad_tpv} uds al producto ID {link.producto_id} (Variante {item.variante_id})")
        except Exception:
            self.logger.exception(f"Error al actualizar stock TPV vinculado para variante {item.variante_id}")
