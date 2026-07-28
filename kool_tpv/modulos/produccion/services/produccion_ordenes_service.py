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
from kool_tpv.modulos.produccion.repositories.produccion_metodos_repository import ProduccionMetodosRepository
from kool_tpv.modulos.produccion.repositories.produccion_extras_repository import ProduccionExtrasRepository
from kool_tpv.modulos.produccion.services.variante_producto_service import VarianteProductoService
from kool_tpv.modulos.produccion.services.produccion_tallas_service import ProduccionTallasService
from kool_tpv.modulos.tpv.services.reposicion_store import ReposicionStore

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
    coleccion_id: Optional[int] = None
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
        self.repo_metodos = ProduccionMetodosRepository(db)
        self.repo_extras = ProduccionExtrasRepository(db)
        self.link_service = VarianteProductoService(db)
        self.tallas_service = ProduccionTallasService(db)
        self.reposicion_store = ReposicionStore()

    def guardar_orden(self, items: List[ItemProduccion], usuario_id: Optional[int] = None) -> int:
        """Guardar una orden de producción completa y actualizar el stock.

        Returns:
            Número de líneas de reposición borradas, o -1 si hubo error.
        """
        if not items:
            return -1

        try:
            lineas_borradas = 0
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

                    # 6. REPOSICIÓN: Borrar línea coincidente del JSON
                    borrado = self._borrar_reposicion_coincidente(item)
                    if borrado:
                        lineas_borradas += 1

            return lineas_borradas

        except Exception:
            self.logger.exception("Error al guardar la orden de producción")
            return -1

    def _actualizar_stock_diseno(self, item: ItemProduccion):
        """Actualizar la tabla produccion_disenos_stock manejando correctamente los NULLs."""
        try:
            # SQLite no considera NULL = NULL en ON CONFLICT, así que usamos un Upsert manual robusto
            check_query = """
                SELECT id FROM produccion_disenos_stock 
                WHERE diseno_codigo = ? AND tipo_id = ? AND color_id IS ? AND talla IS ? AND variante_id IS ?
            """
            row = self.db.fetch_one(check_query, (
                item.diseno_codigo, item.tipo_id, item.color_id, 
                item.talla, item.variante_id
            ))

            if row:
                update_query = "UPDATE produccion_disenos_stock SET cantidad = cantidad + ? WHERE id = ?"
                self.db.execute_query(update_query, (item.cantidad, row[0]))
            else:
                insert_query = """
                    INSERT INTO produccion_disenos_stock 
                    (diseno_codigo, tipo_id, color_id, talla, cantidad, variante_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                self.db.execute_query(insert_query, (
                    item.diseno_codigo, item.tipo_id, item.color_id, 
                    item.talla, item.cantidad, item.variante_id
                ))
        except Exception:
            self.logger.exception(f"Error actualizando stock para diseño {item.diseno_codigo}")

    def _actualizar_stock_tpv_vinculado(self, item: ItemProduccion):
        """Si la variante está vinculada a un producto TPV, sumar el stock correspondiente."""
        try:
            link = self.link_service.get_por_combinacion(item.variante_id, extra_id=item.extra_id, coleccion_id=item.coleccion_id)
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

    def _borrar_reposicion_coincidente(self, item: ItemProduccion) -> bool:
        """Borrar coincidencia del JSON de reposición por tipo, variante y diseño."""
        try:
            return self.reposicion_store.eliminar_coincidencia(
                tipo_id=item.tipo_id,
                variante_id=item.variante_id,
                diseno_codigo=item.diseno_codigo
            )
        except Exception:
            self.logger.exception(f"Error borrando reposición coincidente para diseño {item.diseno_codigo}")
            return False

    def get_linea_por_id(self, linea_id: int) -> Optional[ProduccionLinea]:
        """Obtener una línea específica por su ID."""
        return self.repo_ordenes.get_linea_por_id(linea_id)

    def actualizar_linea(self, linea_id: int, nuevos_datos: dict) -> bool:
        """Actualizar una línea de producción y ajustar stocks."""
        try:
            linea_original = self.repo_ordenes.get_linea_por_id(linea_id)
            if not linea_original:
                return False

            with self.db.transaction():
                # Guardar valores originales para el ajuste de stock
                cant_orig = linea_original.cantidad
                tipo_orig = linea_original.tipo_id
                col_orig = linea_original.color_id
                talla_orig = linea_original.talla
                var_orig = linea_original.variante_id
                dis_orig = linea_original.diseno_codigo

                # 1. Actualizar objeto linea con nuevos datos
                linea_original.diseno_codigo = nuevos_datos.get('diseno_codigo', linea_original.diseno_codigo)
                linea_original.cantidad = nuevos_datos.get('cantidad', linea_original.cantidad)
                linea_original.tipo_id = nuevos_datos.get('tipo_id', linea_original.tipo_id)
                linea_original.talla = nuevos_datos.get('talla', linea_original.talla)
                linea_original.color_id = nuevos_datos.get('color_id', linea_original.color_id)
                linea_original.variante_id = nuevos_datos.get('variante_id', linea_original.variante_id)
                linea_original.metodo_id = nuevos_datos.get('metodo_id', linea_original.metodo_id)
                linea_original.extra_id = nuevos_datos.get('extra_id', linea_original.extra_id)
                linea_original.produccion_mixta = nuevos_datos.get('produccion_mixta', linea_original.produccion_mixta)

                # 2. Recalcular costes si cambiaron campos relevantes
                # a) Coste Base (Prenda) desde stock
                stock_base = self.repo_stock_base.get_by_params(
                    linea_original.tipo_id, linea_original.color_id, 
                    linea_original.talla, linea_original.variante_id
                )
                coste_base = stock_base['coste_medio'] if stock_base else 0

                # b) Coste del método para el diseño
                costes_metodos = self.repo_metodos.get_costes_por_diseno(linea_original.diseno_codigo)
                coste_metodo = costes_metodos.get(linea_original.metodo_id, 0)
                
                # c) Coste del extra
                coste_extra = 0
                if linea_original.extra_id:
                    extra = self.repo_extras.get_por_id(linea_original.extra_id)
                    coste_extra = extra.coste if extra else 0
                
                # Snapshot de costes
                linea_original.extra_coste = coste_extra
                linea_original.coste_unitario = coste_base + coste_metodo # El coste unitario es prenda + impresión
                linea_original.coste_total = int((linea_original.coste_unitario + coste_extra) * linea_original.cantidad)

                # 3. Guardar en DB
                if not self.repo_ordenes.actualizar_linea(linea_original):
                    raise Exception("Error en repo_ordenes.actualizar_linea")

                # 4. AJUSTE DE STOCKS (Transaccional)
                # Revertir stock antiguo (sumar lo que se restó al producir)
                self.repo_stock_base.actualizar_cantidad(
                    tipo_id=tipo_orig, color_id=col_orig, talla=talla_orig,
                    delta=cant_orig, variante_id=var_orig
                )
                self._actualizar_stock_diseno_directo(dis_orig, tipo_orig, col_orig, talla_orig, var_orig, -cant_orig)
                if var_orig:
                    self._ajustar_stock_tpv_vinculado_por_datos(dis_orig, var_orig, -cant_orig)

                # Aplicar stock nuevo (restar la nueva producción)
                self.repo_stock_base.actualizar_cantidad(
                    tipo_id=linea_original.tipo_id, color_id=linea_original.color_id, 
                    talla=linea_original.talla, delta=-linea_original.cantidad, 
                    variante_id=linea_original.variante_id
                )
                self._actualizar_stock_diseno_directo(
                    linea_original.diseno_codigo, linea_original.tipo_id, 
                    linea_original.color_id, linea_original.talla, 
                    linea_original.variante_id, linea_original.cantidad
                )
                if linea_original.variante_id:
                    self._ajustar_stock_tpv_vinculado(linea_original, linea_original.cantidad)

            return True
        except Exception:
            self.logger.exception(f"Error actualizando línea {linea_id}")
            return False

    def _ajustar_stock_tpv_vinculado_por_datos(self, diseno_codigo, variante_id, delta):
        """Ajustar stock TPV por datos directos (para reversiones)."""
        try:
            from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
            repo_dis = ProduccionDisenosRepository(self.db)
            dis = repo_dis.get_por_codigo(diseno_codigo)
            col_id = dis.coleccion_id if dis else None
            link = self.link_service.get_por_combinacion(variante_id, coleccion_id=col_id)
            if link and link.producto_id:
                ratio = link.ratio if link.ratio and link.ratio > 0 else 1
                cantidad_tpv = delta * ratio
                query = "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?"
                self.db.execute_query(query, (cantidad_tpv, link.producto_id))
        except Exception:
            self.logger.exception(f"Error ajustando stock TPV directo para {diseno_codigo}")

    def _actualizar_stock_diseno_directo(self, codigo, tipo_id, color_id, talla, variante_id, delta):
        """Versión directa de _actualizar_stock_diseno para ajustes."""
        try:
            check_query = """
                SELECT id FROM produccion_disenos_stock 
                WHERE diseno_codigo = ? AND tipo_id = ? AND color_id IS ? AND talla IS ? AND variante_id IS ?
            """
            row = self.db.fetch_one(check_query, (codigo, tipo_id, color_id, talla, variante_id))
            if row:
                update_query = "UPDATE produccion_disenos_stock SET cantidad = cantidad + ? WHERE id = ?"
                self.db.execute_query(update_query, (delta, row[0]))
        except Exception:
            self.logger.exception(f"Error ajustando stock directo para diseño {codigo}")

    def _ajustar_stock_tpv_vinculado(self, linea: ProduccionLinea, delta: int):
        """Ajustar el stock TPV vinculado basándose en un delta."""
        try:
            # Obtener coleccion_id del diseño para el link_service
            from kool_tpv.modulos.produccion.repositories.produccion_disenos_repository import ProduccionDisenosRepository
            repo_dis = ProduccionDisenosRepository(self.db)
            dis = repo_dis.get_por_codigo(linea.diseno_codigo)
            col_id = dis.coleccion_id if dis else None

            link = self.link_service.get_por_combinacion(linea.variante_id, extra_id=linea.extra_id, coleccion_id=col_id)
            if link and link.producto_id:
                ratio = link.ratio if link.ratio and link.ratio > 0 else 1
                cantidad_tpv = delta * ratio
                query = "UPDATE productos SET stock_actual = stock_actual + ? WHERE id = ?"
                self.db.execute_query(query, (cantidad_tpv, link.producto_id))
        except Exception:
            self.logger.exception(f"Error ajustando stock TPV vinculado para linea {linea.id}")

    def obtener_lineas_historial(self, filtro: Optional[str] = None) -> List[dict]:
        """Obtener todas las líneas de producción con datos enriquecidos.

        Args:
            filtro: Término de búsqueda opcional (busca en nombre de diseño).

        Returns:
            Lista de diccionarios con fecha, usuario, tipo, variante, color, talla,
            colección, sufijo, diseño y coste.
        """
        return self.repo_ordenes.get_todas_lineas_con_datos(filtro)
