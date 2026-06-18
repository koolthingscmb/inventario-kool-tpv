"""Servicio de acceso a datos para la tabla `cierres`.

Provee métodos básicos para insertar, listar y obtener cierres.
"""
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
import json
from datetime import datetime, timezone


class CierreService:
    def get_puntos_resumen_cierre(self, ticket_ids: list) -> dict:
        """Obtener resumen de puntos (totales + por cliente) para un cierre.

        Args:
            ticket_ids: Lista de IDs de tickets del cierre

        Returns:
            Dict con: tesoro_otorgado, tesoro_gastado, clientes_puntos
        """

        logging.info(f"DEBUG: get_puntos_resumen_cierre() llamado con ticket_ids={ticket_ids}")
        from kool_tpv.modulos.fidelizacion.fidelizacion_repository import FidelizacionRepository
        from decimal import Decimal as _D

        result = {
            'tesoro_otorgado': _D('0'),
            'tesoro_gastado': _D('0'),
            'clientes_puntos': []
        }

        if not ticket_ids:
            return result

        try:
            fid_repo = FidelizacionRepository(self.db)
            clientes_data = fid_repo.get_puntos_por_cliente_para_tickets(ticket_ids)
            logging.info(f"DEBUG: clientes_data retornado={clientes_data}")

            if not clientes_data:
                return result

            # Agregar lista de clientes
            result['clientes_puntos'] = clientes_data

            # Calcular totales
            total_ganados = _D('0')
            total_gastados = _D('0')

            for cliente in clientes_data:
                try:
                    total_ganados += _D(str(cliente.get('puntos_ganados', 0)))
                    total_gastados += _D(str(cliente.get('puntos_gastados', 0)))
                except Exception:
                    continue

            result['tesoro_otorgado'] = total_ganados
            result['tesoro_gastado'] = total_gastados

            return result

        except Exception:
            logging.exception('Error obteniendo resumen de puntos para cierre')
            return result
    def __init__(self, db):
        """Crear servicio usando el wrapper `Database` del proyecto.

        Args:
            db: instancia de `kool_tpv.base_datos.db_wrapper.Database`
        """
        self.db = db

    def ensure_table(self):
        try:
            # Sólo comprobar existencia; las migraciones deben crear el esquema.
            self.db.connect()
            row = self.db.fetch_one("SELECT name FROM sqlite_master WHERE type='table' AND name='cierres'")
            if not row:
                logging.error("Tabla 'cierres' no encontrada. Ejecuta las migraciones (scripts/migrate_cierres.sql)")
                return False
            return True
        except Exception:
            logging.exception('Error comprobando existencia de la tabla cierres')
            return False

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
        sql = f'INSERT INTO cierres ({",".join(cols)}) VALUES ({placeholders})'
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
        sql = 'SELECT * FROM cierres WHERE id = ?'
        try:
            self.db.connect()
            row = self.db.fetch_one(sql, (cierre_id,))
            if not row:
                return None
            data = self._row_to_dict(row)
            
            # Cargar lista de clientes con puntos para este cierre si existen líneas
            try:
                lineas = self.db.fetch_all('SELECT ticket_id FROM cierres_lineas WHERE cierre_id = ?', (cierre_id,))
                if lineas:
                    ticket_ids = [r[0] for r in lineas]
                    puntos_resumen = self.get_puntos_resumen_cierre(ticket_ids)
                    if puntos_resumen and puntos_resumen.get('clientes_puntos'):
                        # Guardar temporalmente en una clave que el procesador pueda usar
                        data['_clientes_puntos'] = puntos_resumen.get('clientes_puntos')
            except Exception:
                pass
                
            return data
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
            'total_facturas': Decimal('0'),
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

            # Obtener datos principales de tickets (totales y pagos en céntimos)
            sql_tickets = f"SELECT id, num_ticket, created_at, total, forma_pago, importe_efectivo, cambio, importe_tarjeta FROM tickets WHERE id IN ({placeholders})"
            self.db.connect()
            ticket_rows = self.db.fetch_all(sql_tickets, tuple(ticket_ids))

            from kool_tpv.base_datos.money_adapter import read_from_db

            nums = []
            # Sum only positive ticket totals as `total_facturas` (facturas)
            total_facturas = Decimal('0')
            for tr in ticket_rows or []:
                try:
                    total_cents = int(tr[3] or 0)
                    total_euros = read_from_db(total_cents)
                    if total_cents >= 0:
                        total_facturas += total_euros
                except Exception:
                    pass
                try:
                    importe_ef_cents = int(tr[5] or 0)
                    cambio_cents = int(tr[6] or 0)
                    importe_ef = read_from_db(importe_ef_cents)
                    cambio = read_from_db(cambio_cents)
                    net_ef = importe_ef - cambio
                    result['total_efectivo'] += net_ef
                except Exception:
                    pass
                try:
                    ta_cents = int(tr[7] or 0)
                    ta = read_from_db(ta_cents)
                    result['total_tarjeta'] += ta
                except Exception:
                    pass
                # web/otros no siempre presentes: inferir desde forma_pago
                try:
                    forma = (tr[4] or '').lower() if tr[4] else ''
                    if forma and 'web' in forma:
                        total_cents = int(tr[3] or 0)
                        result['total_web'] += read_from_db(total_cents)
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
            # track totals for discounts and devoluciones
            total_descuentos = Decimal('0')
            total_devoluciones = Decimal('0')
            for ln in lines or []:
                try:
                    cantidad = Decimal(str(ln[1] or 0))
                    # precio stored in DB as cents -> convert to euros (Decimal)
                    precio_cents = int(ln[2] or 0)
                    from kool_tpv.base_datos.money_adapter import read_from_db as _r
                    precio = _r(precio_cents)
                    tipo_iva = int(float(ln[3])) if ln[3] is not None else 21
                    line_tipo = ln[4] if len(ln) > 4 else 'venta'
                    # determine effective gross: precio already can be negative (discounts)
                    sign = Decimal('-1') if str(line_tipo) == 'devolucion' else Decimal('1')
                    gross = precio * cantidad * sign

                    # accumulate discounts/devoluciones separately for reporting
                    if str(line_tipo) == 'descuento':
                        try:
                            total_descuentos += abs(gross)
                        except Exception:
                            pass
                    if str(line_tipo) == 'devolucion':
                        try:
                            total_devoluciones += abs(gross)
                        except Exception:
                            pass
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

            # Mapear a campos concretos (mantener Decimal en memoria)
            result['base_21'] = base_by_type.get(21, Decimal('0'))
            result['iva_21'] = iva_by_type.get(21, Decimal('0'))
            result['base_4'] = base_by_type.get(4, Decimal('0'))
            result['iva_4'] = iva_by_type.get(4, Decimal('0'))

            result['total_base_imponible'] = sum(base_by_type.values())
            result['total_iva'] = sum(iva_by_type.values())

            # totals for discounts and devoluciones (Decimal)
            result['total_descuentos'] = total_descuentos
            result['total_devoluciones'] = total_devoluciones

            # Persist facturas and set total_ingresos to net ventas (facturas - devoluciones)
            result['total_facturas'] = total_facturas
            try:
                # Los descuentos YA están incluidos en total_facturas (viene del ticket total final)
                # Solo restar devoluciones, no restar descuentos de nuevo
                result['total_ingresos'] = total_facturas - total_devoluciones
            except Exception:
                result['total_ingresos'] = Decimal('0')

            # Construir desglose IVA por tipo para uso en snapshot/BD (mantener Decimal)
            iva_desglose = {}
            for t, base in base_by_type.items():
                cuota = iva_by_type.get(t, Decimal('0'))
                iva_desglose[str(int(t))] = {
                    'base': base,
                    'iva': cuota
                }
            result['iva_desglose'] = iva_desglose

            # Calcular tesoro (puntos) asociados a los tickets
            try:
                placeholders = ','.join(['?'] * len(ticket_ids))
                q = f"SELECT COALESCE(SUM(CASE WHEN puntos>0 THEN puntos ELSE 0 END),0), COALESCE(SUM(CASE WHEN puntos<0 THEN -puntos ELSE 0 END),0) FROM points_movements WHERE ticket_id IN ({placeholders})"
                row = self.db.fetch_one(q, tuple(ticket_ids))
                # Representar tesoro en memoria como Decimal (consistencia de tipos en memoria)
                from decimal import Decimal as _D
                otorgado = _D(str(int(row[0] or 0)))
                gastado = _D(str(int(row[1] or 0)))
                result['tesoro_otorgado'] = otorgado
                result['tesoro_gastado'] = gastado
            except Exception:
                from decimal import Decimal as _D
                result['tesoro_otorgado'] = _D('0')
                result['tesoro_gastado'] = _D('0')

            # Ensure iva_desglose present
            if 'iva_desglose' not in result:
                result['iva_desglose'] = {}

            # result now holds Decimal monetary values for in-memory use
            return result
        except Exception:
            logging.exception('Error computing totals for ticket ids')
            return result

    def create_cierre_atomic(self, ticket_ids: List[int], usuario_id: Optional[int], cajero: Optional[str], cierre_text: Optional[str] = None) -> Optional[int]:
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

            try:
                # Use the Database.transaction context manager to avoid nested BEGIN
                with self.db.transaction() as cur:

                    # Calcular totales
                    totals = self.compute_totals_for_ticket_ids(ticket_ids)

                    # Obtener siguiente cierre_num
                    cur.execute('SELECT MAX(cierre_num) FROM cierres')
                    row = cur.fetchone()
                    last = int(row[0]) if row and row[0] is not None else 0
                    cierre_num = last + 1

                # Preparar campos para insertar
                insert_cols = (
                    'cierre_num', 'fecha_hora', 'cajero', 'total_ingresos', 'num_ventas',
                    'rango_inicio_ticket', 'rango_fin_ticket', 'total_efectivo', 'total_tarjeta',
                    'total_web', 'total_devoluciones', 'total_descuentos',
                    'tesoro_ganado', 'tesoro_gastado', 'iva_desglose',
                    'base_21', 'iva_21', 'base_4', 'iva_4', 'total_base_imponible', 'total_iva',
                    'cierre_text', 'usuario_id'
                )

                # Compute minimal values for devoluciones/discounts as 0 for now
                if cierre_text is None:
                    # Build a human-friendly cierre code and store it in cierre_text.
                    # Keep `cierre_num` as the integer sequential number for audit/queries.
                    now_for_code = datetime.now(timezone.utc)
                    cierre_code = f"CKD-{now_for_code.day:02d}-{now_for_code.month:02d}-{now_for_code.year}-{cierre_num:06d}"
                    cierre_text = cierre_code

                # Ensure monetary fields are stored as integer céntimos in DB
                from kool_tpv.base_datos.money_adapter import prepare_for_db

                # Capture fecha_hora in Python to avoid relying on SQLite CURRENT_TIMESTAMP
                # use UTC for DB timestamps
                fecha_hora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

                # Prepare iva_desglose for DB serialization (convert Decimal -> céntimos int)
                iva_desglose_obj = totals.get('iva_desglose', {}) or {}
                iva_desglose_serializable = {}
                try:
                    for k, v in iva_desglose_obj.items():
                        try:
                            base_v = v.get('base') if isinstance(v, dict) else None
                            iva_v = v.get('iva') if isinstance(v, dict) else None
                            # Use prepare_for_db to enforce DB contract: store as int céntimos
                            base_cents = prepare_for_db(base_v) if base_v is not None else 0
                            iva_cents = prepare_for_db(iva_v) if iva_v is not None else 0
                            iva_desglose_serializable[str(k)] = {
                                'base': int(base_cents),
                                'iva': int(iva_cents),
                            }
                        except Exception:
                            iva_desglose_serializable[str(k)] = {'base': 0, 'iva': 0}
                except Exception:
                    iva_desglose_serializable = {}

                values = (
                    cierre_num,
                    # fecha_hora: captured in Python
                    fecha_hora,
                    cajero,
                    prepare_for_db(totals.get('total_ingresos', 0.0)),
                    totals.get('num_ventas', 0),
                    totals.get('rango_inicio_ticket'),
                    totals.get('rango_fin_ticket'),
                    prepare_for_db(totals.get('total_efectivo', 0.0)),
                    prepare_for_db(totals.get('total_tarjeta', 0.0)),
                    prepare_for_db(totals.get('total_web', 0.0)),
                    prepare_for_db(totals.get('total_devoluciones', 0.0)),
                    prepare_for_db(totals.get('total_descuentos', 0.0)),
                    # tesoro (puntos): kept as Decimal in-memory, persist as int
                    int(totals.get('tesoro_otorgado', Decimal('0'))),
                    int(totals.get('tesoro_gastado', Decimal('0'))),
                    json.dumps(iva_desglose_serializable, ensure_ascii=False),
                    prepare_for_db(totals.get('base_21', 0.0)),
                    prepare_for_db(totals.get('iva_21', 0.0)),
                    prepare_for_db(totals.get('base_4', 0.0)),
                    prepare_for_db(totals.get('iva_4', 0.0)),
                    prepare_for_db(totals.get('total_base_imponible', 0.0)),
                    prepare_for_db(totals.get('total_iva', 0.0)),
                    cierre_text,
                    usuario_id,
                )

                # Build insert SQL mapping None fecha_hora to CURRENT_TIMESTAMP via explicit expression
                insert_sql = (
                    'INSERT INTO cierres (' + ','.join(insert_cols) + ') VALUES (' + ','.join(['?'] * len(insert_cols)) + ')'
                )

                # If fecha_hora is None, use parameter as CURRENT_TIMESTAMP via SQL function - workaround: insert NULL then update
                # Ejecutar insert principal; si falla, dejar que la excepción llegue
                cur.execute(insert_sql, values)
                cierre_id = cur.lastrowid

                # Marcar tickets con cierre_id
                placeholders = ','.join(['?'] * len(ticket_ids))
                update_sql = f'UPDATE tickets SET cierre_id = ? WHERE id IN ({placeholders})'
                params = (cierre_id, *ticket_ids)
                cur.execute(update_sql, params)

                # commit handled by Database.transaction
                return int(cierre_id)
            except Exception:
                logging.exception('Error creando cierre atómico, transacción revertida')
                return None
        except Exception:
            logging.exception('Error en create_cierre_atomic')
            return None

    def listar_cierres(self, termino: str = '', fecha_from: Optional[str] = None, fecha_to: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Listar cierres, filtrando por término (cajero o nº cierre) y rango de fechas."""
        params = []
        where_parts = []
        
        if termino:
            like = f"%{termino}%"
            where_parts.append("(cajero LIKE ? OR CAST(cierre_num AS TEXT) LIKE ?)")
            params.extend([like, like])
            
        if fecha_from and fecha_to:
            where_parts.append("fecha_hora BETWEEN ? AND ?")
            params.extend([fecha_from + " 00:00:00", fecha_to + " 23:59:59"])
        elif fecha_from:
            where_parts.append("fecha_hora >= ?")
            params.append(fecha_from + " 00:00:00")
        elif fecha_to:
            where_parts.append("fecha_hora <= ?")
            params.append(fecha_to + " 23:59:59")

        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
        
        sql = f'SELECT * FROM cierres {where} ORDER BY fecha_hora DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        try:
            self.db.connect()
            rows = self.db.fetch_all(sql, tuple(params))
            return [self._row_to_dict(r) for r in rows]
        except Exception:
            logging.exception('Error listando cierres')
            return []

    def get_cierre_lineas(self, cierre_id: int) -> List[Dict[str, Any]]:
        """Obtener todas las líneas de un cierre desde cierres_lineas.

        Args:
            cierre_id: ID del cierre

        Returns:
            Lista de dicts con: id, ticket_id, ticket_num, ticket_total, forma_pago, etc.
        """

        sql = 'SELECT id, ticket_id, ticket_num, ticket_total, forma_pago, efectivo, tarjeta FROM cierres_lineas WHERE cierre_id = ? ORDER BY id ASC'

        try:
            self.db.connect()
            rows = self.db.fetch_all(sql, (cierre_id,))

            result: List[Dict[str, Any]] = []
            ticket_ids = [r[1] for r in (rows or []) if r and len(r) > 1]

            # Obtener recuento de líneas por ticket desde ticket_lines
            counts: Dict[int, int] = {}
            if ticket_ids:
                try:
                    placeholders = ','.join(['?'] * len(ticket_ids))
                    q = f"SELECT ticket_id, COUNT(*) FROM ticket_lines WHERE ticket_id IN ({placeholders}) GROUP BY ticket_id"
                    cnt_rows = self.db.fetch_all(q, tuple(ticket_ids))
                    for cr in cnt_rows or []:
                        try:
                            counts[int(cr[0])] = int(cr[1] or 0)
                        except Exception:
                            continue
                except Exception:
                    logging.exception('Error contando líneas de ticket en get_cierre_lineas')

            for r in rows or []:
                try:
                    tid = r[1]
                    num_lines = counts.get(int(tid), 0) if tid is not None else 0
                    result.append({
                        'id': r[0],
                        'ticket_id': r[1],
                        'ticket_num': r[2],
                        'ticket_total': r[3],
                        'forma_pago': r[4],
                        # compute efectivo neto = importe_efectivo - cambio and tarjeta from tickets
                        'efectivo': None,
                        'tarjeta': None,
                        'num_lineas': num_lines,
                        'num_ventas': num_lines,
                    })
                except Exception:
                    continue

            # Fill efectivo/tarjeta from tickets table to ensure net efectivo (importe_efectivo - cambio)
            try:
                if ticket_ids:
                    placeholders = ','.join(['?'] * len(ticket_ids))
                    q = f"SELECT id, COALESCE(importe_efectivo,0), COALESCE(cambio,0), COALESCE(importe_tarjeta,0) FROM tickets WHERE id IN ({placeholders})"
                    ticket_rows = self.db.fetch_all(q, tuple(ticket_ids))
                    ticket_map = {r[0]: (int(r[1] or 0), int(r[2] or 0), int(r[3] or 0)) for r in (ticket_rows or [])}
                else:
                    ticket_map = {}

                for item in result:
                    tid = item.get('ticket_id')
                    if tid is None:
                        item['efectivo'] = 0
                        item['tarjeta'] = 0
                        continue
                    ief, cambio, itar = ticket_map.get(tid, (0, 0, 0))
                    try:
                        net_ef = int(ief) - int(cambio)
                    except Exception:
                        net_ef = 0
                    try:
                        tar_val = int(itar)
                    except Exception:
                        tar_val = 0
                    item['efectivo'] = net_ef
                    item['tarjeta'] = tar_val
            except Exception:
                logging.exception('Error rellenando efectivo/tarjeta en get_cierre_lineas')

            return result

        except Exception:
            logging.exception('Error obteniendo líneas de cierre')
            return []

    def get_ventas_por_forma_pago(self, cierre_id: int) -> Dict[str, int]:
        """Devolver conteo de tickets agrupado por `forma_pago` para un cierre.

        Retorna un dict: {'efectivo': 2, 'tarjeta': 3, 'web': 1}
        """
        try:
            # Normalizar forma_pago a lowercase/trim y contar tickets únicos
            sql = (
                "SELECT LOWER(TRIM(COALESCE(forma_pago, 'UNKNOWN'))), COUNT(DISTINCT ticket_id) "
                "FROM cierres_lineas WHERE cierre_id = ? GROUP BY LOWER(TRIM(COALESCE(forma_pago, 'UNKNOWN')))"
            )
            self.db.connect()
            rows = self.db.fetch_all(sql, (cierre_id,))
            result: Dict[str, int] = {}
            for r in rows or []:
                try:
                    key = (r[0] or 'unknown')
                    result[str(key)] = int(r[1] or 0)
                except Exception:
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por forma de pago')
            return {}

    def get_ventas_por_cajero_para_tickets(self, ticket_ids: List[int]) -> List[tuple]:
        """Devuelve lista de (cajero, numero_ventas, total_euros) para una lista de IDs de tickets.
        
        Usado durante la creación del cierre (antes de que los tickets tengan asignado cierre_id).
        """
        if not ticket_ids:
            return []
        try:
            placeholders = ','.join(['?'] * len(ticket_ids))
            sql = f'SELECT cajero, COUNT(*), SUM(total) FROM tickets WHERE id IN ({placeholders}) GROUP BY cajero'
            self.db.connect()
            rows = self.db.fetch_all(sql, tuple(ticket_ids))
            result: List[tuple] = []
            from kool_tpv.base_datos.money_adapter import read_from_db
            for r in rows or []:
                try:
                    cajero = r[0] or 'N/A'
                    cnt = int(r[1] or 0)
                    total_cents = int(r[2] or 0)
                    total_euros = float(read_from_db(total_cents))
                    result.append((cajero, cnt, total_euros))
                except Exception:
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por cajero para tickets')
            return []

    def get_ventas_por_cajero(self, cierre_id: int) -> List[tuple]:
        """Devuelve lista de (cajero, numero_ventas, total_euros) para un cierre.

        Query sobre `tickets` y conversión de totales (céntimos -> euros) con `read_from_db`.
        """
        try:
            sql = 'SELECT cajero, COUNT(*), SUM(total) FROM tickets WHERE cierre_id = ? GROUP BY cajero'
            self.db.connect()
            rows = self.db.fetch_all(sql, (cierre_id,))
            result: List[tuple] = []
            from kool_tpv.base_datos.money_adapter import read_from_db
            for r in rows or []:
                try:
                    cajero = r[0] or ''
                    cnt = int(r[1] or 0)
                    total_cents = int(r[2] or 0)
                    total_euros = float(read_from_db(total_cents))
                    result.append((cajero, cnt, total_euros))
                except Exception:
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por cajero')
            return []

    def get_ventas_por_categoria(self, cierre_id: int) -> List[tuple]:
        """Devuelve lista de (nombre_categoria, nº_ventas, total_euros) para un cierre.

        Se agrupa por categoría usando las líneas de los tickets incluidos en el cierre.
        """
        try:
            sql = (
                "SELECT c.nombre, COUNT(DISTINCT tl.ticket_id) as tickets_cnt, "
                "COALESCE(SUM(tl.cantidad * tl.precio),0) as total_cents "
                "FROM ticket_lines tl "
                "JOIN productos p ON tl.producto_id = p.id "
                "JOIN categorias c ON p.categoria = c.id "
                "WHERE tl.ticket_id IN (SELECT ticket_id FROM cierres_lineas WHERE cierre_id = ?) "
                "GROUP BY c.id, c.nombre"
            )
            self.db.connect()
            rows = self.db.fetch_all(sql, (cierre_id,))
            result: List[tuple] = []
            from kool_tpv.base_datos.money_adapter import read_from_db
            for r in rows or []:
                try:
                    nombre = r[0] or ''
                    cnt = int(r[1] or 0)
                    total_cents = int(r[2] or 0)
                    total_euros = float(read_from_db(total_cents))
                    result.append((nombre, cnt, total_euros))
                except Exception:
                    continue
            return result
        except Exception:
            logging.exception('Error obteniendo ventas por categoría')
            return []

    def ultimo_num_cierre(self) -> Optional[int]:
        sql = 'SELECT MAX(cierre_num) FROM cierres'
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
            self.db.execute_query('DELETE FROM cierres WHERE id = ?', (cierre_id,))
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
            'tesoro_gastado', 'tesoro_total_ganado', 'tesoro_total_gastado', 'cierre_text', 'usuario_id',
            'total_base_imponible', 'total_iva', 'base_21', 'iva_21', 'base_4', 'iva_4', 'iva_desglose', 'created_at', 'printed', 'printed_at', 'printer_name'
        ]
        data = {}
        for i, col in enumerate(cols):
            try:
                data[col] = row[i]
            except Exception:
                data[col] = None
        return data
