"""Servicio para gestión de variantes de tipos de producto.

Contiene la clase `ProduccionTiposVariantesService` que expone métodos para gestionar
variantes con lógica de negocio, utilizando el repository para acceso a datos.
"""
from typing import List, Optional

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.models.produccion_tipo_variante_model import ProduccionTipoVariante
from kool_tpv.modulos.produccion.repositories.produccion_tipos_variantes_repository import ProduccionTiposVariantesRepository


class ProduccionTiposVariantesService:
    """Servicio de lógica de negocio para variantes de tipos de producto.

    Args:
        db: instancia de `Database` ya conectada.
    """

    def __init__(self, db: Database):
        self.db = db
        self.repository = ProduccionTiposVariantesRepository(db)

    def obtener_todos(self) -> List[ProduccionTipoVariante]:
        """Obtener todas las variantes."""
        return self.repository.get_todos()

    def obtener_por_tipo(self, tipo_id: int, solo_activos: bool = True) -> List[ProduccionTipoVariante]:
        """Obtener variantes de un tipo específico."""
        return self.repository.get_por_tipo(tipo_id, solo_activos)

    def obtener_por_id(self, variante_id: int) -> Optional[ProduccionTipoVariante]:
        """Obtener una variante por su ID."""
        return self.repository.get_por_id(variante_id)

    def crear(self, tipo_id: int, nombre: str, coste_base: int = 0,
              precio_recomendado: int = 0, shopify_variant_id: Optional[str] = None,
              requiere_talla: int = 0, requiere_color: int = 0,
              grupo_talla_id: Optional[int] = None) -> Optional[int]:
        """Crear una nueva variante.

        Args:
            tipo_id: ID del tipo al que pertenece.
            nombre: Nombre de la variante (ej: "A4").
            coste_base: Coste de fabricación.
            precio_recomendado: Precio de venta sugerido.
            shopify_variant_id: ID externo opcional.
            requiere_talla: 1 si requiere talla.
            requiere_color: 1 si requiere color.
            grupo_talla_id: ID del grupo de tallas opcional.

        Returns:
            ID de la variante creada o None si error.
        """
        if not tipo_id or not nombre or not nombre.strip():
            return None

        variante = ProduccionTipoVariante(
            tipo_id=tipo_id,
            nombre=nombre.strip(),
            coste_base=coste_base,
            precio_recomendado=precio_recomendado,
            activo=1,
            shopify_variant_id=shopify_variant_id,
            requiere_talla=requiere_talla,
            requiere_color=requiere_color,
            grupo_talla_id=grupo_talla_id
        )
        return self.repository.crear(variante)

    def actualizar(self, variante_id: int, tipo_id: int, nombre: str,
                   coste_base: int = 0, precio_recomendado: int = 0,
                   activo: int = 1, shopify_variant_id: Optional[str] = None,
                   requiere_talla: int = 0, requiere_color: int = 0,
                   grupo_talla_id: Optional[int] = None) -> bool:
        """Actualizar una variante existente."""
        if not variante_id or not tipo_id or not nombre or not nombre.strip():
            return False

        variante = ProduccionTipoVariante(
            id=variante_id,
            tipo_id=tipo_id,
            nombre=nombre.strip(),
            coste_base=coste_base,
            precio_recomendado=precio_recomendado,
            activo=activo,
            shopify_variant_id=shopify_variant_id,
            requiere_talla=requiere_talla,
            requiere_color=requiere_color,
            grupo_talla_id=grupo_talla_id
        )
        return self.repository.actualizar(variante)

    def eliminar(self, variante_id: int) -> bool:
        """Eliminar una variante (soft delete)."""
        return self.repository.eliminar(variante_id)

    def listar_variantes_con_coste(self, search_term: str = "") -> List[dict]:
        """Obtener variantes con coste para la UI a través del repositorio."""
        return self.repository.get_variantes_con_coste(search_term)

    def obtener_activos_como_dict(self) -> dict:
        """Obtener variantes activas como dict {id: "Tipo / Variante"} para UI."""
        variantes = self.repository.get_todos()
        resultado = {}
        for v in variantes:
            if v.activo != 1:
                continue
            tipo_row = self.db.fetch_one("SELECT nombre FROM tipos WHERE id = ?", (v.tipo_id,))
            tipo_nombre = tipo_row[0] if tipo_row else "???"
            clave = f"{tipo_nombre} / {v.nombre}"
            resultado[v.id] = clave
        return resultado
