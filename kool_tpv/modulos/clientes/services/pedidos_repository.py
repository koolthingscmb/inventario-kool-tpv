"""Repository para la gestión de pedidos (Cabecera + Líneas)."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from kool_tpv.base_datos.db_wrapper import Database

logger = logging.getLogger(__name__)

class PedidosRepository:
    def __init__(self, db: Database):
        self.db = db
        # Migración automática de IDs de estado de 'en_stock' a 'distribuidor'
        try:
            self.db.execute_query("UPDATE pedidos_clientes SET estado = 'distribuidor' WHERE estado = 'en_stock'")
            self.db.execute_query("UPDATE pedidos_clientes_lines SET estado_linea = 'distribuidor' WHERE estado_linea = 'en_stock'")
        except:
            pass

    def get_pedidos(self, estado: Optional[str] = None, cliente_id: Optional[int] = None, termino: str = "") -> List[Dict[str, Any]]:
        """Obtener lista de pedidos. Devuelve una fila por cada línea de producto."""
        query = """
            SELECT 
                p.id, p.cliente_id, p.contacto_nombre, p.contacto_telefono, p.contacto_email,
                p.estado, p.fecha_pedido, p.notas_generales, p.usuario_id,
                c.nombre AS cliente_nombre, u.nombre AS usuario_nombre,
                COALESCE(pr.nombre, pl.nombre_manual) AS linea_producto_nombre,
                pl.cantidad AS linea_unidades,
                (SELECT COUNT(*) FROM pedidos_clientes_lines pl2 WHERE pl2.pedido_id = p.id) AS num_lineas
            FROM pedidos_clientes p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            LEFT JOIN pedidos_clientes_lines pl ON p.id = pl.pedido_id
            LEFT JOIN productos pr ON pl.producto_id = pr.id
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
            query += " AND (p.contacto_nombre LIKE ? OR p.contacto_telefono LIKE ? OR p.contacto_email LIKE ? OR p.notas_generales LIKE ? OR pl.nombre_manual LIKE ? OR pr.nombre LIKE ?)"
            params.extend([term, term, term, term, term, term])

        # Orden: 
        # 1. Por estado (entregado va al final). Usamos un CASE para asignar peso.
        # 2. Por fecha_pedido (más actual arriba)
        # 3. Por pedido_id (para agrupar las líneas del mismo pedido)
        query += """
            ORDER BY 
                CASE 
                    WHEN p.estado = 'entregado' THEN 1 
                    ELSE 0 
                END ASC,
                p.fecha_pedido DESC,
                p.id DESC
        """
        
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
        """Actualiza el estado de una línea individual y sincroniza la cabecera si es necesario."""
        query = "UPDATE pedidos_clientes_lines SET estado_linea = ? "
        params = [nuevo_estado]
        if nuevo_estado == 'distribuidor':
            query += ", fecha_en_stock = ? "
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        query += " WHERE id = ?"
        params.append(linea_id)
        try:
            with self.db.transaction() as cur:
                cur.execute(query, tuple(params))
                
                # Obtener el pedido_id de esta línea
                row = self.db.fetch_one("SELECT pedido_id FROM pedidos_clientes_lines WHERE id = ?", (linea_id,))
                if row:
                    pedido_id = row[0]
                    # Si la línea se marca como entregada, comprobar si el pedido completo debe marcarse como entregado
                    if nuevo_estado == 'entregado':
                        # Contar líneas que NO están entregadas
                        res = self.db.fetch_one("""
                            SELECT COUNT(*) FROM pedidos_clientes_lines 
                            WHERE pedido_id = ? AND estado_linea != 'entregado'
                        """, (pedido_id,))
                        
                        if res and res[0] == 0:
                            # Todas las líneas entregadas -> Pedido entregado
                            cur.execute("UPDATE pedidos_clientes SET estado = 'entregado' WHERE id = ?", (pedido_id,))
                            logger.info(f"Pedido {pedido_id} marcado como ENTREGADO automáticamente.")
                    
                    # Si se marca como pendiente/distribuidor/avisado, y el pedido estaba entregado, volver a pendiente
                    elif nuevo_estado in ['pendiente', 'distribuidor', 'avisado']:
                        res_ped = self.db.fetch_one("SELECT estado FROM pedidos_clientes WHERE id = ?", (pedido_id,))
                        if res_ped and res_ped[0] == 'entregado':
                            cur.execute("UPDATE pedidos_clientes SET estado = 'pendiente' WHERE id = ?", (pedido_id,))

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
        """Actualiza a 'distribuidor' las líneas pendientes de productos que acaban de entrar."""
        if not producto_ids:
            return 0
        placeholders = ','.join(['?'] * len(producto_ids))
        query = f"""
            UPDATE pedidos_clientes_lines
            SET estado_linea = 'distribuidor', fecha_en_stock = CURRENT_TIMESTAMP
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

    def get_lineas_pendientes_por_producto(self, producto_id: int) -> List[Dict[str, Any]]:
        """Obtener líneas pendientes asociadas a un producto, con info del cliente."""
        query = """
            SELECT 
                pl.id AS linea_id, pl.pedido_id, pl.cantidad,
                p.contacto_nombre, c.nombre AS cliente_nombre
            FROM pedidos_clientes_lines pl
            JOIN pedidos_clientes p ON pl.pedido_id = p.id
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE pl.producto_id = ? AND pl.estado_linea IN ('pendiente', 'distribuidor')
        """
        try:
            rows = self.db.fetch_all(query, (producto_id,))
            return [dict(row) for row in rows]
        except Exception:
            logger.exception(f"Error en get_lineas_pendientes_por_producto {producto_id}")
            return []

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
