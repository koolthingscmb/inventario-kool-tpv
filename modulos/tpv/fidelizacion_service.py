from typing import List, Dict, Optional
import logging
from datetime import date

from modulos.configuracion.config_service import ConfigService
from modulos.almacen.producto_service import ProductoService

logger = logging.getLogger(__name__)


class FidelizacionService:
    """Encapsula la lógica de cálculo de puntos por una venta.

    `calcular_puntos(carrito, cliente)` devuelve el número de puntos a otorgar
    para la venta indicada. `cliente` puede ser None o un dict con al menos
    la clave 'id'.
    """

    def __init__(self):
        self.cfg = ConfigService()
        self.prod_svc = ProductoService()

    def calcular_puntos(self, carrito: List[Dict], cliente: Optional[Dict] = None) -> float:
        try:
            fide_activa = self.cfg.get_valor('fide_activa', '1')
            try:
                if int(fide_activa) != 1:
                    return 0.0
            except Exception:
                pass

            try:
                pct_general = float(self.cfg.get_valor('fide_porcentaje_general', '5') or 0)
            except Exception:
                pct_general = 0.0
            try:
                puntos_por_euro = float(self.cfg.get_valor('fide_puntos_valor_euro', '1') or 1)
            except Exception:
                puntos_por_euro = 1.0

            # promociones activas hoy -> obtener multiplicador máximo
            mult = 1.0
            try:
                promos = self.cfg.listar_promociones() or []
                hoy = date.today()
                for p in promos:
                    try:
                        if int(p.get('activa') or 0) != 1:
                            continue
                        fi = p.get('fecha_inicio')
                        ff = p.get('fecha_fin')
                        valid = True
                        if fi:
                            try:
                                if date.fromisoformat(fi) > hoy:
                                    valid = False
                            except Exception:
                                pass
                        if ff:
                            try:
                                if date.fromisoformat(ff) < hoy:
                                    valid = False
                            except Exception:
                                pass
                        if valid:
                            try:
                                m = float(p.get('multiplicador') or 1.0)
                                if m > mult:
                                    mult = m
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                mult = 1.0

            cats = { (c.get('nombre') or ''): (c.get('fide_porcentaje') or None) for c in self.cfg.listar_categorias_fide() }
            tipos = { (t.get('nombre') or ''): (t.get('fide_porcentaje') or None) for t in self.cfg.listar_tipos_fide() }

            total_points = 0.0

            for item in carrito or []:
                try:
                    price = float(item.get('precio') or 0.0)
                except Exception:
                    price = 0.0
                try:
                    qty = float(item.get('cantidad') or 1.0)
                except Exception:
                    qty = 1.0

                prod_categoria = item.get('categoria')
                prod_tipo = item.get('tipo')
                prod_fide_fixed = item.get('fide_puntos_fijos')

                if (prod_categoria is None or prod_tipo is None or prod_fide_fixed is None) and (item.get('id') or item.get('sku')):
                    try:
                        if item.get('id'):
                            p = self.prod_svc.obtener_por_id(item.get('id'))
                        else:
                            p = self.prod_svc.buscar_por_codigo(item.get('sku'))
                        if p:
                            if prod_categoria is None:
                                prod_categoria = p.get('categoria')
                            if prod_tipo is None:
                                prod_tipo = p.get('tipo')
                            if prod_fide_fixed is None:
                                prod_fide_fixed = p.get('fide_puntos_fijos')
                    except Exception:
                        pass

                # compute points for this item
                item_points = 0.0
                # 1) promotion multiplier applies to entire sale later; per-item we compute base
                if prod_fide_fixed is not None and prod_fide_fixed != '':
                    try:
                        item_points = float(prod_fide_fixed) * qty
                    except Exception:
                        item_points = 0.0
                else:
                    # fallback to tipo/categoria/general percentages
                    applied_pct = None
                    try:
                        if prod_tipo and tipos.get(prod_tipo) is not None:
                            applied_pct = float(tipos.get(prod_tipo))
                        elif prod_categoria and cats.get(prod_categoria) is not None:
                            applied_pct = float(cats.get(prod_categoria))
                        else:
                            applied_pct = float(pct_general)
                    except Exception:
                        applied_pct = float(pct_general)
                    try:
                        item_points = (price * qty) * (applied_pct / 100.0) * puntos_por_euro
                    except Exception:
                        item_points = 0.0

                total_points += item_points

            # apply promotion multiplier
            total_points = total_points * mult

            try:
                return float(total_points)
            except Exception:
                return 0.0
        except Exception:
            logger.exception('Error calculando puntos de fidelización')
            return 0.0

    def desglose_puntos_periodo(self, fecha_desde: str, fecha_hasta: str) -> dict:
        """Devuelve un desglose de puntos en el periodo [fecha_desde, fecha_hasta].

        Fecha esperada en ISO: 'YYYY-MM-DD' o ISO datetime. Devuelve dict con claves:
        - puntos_otorgados, puntos_gastados, clientes_otorgados, clientes_gastados
        Clientes se intentan mapear contra la tabla `clientes` por nombre exacto.
        """
        try:
            import sqlite3
            from database import connect

            conn = connect()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Normalize inputs to full timestamps for inclusive range
            def _norm(dt_str):
                if 'T' in dt_str:
                    return dt_str
                return dt_str + 'T00:00:00'

            desde = _norm(fecha_desde)
            hasta = fecha_hasta
            if 'T' not in hasta:
                hasta = fecha_hasta + 'T23:59:59'

            # Totales
            cur.execute('SELECT COALESCE(SUM(puntos_ganados),0) AS otorgados, COALESCE(SUM(puntos_canjeados),0) AS gastados FROM tickets WHERE created_at BETWEEN ? AND ?', (desde, hasta))
            row = cur.fetchone()
            puntos_otorgados = float(row['otorgados'] or 0.0)
            puntos_gastados = float(row['gastados'] or 0.0)

            # Por cliente (por nombre guardado en tickets.cliente)
            cur.execute('SELECT cliente, COALESCE(SUM(puntos_ganados),0) AS pts FROM tickets WHERE created_at BETWEEN ? AND ? AND cliente IS NOT NULL GROUP BY cliente', (desde, hasta))
            otorgados_rows = [dict(r) for r in cur.fetchall()]

            cur.execute('SELECT cliente, COALESCE(SUM(puntos_canjeados),0) AS pts FROM tickets WHERE created_at BETWEEN ? AND ? AND cliente IS NOT NULL GROUP BY cliente', (desde, hasta))
            gastados_rows = [dict(r) for r in cur.fetchall()]

            # Map ticket cliente (string) to clientes.id when possible
            clientes_map = {}
            try:
                cur.execute('SELECT id, nombre FROM clientes')
                for r in cur.fetchall():
                    nombre = r['nombre'] if 'nombre' in r.keys() else r[1]
                    clientes_map[nombre] = int(r['id'] if 'id' in r.keys() else r[0])
            except Exception:
                clientes_map = {}

            clientes_otorgados = []
            for r in otorgados_rows:
                nombre = r.get('cliente')
                pts = float(r.get('pts') or 0.0)
                cid = clientes_map.get(nombre)
                clientes_otorgados.append({'cliente_id': cid, 'nombre': nombre, 'puntos': pts})

            clientes_gastados = []
            for r in gastados_rows:
                nombre = r.get('cliente')
                pts = float(r.get('pts') or 0.0)
                cid = clientes_map.get(nombre)
                clientes_gastados.append({'cliente_id': cid, 'nombre': nombre, 'puntos': pts})

            try:
                conn.close()
            except Exception:
                pass

            return {
                'puntos_otorgados': puntos_otorgados,
                'puntos_gastados': puntos_gastados,
                'clientes_otorgados': clientes_otorgados,
                'clientes_gastados': clientes_gastados,
            }
        except Exception:
            logger.exception('Error obteniendo desglose puntos periodo')
            return {
                'puntos_otorgados': 0,
                'puntos_gastados': 0,
                'clientes_otorgados': [],
                'clientes_gastados': [],
            }
