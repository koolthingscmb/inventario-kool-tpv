# -*- coding: utf-8 -*-
"""
fidelizacion_service.py
─────────────────────
Servicio dedicado únicamente al **cálculo** de los puntos (tesoro) de fidelización.
No realiza operaciones de escritura en la base de datos; esa responsabilidad
pasará a un futuro `loyalty_repository` (o `loyalty_service`).

Mantener este archivo separado permite:
* Testear la lógica de puntos de forma aislada.
* Evitar que la capa de cálculo se mezcle con la capa de persistencia.
* Facilitar la futura migración a `loyalty_service.py`.

Autor: [Egon]
"""

import logging
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.base_datos.configuracion_service import ConfiguracionService
from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)

class FidelizacionService:
    """
    Cálculo de puntos de fidelización.

    - La jerarquía de porcentaje es:
        1️⃣ Tipo del producto (`tipos.fide_porcentaje`)
        2️⃣ Categoría del producto (`categorias.fide_porcentaje`)
        3️⃣ Valor global (`configuracion.fide_porcentaje_general`)

    - El método `calcular_puntos_ganados` devuelve la suma total de puntos
      (en **euros**, usando `Decimal`) que corresponde a una lista de ítems.
    """

    def __init__(self, db: Database):
        self.db = db
        self.config_service = ConfiguracionService(db)

    # --------------------------------------------------------------------- #
    # 1️⃣ Porcentaje aplicable a un producto (tipo → categoría → global)
    # --------------------------------------------------------------------- #
    def obtener_porcentaje_producto(self, producto_id: int) -> Decimal:
        """
        Devuelve el porcentaje (Decimal) que se aplicará al producto indicado.
        Si no se encuentra ningún valor, devuelve Decimal('0').
        """
        try:
            cfg = self.obtener_fidelizacion_producto(producto_id)
            if not cfg:
                return Decimal('0')
            # Tipo "fijo" significa que no hay porcentaje
            if cfg.get('tipo') == 'fijo':
                return Decimal('0')
            return cfg.get('valor', Decimal('0'))
        except Exception:
            logger.exception('Error obteniendo porcentaje del producto %s', producto_id)
            # Fallback al valor global configurado
            try:
                return Decimal(str(self.config_service.get_fide_porcentaje_global()))
            except Exception:
                return Decimal('0')

    # --------------------------------------------------------------------- #
    # 2️⃣ Configuración completa de fidelización de un producto
    # --------------------------------------------------------------------- #
    def obtener_fidelizacion_producto(self, producto_id: int) -> dict:
        """
        Retorna un diccionario con:
            {
                'tipo': 'fijo' | 'porcentaje',
                'valor': Decimal
            }
        La resolución sigue la jerarquía: producto → tipo → categoría → global.
        """
        try:
            query = """
                SELECT
                    p.fidelizacion_tipo,
                    p.fidelizacion_valor,
                    t.fide_porcentaje AS tipo_pct,
                    c.fide_porcentaje AS cat_pct
                FROM productos p
                LEFT JOIN tipos t ON t.id = p.tipo
                LEFT JOIN categorias c ON c.id = p.categoria
                WHERE p.id = ?
                LIMIT 1
            """
            row = self.db.fetch_one(query, (producto_id,))
            if not row:
                # No existe el producto → usar el valor global
                global_pct = self.config_service.get_fide_porcentaje_global()
                return {'tipo': 'porcentaje', 'valor': Decimal(str(global_pct))}

            prod_tipo, prod_valor, tipo_pct, cat_pct = row

            # 1️⃣ Valor específico del producto
            if prod_valor is not None and Decimal(str(prod_valor)) > 0:
                return {
                    'tipo': prod_tipo or 'porcentaje',
                    'valor': Decimal(str(prod_valor))
                }

            # 2️⃣ Porcentaje del tipo
            if tipo_pct is not None and Decimal(str(tipo_pct)) > 0:
                return {'tipo': 'porcentaje', 'valor': Decimal(str(tipo_pct))}

            # 3️⃣ Porcentaje de la categoría
            if cat_pct is not None and Decimal(str(cat_pct)) > 0:
                return {'tipo': 'porcentaje', 'valor': Decimal(str(cat_pct))}

            # 4️⃣ Global
            global_pct = self.config_service.get_fide_porcentaje_global()
            return {'tipo': 'porcentaje', 'valor': Decimal(str(global_pct))}

        except Exception:
            logger.exception('Error obteniendo configuración de fidelización para producto %s', producto_id)
            return {'tipo': 'porcentaje', 'valor': Decimal('0')}

    # --------------------------------------------------------------------- #
    # 3️⃣ Cálculo de puntos ganados (ventas y devoluciones)
    # --------------------------------------------------------------------- #
    def calcular_puntos_ganados(
        self,
        items: List[Dict],
        puntos_canjeados: Decimal = Decimal('0')
    ) -> int:
        """
        Calcula los puntos totales obtenidos por una lista de ítems.

        Parámetros
        ----------
        items : list[dict]
            Cada ítem debe contener al menos: 'id', 'pvp' (precio), 'cantidad'.
        puntos_canjeados : Decimal, opcional
            Puntos previamente canjeados en la misma operación.
            Se resta proporcionalmente del total de la venta.

        Retorna
        -------
        Decimal
            Total de puntos (en euros) redondeado a 2 decimales
            (usar `ROUND_DOWN` para ser coherente con la lógica original).
        """
        total = Decimal('0')
        if not items:
            return total

        # Cache para evitar consultas repetidas al DB
        pct_cache: dict[int, dict] = {}

        # Precio bruto total (sin aplicar canje) – sirve para el factor de pago
        try:
            total_bruto = sum(
                Decimal(str(it.get('pvp', 0))) *
                Decimal(str(it.get('cantidad', 1)))
                for it in items
            )
        except Exception:
            total_bruto = Decimal('0')

        # Factor de pago = (bruto - puntos canjeados) / bruto
        factor_pago = Decimal('0')
        if total_bruto > 0:
            try:
                factor_pago = (total_bruto - (puntos_canjeados or Decimal('0'))) / total_bruto
            except Exception:
                factor_pago = Decimal('0')

        for it in items:
            try:
                pid = it.get('id')
                if pid is None:
                    continue

                cantidad = Decimal(str(it.get('cantidad', 1)))
                pvp = Decimal(str(it.get('pvp', '0')))

                # Obtener (o reutilizar) la configuración de fidelización del producto
                if pid in pct_cache:
                    cfg = pct_cache[pid]
                else:
                    cfg = self.obtener_fidelizacion_producto(pid)
                    pct_cache[pid] = cfg

                tipo = cfg.get('tipo', 'porcentaje')
                valor = cfg.get('valor', Decimal('0'))

                # Si el ítem es una devolución, no aplicamos el factor de pago
                item_line_type = it.get('line_tipo')
                item_factor = factor_pago
                if isinstance(item_line_type, str) and item_line_type.lower() == 'devolucion':
                    item_factor = Decimal('1')

                if tipo == 'fijo':
                    # Puntos fijos por unidad (aplicamos el factor correspondiente)
                    puntos_item = (valor * cantidad * item_factor).quantize(
                        Decimal('0.01'), rounding=ROUND_DOWN
                    )
                else:
                    # Porcentaje del precio
                    puntos_item = (
                        pvp *
                        cantidad *
                        (valor / Decimal('100')) *
                        item_factor
                    ).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

                total += puntos_item
            except Exception:
                logger.exception('Error calculando puntos para ítem: %s', it)
                continue

        return int(prepare_for_db(total))