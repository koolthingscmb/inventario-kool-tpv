from decimal import Decimal, ROUND_DOWN
import logging
from typing import List, Dict

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.configuracion_service import ConfiguracionService


class FidelizacionService:
    """Servicio para calcular puntos de fidelización.

    Estrategia de búsqueda de porcentaje (jerarquía): tipo -> categoría -> global (config).
    """

    def __init__(self, db: Database):
        self.db = db
        self.config_service = ConfiguracionService(db)

    def obtener_porcentaje_producto(self, producto_id: int) -> Decimal:
        """Obtiene el porcentaje de fidelización aplicable a `producto_id`.

        Intenta en el siguiente orden: `tipos.fide_porcentaje`, `categorias.fide_porcentaje`,
        y finalmente el valor global en `configuracion` (`fide_porcentaje_general`).
        Devuelve Decimal('0') si no hay nada definido o en caso de error.
        """
        # Legacy compatibility wrapper: delegate to new obtener_fidelizacion_producto
        try:
            config = self.obtener_fidelizacion_producto(producto_id)
            if not config:
                return Decimal('0')
            if config.get('tipo') == 'fijo':
                return Decimal('0')
            return config.get('valor', Decimal('0'))
        except Exception:
            logging.exception('Error obteniendo porcentaje de producto %s', producto_id)
            try:
                return Decimal(str(self.config_service.get_fide_porcentaje_global()))
            except Exception:
                return Decimal('0')

    def obtener_fidelizacion_producto(self, producto_id: int) -> dict:
        """Obtiene configuración de fidelización para un producto.

        Jerarquía: producto → tipo → categoría → global

        Returns:
            dict: {
                'tipo': 'fijo' | 'porcentaje',
                'valor': Decimal
            }
        """
        try:
            query = """
            SELECT 
                p.fidelizacion_tipo,
                p.fidelizacion_valor,
                t.fide_porcentaje as tipo_pct,
                c.fide_porcentaje as cat_pct
            FROM productos p
            LEFT JOIN tipos t ON t.id = p.tipo
            LEFT JOIN categorias c ON c.id = p.categoria
            WHERE p.id = ?
            LIMIT 1
            """
            row = self.db.fetch_one(query, (producto_id,))

            if not row:
                global_pct = self.config_service.get_fide_porcentaje_global()
                return {'tipo': 'porcentaje', 'valor': Decimal(str(global_pct))}

            prod_tipo = row[0]
            prod_valor = row[1]

            # Producto específico configurado y valor > 0
            try:
                if prod_valor is not None and Decimal(str(prod_valor)) > 0:
                    return {'tipo': (prod_tipo or 'porcentaje'), 'valor': Decimal(str(prod_valor))}
            except Exception:
                pass

            # Tipo tiene porcentaje?
            tipo_pct = row[2]
            try:
                if tipo_pct is not None and Decimal(str(tipo_pct)) > 0:
                    return {'tipo': 'porcentaje', 'valor': Decimal(str(tipo_pct))}
            except Exception:
                pass

            # Categoría tiene porcentaje?
            cat_pct = row[3]
            try:
                if cat_pct is not None and Decimal(str(cat_pct)) > 0:
                    return {'tipo': 'porcentaje', 'valor': Decimal(str(cat_pct))}
            except Exception:
                pass

            # Fallback a global
            global_pct = self.config_service.get_fide_porcentaje_global()
            return {'tipo': 'porcentaje', 'valor': Decimal(str(global_pct))}

        except Exception:
            logging.exception('Error obteniendo fidelización de producto %s', producto_id)
            return {'tipo': 'porcentaje', 'valor': Decimal('0')}

    def calcular_puntos_ganados(self, items: List[Dict], puntos_canjeados: Decimal = Decimal('0')) -> Decimal:
        """Calcula el total de puntos ganados por una lista de items del carrito.

        Cada item debe contener al menos: 'id', 'pvp' y 'cantidad'.
        Se utiliza Decimal para todos los cálculos y se redondea a 2 decimales.
        """
        total = Decimal('0')
        if not items:
            return total

        # Cache para evitar múltiples consultas al mismo producto
        pct_cache = {}

        # Calcular total bruto para aplicar factor de pago (después de canjes)
        try:
            total_bruto = sum(
                (Decimal(str(it.get('pvp', 0))) * Decimal(str(it.get('cantidad', 1)))) for it in items
            )
        except Exception:
            total_bruto = Decimal('0')

        if total_bruto > 0:
            try:
                factor_pago = (total_bruto - (puntos_canjeados or Decimal('0'))) / total_bruto
            except Exception:
                factor_pago = Decimal('0')
        else:
            factor_pago = Decimal('0')

        for it in items:
            try:
                pid = it.get('id')
                if pid is None:
                    continue
                cantidad = Decimal(str(it.get('cantidad', 1)))
                pvp = Decimal(str(it.get('pvp', '0')))

                if pid in pct_cache:
                    config = pct_cache[pid]
                else:
                    config = self.obtener_fidelizacion_producto(pid)
                    pct_cache[pid] = config

                tipo = config.get('tipo', 'porcentaje')
                valor = config.get('valor', Decimal('0'))

                if tipo == 'fijo':
                    # Puntos fijos por unidad (afectados por factor_pago)
                    puntos_item = (valor * cantidad * factor_pago).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                else:
                    # Porcentaje del precio
                    puntos_item = (pvp * cantidad * (valor / Decimal('100')) * factor_pago).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                total += puntos_item
            except Exception:
                logging.exception('Error calculando puntos para item: %s', it)
                continue

        return total
