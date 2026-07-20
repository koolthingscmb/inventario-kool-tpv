"""Repository para la gestión de pedidos (Cabecera + Líneas)."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class PedidosRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_pedidos(self, estado: Optional[str] = None, cliente_id: Optional[int] = None, termino: str = "") -> List[Dict[str, Any]]:
        """Obtener lista de pedidos (cabeceras)."""
        query = """
            SELECT 
                p.id, p.cliente_id, p.contacto_nombre, p.contacto_telefono, p.contacto_email,
                p.estado, p.fecha_pedido, p.notas_generales, p.usuario_id,
                c.nombre AS cliente_nombre, u.nombre AS usuario_nombre,
                (SELECT COUNT(*) FROM pedidos_clientes_lines pl WHERE pl.pedido_id = p.id) AS num_lineas
            FROM pedidos_clientes p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            WHERE 1=1
        """
        params = []
        if estado:
            query += " AND p.estado = ?"
            params.append(estado)
        if cliente_id:
            query += " AND p.cliente_id = ?"
            params.append(cliente_id)
        if termino:
            term = f"%{termino}%"
            query += " AND (p.contacto_nombre LIKE ? OR p.contacto_telefono LIKE ? OR p.contacto_email LIKE ?)"
            params.extend([term, term, term])

        query += " ORDER BY p.fecha_pedido DESC"
        
        try:
            rows = self.db.fetch_all(query, tuple(params))
            return [dict(row) for row in rows]
        except Exception:
            logger.exception("Error en get_pedidos")
            return []

    def get_lineas_pedido(self, pedido_id: int) -> List[Dict[str, Any]]:
        """Obtener líneas de un pedido."""
        query = """
            SELECT 
                pl.*, pr.nombre AS producto_nombre_db, pr.sku AS producto_sku_db,
                pr.stock_actual AS producto_stock_db,
                t.nombre AS tipo_nombre, prov.nombre AS proveedor_nombre
            FROM pedidos_clientes_lines pl
            LEFT JOIN productos pr ON pl.producto_id = pr.id
            LEFT JOIN tipos t ON pl.tipo_id = t.id
            LEFT JOIN proveedores prov ON pl.proveedor_id = prov.id
            WHERE pl.pedido_id = ?
        """
        try:
            rows = self.db.fetch_all(query, (pedido_id,))
            return [dict(row) for row in rows]
        except Exception:
            logger.exception(f"Error en get_lineas_pedido {pedido_id}")
            return []

    def guardar_pedido_completo(self, cabecera: Dict[str, Any], lineas: List[Dict[str, Any]]) -> Optional[int]:
        """Guarda un pedido completo (cabecera + líneas) en una transacción."""
        try:
            pedido_id = cabecera.get('id')
            with self.db.transaction() as cur:
                if pedido_id:
                    # Actualizar Cabecera
                    query_cab = """
                        UPDATE pedidos_clientes 
                        SET cliente_id = ?, contacto_nombre = ?, contacto_telefono = ?, 
                            contacto_email = ?, estado = ?, notas_generales = ?, usuario_id = ?
                        WHERE id = ?
                    """
                    params_cab = (
                        cabecera.get('cliente_id'),
                        cabecera.get('contacto_nombre'),
                        cabecera.get('contacto_telefono'),
                        cabecera.get('contacto_email'),
                        cabecera.get('estado', 'pendiente'),
                        cabecera.get('notas_generales'),
                        cabecera.get('usuario_id'),
                        pedido_id
                    )
                    cur.execute(query_cab, params_cab)
                    
                    # Borrar líneas viejas (para simplificar la edición)
                    cur.execute("DELETE FROM pedidos_clientes_lines WHERE pedido_id = ?", (pedido_id,))
                else:
                    # 1. Insertar Cabecera
                    query_cab = """
                        INSERT INTO pedidos_clientes 
                        (cliente_id, contacto_nombre, contacto_telefono, contacto_email, estado, notas_generales, usuario_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    params_cab = (
                        cabecera.get('cliente_id'),
                        cabecera.get('contacto_nombre'),
                        cabecera.get('contacto_telefono'),
                        cabecera.get('contacto_email'),
                        cabecera.get('estado', 'pendiente'),
                        cabecera.get('notas_generales'),
                        cabecera.get('usuario_id')
                    )
                    cur.execute(query_cab, params_cab)
                    pedido_id = cur.lastrowid

                # 2. Insertar Líneas
                query_lin = """
                    INSERT INTO pedidos_clientes_lines
                    (pedido_id, producto_id, nombre_manual, tipo_id, proveedor_id, tipo_manual, proveedor_manual, cantidad, estado_linea)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                for lin in lineas:
                    params_lin = (
                        pedido_id,
                        lin.get('producto_id'),
                        lin.get('nombre_manual'),
                        lin.get('tipo_id'),
                        lin.get('proveedor_id'),
                        lin.get('tipo_manual'),
                        lin.get('proveedor_manual'),
                        lin.get('cantidad', 1),
                        lin.get('estado_linea', 'pendiente')
                    )
                    cur.execute(query_lin, params_lin)
                
                return pedido_id
        except Exception:
            logger.exception("Error guardando/actualizando pedido completo")
            return None

    def actualizar_estado_linea(self, linea_id: int, nuevo_estado: str) -> bool:
        """Actualiza el estado de una línea individual."""
        query = "UPDATE pedidos_clientes_lines SET estado_linea = ? "
        params = [nuevo_estado]
        if nuevo_estado == 'en_stock':
            query += ", fecha_en_stock = ? "
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        query += " WHERE id = ?"
        params.append(linea_id)
        try:
            self.db.execute_query(query, tuple(params))
            return True
        except Exception:
            logger.exception(f"Error actualizando estado linea {linea_id}")
            return False

    def get_pedido_por_id(self, pedido_id: int) -> Optional[Dict[str, Any]]:
        """Obtener un pedido completo por su ID."""
        query = """
            SELECT 
                p.*, c.nombre AS cliente_nombre, u.nombre AS usuario_nombre
            FROM pedidos_clientes p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.id = ?
        """
        try:
            row = self.db.fetch_one(query, (pedido_id,))
            if row:
                return dict(row)
            return None
        except Exception:
            logger.exception(f"Error en get_pedido_por_id {pedido_id}")
            return None

    def actualizar_lineas_por_stock(self, producto_ids: List[int]) -> int:
        """Actualiza a 'en_stock' las líneas pendientes de productos que acaban de entrar."""
        if not producto_ids:
            return 0
        placeholders = ','.join(['?'] * len(producto_ids))
        query = f"""
            UPDATE pedidos_clientes_lines
            SET estado_linea = 'en_stock', fecha_en_stock = CURRENT_TIMESTAMP
            WHERE estado_linea = 'pendiente'
            AND producto_id IN ({placeholders})
            AND producto_id IN (SELECT id FROM productos WHERE stock_actual >= 1)
        """
        try:
            cursor = self.db.execute_query(query, tuple(producto_ids))
            return cursor.rowcount if cursor else 0
        except Exception:
            logger.exception("Error en actualizar_lineas_por_stock")
            return 0

    def actualizar_estado_pedido(self, pedido_id: int, nuevo_estado: str) -> bool:
        """Actualizar solo el estado de la cabecera del pedido."""
        query = "UPDATE pedidos_clientes SET estado = ? WHERE id = ?"
        try:
            self.db.execute_query(query, (nuevo_estado, pedido_id))
            return True
        except Exception:
            logger.exception(f"Error actualizando estado pedido {pedido_id}")
            return False

    def borrar_pedido(self, pedido_id: int) -> bool:
        """Borrar un pedido y sus líneas."""
        try:
            with self.db.transaction() as cur:
                cur.execute("DELETE FROM pedidos_clientes_lines WHERE pedido_id = ?", (pedido_id,))
                cur.execute("DELETE FROM pedidos_clientes WHERE id = ?", (pedido_id,))
                return True
        except Exception:
            logger.exception(f"Error borrando pedido {pedido_id}")
            return False
