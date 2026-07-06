from typing import List, Dict, Optional, Tuple
import logging
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.modulos.almacen.menu_repository import MenuRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db

logger = logging.getLogger(__name__)

class MenuService:
    """Servicio de negocio para gestionar los Menús de Oferta (Bundles)."""

    def __init__(self, db):
        self.db = db
        self.prod_repo = ProductoRepository(db)
        self.menu_repo = MenuRepository(db)

    def guardar_menu(self, 
                     nombre: str, 
                     pvp_euros: float, 
                     categoria_id: int, 
                     tipo_id: int, 
                     componentes: List[Dict], 
                     producto_id: Optional[int] = None,
                     sku: str = "",
                     proveedor_id: Optional[int] = None) -> int:
        """Crea o actualiza un producto-menú y sus componentes.
        
        Args:
            nombre: Nombre del menú
            pvp_euros: Precio de venta al público en euros
            categoria_id: ID de la categoría (ej: Menú)
            tipo_id: ID del tipo
            componentes: Lista de dicts {'componente_id': int, 'cantidad': int}
            producto_id: ID del producto si es una edición
            sku: SKU del menú (opcional)
            proveedor_id: ID del proveedor (opcional)
            
        Returns:
            ID del producto guardado.
        """
        try:
            # 1. Guardar el producto base usando ProductoRepository
            # Los menús no tienen stock propio (stock_actual=0)
            pid = self.prod_repo.guardar_producto_completo(
                nombre=nombre,
                nombre_boton=nombre,
                sku=sku,
                categoria_id=categoria_id,
                tipo_id=tipo_id,
                proveedor_id=proveedor_id,
                iva=21, # IVA por defecto para menús
                stock_actual=0,
                stock_min=0,
                activo=1,
                pvp=pvp_euros,
                coste=0.0,
                producto_id=producto_id
            )

            # 2. Guardar la estructura del menú
            if producto_id:
                # Si estamos editando, actualizamos componentes
                self.menu_repo.actualizar_componentes(pid, componentes)
            else:
                # Si es nuevo, creamos la relación
                self.menu_repo.crear_menu(pid, componentes)

            return pid
        except Exception:
            logger.exception("Error guardando menú en MenuService")
            raise

    def listar_menuses(self) -> List[Dict]:
        """Obtiene la lista de menús con sus precios convertidos a euros."""
        try:
            menuses = self.menu_repo.get_menuses()
            for m in menuses:
                # Convertimos el PVP de céntimos a euros
                pvp_cents = m.get('pvp_cents', 0)
                m['pvp'] = float(read_from_db(pvp_cents))
            return menuses
        except Exception:
            logger.exception("Error listando menús")
            return []

    def get_detalle_menu(self, producto_id: int) -> Optional[Dict]:
        """Obtiene toda la información de un menú para la UI."""
        try:
            producto = self.prod_repo.get_by_id(producto_id)
            if not producto:
                return None
            
            # Obtener PVP activo
            pvps = self.prod_repo.get_pvps_by_ids([producto_id])
            pvp = pvps.get(producto_id, 0.0)
            
            # Obtener componentes
            componentes = self.menu_repo.get_componentes(producto_id)
            
            return {
                'id': producto['id'],
                'nombre': producto['nombre'],
                'sku': producto['sku'],
                'categoria_id': producto['categoria'],
                'tipo_id': producto['tipo'],
                'proveedor_id': producto['proveedor_id'],
                'pvp': pvp,
                'componentes': componentes
            }
        except Exception:
            logger.exception("Error obteniendo detalle del menú id=%s", producto_id)
            return None

    def eliminar_menu(self, producto_id: int) -> bool:
        """Elimina la definición del menú (los componentes) y lo desmarca."""
        try:
            return self.menu_repo.eliminar_menu(producto_id)
        except Exception:
            logger.exception("Error eliminando menú id=%s", producto_id)
            return False

    def descontar_componentes_stock(self, producto_id: int, unidades: int, ticket_id: int, cur=None) -> None:
        """Descuenta el stock de los componentes de un menú al venderlo.

        Args:
            producto_id: ID del producto-menú vendido.
            unidades: Unidades vendidas del menú.
            ticket_id: ID del ticket (para registrar el motivo del movimiento).
            cur: Cursor de transacción activa (obligatorio para integridad).
        """
        try:
            componentes = self.menu_repo.get_componentes_para_venta(producto_id, cur=cur)
            for componente_id, cantidad in componentes:
                stock_change = -(cantidad * unidades)
                cur.execute(
                    'UPDATE productos SET stock_actual = COALESCE(stock_actual, 0) + ? WHERE id = ?',
                    (stock_change, componente_id)
                )
                cur.execute(
                    'INSERT INTO stock_movements (producto_id, cantidad, motivo, ticket_line_id) VALUES (?, ?, ?, ?)',
                    (componente_id, stock_change, f'menu:{ticket_id}', None)
                )
        except Exception:
            logger.exception("Error descontando componentes del menú id=%s", producto_id)
            raise

    def validar_stock_menu(self, producto_id: int, cantidad: int = 1) -> Tuple[bool, str]:
        """Verifica si hay stock suficiente de todos los componentes.
        
        Returns:
            (disponible: bool, mensaje: str)
        """
        try:
            componentes = self.menu_repo.get_componentes(producto_id)
            for comp in componentes:
                stock_necesario = comp['cantidad'] * cantidad
                if comp['stock_actual'] < stock_necesario:
                    faltan = stock_necesario - comp['stock_actual']
                    return False, f"Stock insuficiente de '{comp['nombre']}' (Faltan {faltan} uds)"
            return True, "Stock disponible"
        except Exception:
            logger.exception("Error validando stock del menú id=%s", producto_id)
            return False, "Error al validar stock"
