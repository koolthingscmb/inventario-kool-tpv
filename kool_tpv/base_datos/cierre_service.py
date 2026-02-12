"""Servicio de acceso a datos para la tabla `cierres_caja`.

Provee métodos básicos para insertar, listar y obtener cierres.
"""
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal


class CierreService:
    def __init__(self, db):
        """Crear servicio usando el wrapper `Database` del proyecto.

        Args:
            db: instancia de `kool_tpv.base_datos.db_wrapper.Database`
        """
        self.db = db

    def ensure_table(self):
        sql = '''CREATE TABLE IF NOT EXISTS "cierres_caja" (
    "id"    INTEGER,
    "cierre_num"    INTEGER,
    "fecha_hora"    TIMESTAMP,
    "cajero"    TEXT,
    "total_ingresos"    REAL,
    "num_ventas"    INTEGER,
    "rango_inicio_ticket"    INTEGER,
    "rango_fin_ticket"    INTEGER,
    "total_efectivo"    REAL DEFAULT 0.0,
    "total_tarjeta"    REAL DEFAULT 0.0,
    "total_web"    REAL DEFAULT 0.0,
    "total_devoluciones"    REAL DEFAULT 0.0,
    "total_descuentos"    REAL DEFAULT 0.0,
    "tesoro_ganado"    REAL DEFAULT 0.0,
    "tesoro_gastado"    REAL DEFAULT 0.0,
    "tesoro_total_ganado"    REAL DEFAULT 0.0,
    "tesoro_total_gastado"    REAL DEFAULT 0.0,
    "cierre_text"    TEXT,
    "usuario_id"    INTEGER,
    PRIMARY KEY("id" AUTOINCREMENT)
)'''
        try:
            self.db.connect()
            self.db.execute_query(sql)
        except Exception:
            logging.exception('Error al asegurar tabla cierres_caja')

    def insert_cierre(self, cierre: Dict[str, Any]) -> Optional[int]:
        """Insertar un cierre y devolver el id insertado.

        Espera un dict con claves compatibles con las columnas de la tabla.
        """
        cols = [
            'cierre_num', 'fecha_hora', 'cajero', 'total_ingresos', 'num_ventas',
            'rango_inicio_ticket', 'rango_fin_ticket', 'total_efectivo', 'total_tarjeta',
            'total_web', 'total_devoluciones', 'total_descuentos', 'tesoro_ganado',
            'tesoro_gastado', 'tesoro_total_ganado', 'tesoro_total_gastado', 'cierre_text', 'usuario_id'
        ]
        values = [cierre.get(c) for c in cols]
        placeholders = ','.join(['?'] * len(cols))
        sql = f'INSERT INTO cierres_caja ({",".join(cols)}) VALUES ({placeholders})'
        try:
            self.db.connect()
            cur = self.db.execute_query(sql, tuple(values))
            try:
                return cur.lastrowid
            except Exception:
                return None
        except Exception:
            logging.exception('Error insertando cierre')
            return None

    def obtener_cierre_por_id(self, cierre_id: int) -> Optional[Dict[str, Any]]:
        sql = 'SELECT * FROM cierres_caja WHERE id = ?'
        try:
            self.db.connect()
            row = self.db.fetch_one(sql, (cierre_id,))
            if not row:
                return None
            return self._row_to_dict(row)
        except Exception:
            logging.exception('Error obteniendo cierre por id')
            return None

    def get_ticket_ids_without_cierre(self, filters: Optional[Dict[str, Any]] = None) -> List[int]:
        """Devolver lista de IDs de tickets con `cierre_id IS NULL`.

        Actualmente `filters` se ignora (se implementará según requisitos).
        """
        try:
            sql = 'SELECT id FROM tickets WHERE cierre_id IS NULL ORDER BY created_at ASC'
            self.db.connect()
            rows = self.db.fetch_all(sql)
            return [r[0] for r in rows or []]
        except Exception:
            logging.exception('Error obteniendo ticket ids sin cierre')
            return []

    def compute_totals_for_ticket_ids(self, ticket_ids: List[int]) -> Dict[str, Any]:
        """Calcular totales y desglose de IVA para una lista de tickets.

        Devuelve un dict con claves: total_ingresos, num_ventas, total_efectivo,
        total_tarjeta, total_web, base_21, iva_21, base_4, iva_4, total_base_imponible, total_iva,
        rango_inicio_ticket, rango_fin_ticket, ticket_ids.
        """
        result = {
            'total_ingresos': Decimal('0'),
            'num_ventas': 0,
            'total_efectivo': Decimal('0'),
            'total_tarjeta': Decimal('0'),
            'total_web': Decimal('0'),
            'base_21': Decimal('0'),
            'iva_21': Decimal('0'),
            'base_4': Decimal('0'),
            'iva_4': Decimal('0'),
            'total_base_imponible': Decimal('0'),
            'total_iva': Decimal('0'),
            'rango_inicio_ticket': None,
            'rango_fin_ticket': None,
            'ticket_ids': list(ticket_ids)
        }

        if not ticket_ids:
            return result

        try:
            # Prepare placeholders
            placeholders = ','.join(['?'] * len(ticket_ids))

            # Obtener datos principales de tickets
            sql_tickets = f"SELECT id, num_ticket, created_at, total, forma_pago, importe_efectivo, importe_tarjeta FROM tickets WHERE id IN ({placeholders})"
            self.db.connect()
            ticket_rows = self.db.fetch_all(sql_tickets, tuple(ticket_ids))

            nums = []
            for tr in ticket_rows or []:
                try:
                    total = Decimal(str(tr[3] or 0))
                    result['total_ingresos'] += total
                except Exception:
                    pass
                try:
                    ef = Decimal(str(tr[5] or 0))
                    result['total_efectivo'] += ef
                except Exception:
                    pass
                try:
                    ta = Decimal(str(tr[6] or 0))
                    result['total_tarjeta'] += ta
                except Exception:
                    pass
                # web/otros no siempre presentes: inferir desde forma_pago
                try:
                    forma = (tr[4] or '').lower() if tr[4] else ''
                    if forma and 'web' in forma:
                        result['total_web'] += Decimal(str(tr[3] or 0))
                except Exception:
                    pass
                nums.append(tr[1])

            result['num_ventas'] = len(ticket_rows or [])
            if nums:
                try:
                    result['rango_inicio_ticket'] = min([n for n in nums if n is not None])
                    result['rango_fin_ticket'] = max([n for n in nums if n is not None])
                except Exception:
                    pass

            # Obtener líneas de todos los tickets para calcular IVA
            sql_lines = f"SELECT ticket_id, cantidad, precio, iva, line_tipo FROM ticket_lines WHERE ticket_id IN ({placeholders})"
            lines = self.db.fetch_all(sql_lines, tuple(ticket_ids))

            base_by_type = {}
            iva_by_type = {}
            for ln in lines or []:
                try:
                    cantidad = Decimal(str(ln[1] or 0))
                    precio = Decimal(str(ln[2] or 0))
                    tipo_iva = int(float(ln[3])) if ln[3] is not None else 21
                    line_tipo = ln[4] if len(ln) > 4 else 'venta'
                    sign = Decimal('-1') if str(line_tipo) == 'devolucion' else Decimal('1')

                    gross = precio * cantidad * sign
                    divisor = (Decimal('1') + (Decimal(tipo_iva) / Decimal('100')))
                    try:
                        base = (gross / divisor)
                    except Exception:
                        base = Decimal('0')
                    cuota = gross - base

                    base_by_type[tipo_iva] = base_by_type.get(tipo_iva, Decimal('0')) + base
                    iva_by_type[tipo_iva] = iva_by_type.get(tipo_iva, Decimal('0')) + cuota
                except Exception:
                    logging.exception('Error procesando linea ticket en compute_totals_for_ticket_ids')

            # Mapear a campos concretos
            result['base_21'] = base_by_type.get(21, Decimal('0'))
            result['iva_21'] = iva_by_type.get(21, Decimal('0'))
            result['base_4'] = base_by_type.get(4, Decimal('0'))
            result['iva_4'] = iva_by_type.get(4, Decimal('0'))

            result['total_base_imponible'] = sum(base_by_type.values())
            result['total_iva'] = sum(iva_by_type.values())

            # Convert Decimals to floats for caller convenience
            for k in ['total_ingresos', 'total_efectivo', 'total_tarjeta', 'total_web', 'base_21', 'iva_21', 'base_4', 'iva_4', 'total_base_imponible', 'total_iva']:
                try:
                    result[k] = float(result[k])
                except Exception:
                    result[k] = 0.0

            return result
        except Exception:
            logging.exception('Error computing totals for ticket ids')
            return result

    def create_cierre_atomic(self, ticket_ids: List[int], usuario_id: Optional[int], cajero: Optional[str]) -> Optional[int]:
        """Crear un cierre y marcar tickets en una única transacción.

        Retorna el `id` del cierre creado o None en caso de error.
        """
        if not ticket_ids:
            logging.info('No ticket ids provided to create_cierre_atomic')
            return None

        try:
            # asegurar conexión
            self.db.connect()
            conn = getattr(self.db, 'connection', None)
            if conn is None:
                logging.error('No DB connection available for create_cierre_atomic')
                return None

            cur = conn.cursor()
            try:
                cur.execute('BEGIN')

                # Calcular totales
                totals = self.compute_totals_for_ticket_ids(ticket_ids)

                # Obtener siguiente cierre_num
                cur.execute('SELECT MAX(cierre_num) FROM cierres_caja')
                row = cur.fetchone()
                last = int(row[0]) if row and row[0] is not None else 0
                cierre_num = last + 1

                # Preparar campos para insertar
                insert_cols = (
                    'cierre_num', 'fecha_hora', 'cajero', 'total_ingresos', 'num_ventas',
                    'rango_inicio_ticket', 'rango_fin_ticket', 'total_efectivo', 'total_tarjeta',
                    'total_web', 'total_devoluciones', 'total_descuentos',
                    'base_21', 'iva_21', 'base_4', 'iva_4', 'total_base_imponible', 'total_iva',
                    'cierre_text', 'usuario_id'
                )

                # Compute minimal values for devoluciones/discounts as 0 for now
                cierre_text = f"Cierre {cierre_num} - tickets: {len(ticket_ids)}"

                values = (
                    cierre_num,
                    # fecha_hora: use SQLite CURRENT_TIMESTAMP
                    None,
                    cajero,
                    totals.get('total_ingresos', 0.0),
                    totals.get('num_ventas', 0),
                    totals.get('rango_inicio_ticket'),
                    totals.get('rango_fin_ticket'),
                    totals.get('total_efectivo', 0.0),
                    totals.get('total_tarjeta', 0.0),
                    totals.get('total_web', 0.0),
                    0.0,  # total_devoluciones
                    0.0,  # total_descuentos
                    totals.get('base_21', 0.0),
                    totals.get('iva_21', 0.0),
                    totals.get('base_4', 0.0),
                    totals.get('iva_4', 0.0),
                    totals.get('total_base_imponible', 0.0),
                    totals.get('total_iva', 0.0),
                    cierre_text,
                    usuario_id,
                )

                # Build insert SQL mapping None fecha_hora to CURRENT_TIMESTAMP via explicit expression
                insert_sql = (
                    'INSERT INTO cierres_caja (' + ','.join(insert_cols) + ') VALUES (' + ','.join(['?'] * len(insert_cols)) + ')'
                )

                # If fecha_hora is None, use parameter as CURRENT_TIMESTAMP via SQL function - workaround: insert NULL then update
                try:
                    cur.execute(insert_sql, values)
                    cierre_id = cur.lastrowid
                except Exception as e:
                    # Fallback for DBs that don't have the newer IVA columns: insert a reduced set
                    try:
                        import sqlite3 as _sqlite
                        if isinstance(e, _sqlite.OperationalError):
                            fallback_cols = (
                                'cierre_num', 'fecha_hora', 'cajero', 'total_ingresos', 'num_ventas',
                                'rango_inicio_ticket', 'rango_fin_ticket', 'total_efectivo', 'total_tarjeta',
                                'total_web', 'total_devoluciones', 'total_descuentos', 'cierre_text', 'usuario_id'
                            )
                            fallback_values = (
                                cierre_num,
                                None,
                                cajero,
                                totals.get('total_ingresos', 0.0),
                                totals.get('num_ventas', 0),
                                totals.get('rango_inicio_ticket'),
                                totals.get('rango_fin_ticket'),
                                totals.get('total_efectivo', 0.0),
                                totals.get('total_tarjeta', 0.0),
                                totals.get('total_web', 0.0),
                                0.0,
                                0.0,
                                cierre_text,
                                usuario_id,
                            )
                            fallback_sql = 'INSERT INTO cierres_caja (' + ','.join(fallback_cols) + ') VALUES (' + ','.join(['?'] * len(fallback_cols)) + ')'
                            cur.execute(fallback_sql, fallback_values)
                            cierre_id = cur.lastrowid
                        else:
                            raise
                    except Exception:
                        raise

                # If fecha_hora should be set to current timestamp, update it
                try:
                    cur.execute('UPDATE cierres_caja SET fecha_hora = CURRENT_TIMESTAMP WHERE id = ?', (cierre_id,))
                except Exception:
                    pass

                # Marcar tickets con cierre_id
                placeholders = ','.join(['?'] * len(ticket_ids))
                update_sql = f'UPDATE tickets SET cierre_id = ? WHERE id IN ({placeholders})'
                params = (cierre_id, *ticket_ids)
                cur.execute(update_sql, params)

                conn.commit()
                return int(cierre_id)
            except Exception:
                conn.rollback()
                logging.exception('Error creando cierre atómico, transacción revertida')
                return None
        except Exception:
            logging.exception('Error en create_cierre_atomic')
            return None

    def listar_cierres(self, fecha_from: Optional[str] = None, fecha_to: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Listar cierres, opcionalmente filtrando por rango de fecha (fecha_hora).

        Las fechas deben interpretarse por SQLite (ej: 'YYYY-MM-DD' o ISO).
        """
        params = []
        where = ''
        if fecha_from and fecha_to:
            where = 'WHERE fecha_hora BETWEEN ? AND ?'
            params.extend([fecha_from, fecha_to])
        elif fecha_from:
            where = 'WHERE fecha_hora >= ?'
            params.append(fecha_from)
        elif fecha_to:
            where = 'WHERE fecha_hora <= ?'
            params.append(fecha_to)

        sql = f'SELECT * FROM cierres_caja {where} ORDER BY fecha_hora DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        try:
            self.db.connect()
            rows = self.db.fetch_all(sql, tuple(params))
            return [self._row_to_dict(r) for r in rows]
        except Exception:
            logging.exception('Error listando cierres')
            return []

    def ultimo_num_cierre(self) -> Optional[int]:
        sql = 'SELECT MAX(cierre_num) FROM cierres_caja'
        try:
            self.db.connect()
            row = self.db.fetch_one(sql)
            if row and row[0] is not None:
                return int(row[0])
            return None
        except Exception:
            logging.exception('Error obteniendo ultimo num cierre')
            return None

    def borrar_cierre(self, cierre_id: int) -> bool:
        try:
            self.db.connect()
            self.db.execute_query('DELETE FROM cierres_caja WHERE id = ?', (cierre_id,))
            return True
        except Exception:
            logging.exception('Error borrando cierre')
            return False

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        # Mapear columnas en el mismo orden definido en el schema
        cols = [
            'id', 'cierre_num', 'fecha_hora', 'cajero', 'total_ingresos', 'num_ventas',
            'rango_inicio_ticket', 'rango_fin_ticket', 'total_efectivo', 'total_tarjeta',
            'total_web', 'total_devoluciones', 'total_descuentos', 'tesoro_ganado',
            'tesoro_gastado', 'tesoro_total_ganado', 'tesoro_total_gastado', 'cierre_text', 'usuario_id'
        ]
        data = {}
        for i, col in enumerate(cols):
            try:
                data[col] = row[i]
            except Exception:
                data[col] = None
        return data
