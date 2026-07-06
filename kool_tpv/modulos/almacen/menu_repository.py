from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class MenuRepository:
    """Repository para gestionar la relación de componentes de un producto-menú."""
    
    def __init__(self, db):
        self.db = db

    def crear_menu(self, producto_id: int, componentes: List[Dict], cur=None) -> bool:
        """Crea la relación de componentes para un menú y marca el producto como es_menu=1.
        
        componentes: Lista de dicts con {'componente_id': int, 'cantidad': int}
        """
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
        
        try:
            # 1. Marcar el producto como menú
            cur.execute('UPDATE productos SET es_menu = 1 WHERE id = ?', (producto_id,))
            
            # 2. Insertar componentes
            for comp in componentes:
                cur.execute(
                    'INSERT INTO productos_menu (producto_id, componente_id, cantidad) VALUES (?, ?, ?)',
                    (producto_id, comp['componente_id'], comp['cantidad'])
                )
            
            if not use_external_cursor:
                self.db.connection.commit()
            return True
        except Exception:
            if not use_external_cursor:
                self.db.connection.rollback()
            logger.exception("Error creando componentes de menú para producto_id=%s", producto_id)
            raise

    def get_componentes(self, producto_id: int) -> List[Dict]:
        """Obtiene los componentes de un menú con información del producto."""
        query = '''
            SELECT pm.componente_id, p.nombre, p.sku, pm.cantidad, p.stock_actual
            FROM productos_menu pm
            JOIN productos p ON pm.componente_id = p.id
            WHERE pm.producto_id = ?
        '''
        rows = self.db.fetch_all(query, (producto_id,))
        return [
            {
                'componente_id': r[0],
                'nombre': r[1],
                'sku': r[2],
                'cantidad': r[3],
                'stock_actual': r[4]
            } for r in rows
        ]

    def actualizar_componentes(self, producto_id: int, componentes: List[Dict], cur=None) -> bool:
        """Borra los componentes actuales y guarda los nuevos."""
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
        
        try:
            # 1. Borrar componentes antiguos
            cur.execute('DELETE FROM productos_menu WHERE producto_id = ?', (producto_id,))
            
            # 2. Insertar nuevos
            for comp in componentes:
                cur.execute(
                    'INSERT INTO productos_menu (producto_id, componente_id, cantidad) VALUES (?, ?, ?)',
                    (producto_id, comp['componente_id'], comp['cantidad'])
                )
            
            # 3. Asegurar que está marcado como menú (por si acaso)
            cur.execute('UPDATE productos SET es_menu = 1 WHERE id = ?', (producto_id,))
            
            if not use_external_cursor:
                self.db.connection.commit()
            return True
        except Exception:
            if not use_external_cursor:
                self.db.connection.rollback()
            logger.exception("Error actualizando componentes de menú para producto_id=%s", producto_id)
            raise

    def eliminar_menu(self, producto_id: int, cur=None) -> bool:
        """Elimina la relación de componentes y desmarca el producto como menú."""
        use_external_cursor = cur is not None
        if not use_external_cursor:
            cur = self.db.connection.cursor()
            cur.execute('BEGIN')
        
        try:
            cur.execute('DELETE FROM productos_menu WHERE producto_id = ?', (producto_id,))
            cur.execute('UPDATE productos SET es_menu = 0 WHERE id = ?', (producto_id,))
            
            if not use_external_cursor:
                self.db.connection.commit()
            return True
        except Exception:
            if not use_external_cursor:
                self.db.connection.rollback()
            logger.exception("Error eliminando menú para producto_id=%s", producto_id)
            raise

    def get_menuses(self) -> List[Dict]:
        """Lista todos los productos que son menús con sus datos básicos y precio actual."""
        query = '''
            SELECT p.id, p.nombre, p.sku, p.categoria, p.tipo, pr.pvp,
                   (SELECT COUNT(*) FROM productos_menu WHERE producto_id = p.id) as num_componentes
            FROM productos p
            LEFT JOIN precios pr ON p.id = pr.producto_id AND pr.activo = 1
            WHERE p.es_menu = 1
            ORDER BY p.nombre
        '''
        rows = self.db.fetch_all(query)
        return [
            {
                'id': r[0],
                'nombre': r[1],
                'sku': r[2],
                'categoria_id': r[3],
                'tipo_id': r[4],
                'pvp_cents': r[5],
                'num_componentes': r[6]
            } for r in rows
        ]

    def get_componentes_para_venta(self, producto_id: int, cur=None) -> List[Tuple[int, int]]:
        """Obtiene tuplas (componente_id, cantidad) optimizado para el TPV."""
        query = 'SELECT componente_id, cantidad FROM productos_menu WHERE producto_id = ?'
        if cur:
            cur.execute(query, (producto_id,))
            rows = cur.fetchall()
        else:
            rows = self.db.fetch_all(query, (producto_id,))
        return [(r[0], r[1]) for r in rows]

    def get_es_menu(self, producto_id: int, cur=None) -> bool:
        """Verifica si un producto es menú."""
        query = 'SELECT es_menu FROM productos WHERE id = ?'
        if cur:
            cur.execute(query, (producto_id,))
            r = cur.fetchone()
        else:
            r = self.db.fetch_one(query, (producto_id,))
        return bool(r[0]) if r and r[0] else False
