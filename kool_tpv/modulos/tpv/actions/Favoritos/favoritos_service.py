import logging
from typing import List, Optional
from decimal import Decimal
from kool_tpv.base_datos.money_adapter import read_from_db
from .favoritos_repository import FavoritosRepository

logger = logging.getLogger(__name__)

class FavoritosService:
    def __init__(self, db):
        self.db = db
        self.repo = FavoritosRepository(db)

    def listar_favoritos(self) -> List[dict]:
        """Lista favoritos procesando valores monetarios."""
        items = self.repo.get_all()
        for item in items:
            # Normalizar PVP
            pvp_raw = item.get('pvp', 0)
            try:
                if pvp_raw is None:
                    item['pvp'] = Decimal('0.00')
                else:
                    item['pvp'] = read_from_db(int(pvp_raw))
            except Exception:
                item['pvp'] = Decimal('0.00')
        return items

    def agregar_a_favoritos(self, producto_id: int, nombre: Optional[str] = None) -> dict:
        """Agrega un producto a favoritos.

        Returns:
            dict con 'success' (bool) y 'duplicado' (bool).
        """
        # Verificar si ya existe
        query_check = "SELECT id FROM favoritos WHERE producto_id = ?"
        try:
            existe = self.db.fetch_one(query_check, (producto_id,))
            if existe:
                return {"success": False, "duplicado": True}
        except Exception:
            logger.exception("Error verificando duplicado en favoritos")
            return {"success": False, "duplicado": False}

        if not nombre:
            query = "SELECT nombre FROM productos WHERE id = ?"
            res = self.db.fetch_one(query, (producto_id,))
            nombre = res[0] if res else "Producto"
        
        pos = self.repo.get_next_posicion()
        ok = self.repo.add(producto_id, nombre, pos)
        return {"success": ok, "duplicado": False}

    def eliminar_de_favoritos(self, favorito_id: int) -> bool:
        """Elimina un favorito."""
        return self.repo.remove(favorito_id)

    def cambiar_posicion(self, favorito_id: int, subir: bool = True) -> bool:
        """Sube o baja la posición de un favorito intercambiándola con el vecino."""
        favoritos = self.repo.get_all()
        if not favoritos:
            return False

        # Buscar índice del que queremos mover
        idx = -1
        for i, f in enumerate(favoritos):
            if f['id'] == favorito_id:
                idx = i
                break
        
        if idx == -1:
            return False

        # Calcular destino
        target_idx = idx - 1 if subir else idx + 1
        
        if target_idx < 0 or target_idx >= len(favoritos):
            return False # Ya está al principio o al final

        f1 = favoritos[idx]
        f2 = favoritos[target_idx]

        # Intercambiar posiciones en la BD
        res1 = self.repo.update_posicion(f1['id'], f2['posicion'])
        res2 = self.repo.update_posicion(f2['id'], f1['posicion'])
        
        return res1 and res2

    def actualizar_nombre(self, favorito_id: int, nuevo_nombre: str) -> bool:
        """Actualiza el nombre personalizado."""
        return self.repo.update_nombre(favorito_id, nuevo_nombre)

    def auto_ordenar_por_ventas(self) -> bool:
        """Reorganiza todos los favoritos poniendo los más vendidos primero."""
        query = """
        SELECT f.id, p.ventas_totales
        FROM favoritos f
        JOIN productos p ON f.producto_id = p.id
        ORDER BY p.ventas_totales DESC
        """
        try:
            # Obtener todos ordenados por ventas
            rows = self.db.fetch_all(query)
            if not rows:
                return False
                
            # Crear mapeo de (id_favorito, nueva_posicion)
            mapeo = []
            for i, row in enumerate(rows):
                mapeo.append((row[0], i))
                
            return self.repo.update_posiciones_masivo(mapeo)
        except Exception:
            logger.exception("Error en FavoritosService.auto_ordenar_por_ventas")
            return False
