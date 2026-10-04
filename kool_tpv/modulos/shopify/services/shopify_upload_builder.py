"""Preparación de los datos de subida a Shopify (lógica de negocio fuera de la interfaz).

De momento contiene la generación del color "Sorpresa" de las camisetas, que antes estaba
duplicada en la creación y en la edición de la pantalla SUBIDA.

Las variantes Sorpresa se envían SIN control de inventario (tracked = False): siempre se
pueden comprar, no hay número de stock que mantener.
"""
import logging
from typing import Any, Dict, Iterable, List, Optional

from kool_tpv.base_datos.money_adapter import prepare_for_db, read_from_db
from .producto_content_service import slugify_diseno
from .shopify_config_service import ShopifyConfigService

logger = logging.getLogger(__name__)


class ShopifyUploadBuilder:
    """Construye las variantes y datos auxiliares que consume ShopifyProductService.product_set."""

    COLOR_SORPRESA = "Sorpresa"
    TIPO_CON_SORPRESA = "camiseta"

    def __init__(self, db):
        self.config_service = ShopifyConfigService(db)

    # ------------------------------------------------------------------
    # Reglas
    # ------------------------------------------------------------------

    @classmethod
    def aplica_sorpresa(cls, tipo_nombre: str) -> bool:
        """Solo las camisetas llevan color Sorpresa."""
        return (tipo_nombre or "").strip().lower() == cls.TIPO_CON_SORPRESA

    @classmethod
    def es_color_sorpresa(cls, color: Optional[str]) -> bool:
        return (color or "").strip().upper() == cls.COLOR_SORPRESA.upper()

    @classmethod
    def sorpresas_existentes(cls, producto: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Variantes Sorpresa que ya tiene el producto en Shopify, indexadas por talla."""
        resultado: Dict[str, Dict[str, Any]] = {}
        for var in (producto.get("variants") or {}).get("nodes") or []:
            talla, color = "", ""
            for opt in var.get("selectedOptions") or []:
                nombre = (opt.get("name") or "").upper()
                if nombre == "TALLA":
                    talla = opt.get("value") or ""
                elif nombre == "COLOR":
                    color = opt.get("value") or ""
            if cls.es_color_sorpresa(color):
                resultado[talla] = var
        return resultado

    # ------------------------------------------------------------------
    # Variantes Sorpresa
    # ------------------------------------------------------------------

    def variantes_sorpresa(self, tipo_nombre: str, variante_nombre: str, tallas: Iterable[str],
                           existentes: Optional[Dict[str, Dict[str, Any]]] = None,
                           marcar_variante_tpv: bool = False) -> List[Dict[str, Any]]:
        """Una variante Sorpresa por talla, sin control de inventario.

        existentes: Sorpresa que ya hay en Shopify por talla (modo editar). Se conserva su SKU y,
                    si no hay precio configurado, su precio.
        marcar_variante_tpv: añade 'tpv_variante_nombre' (productos con variantes agrupadas).
        """
        tipo_code = slugify_diseno(tipo_nombre).upper()[:4] or "PROD"
        variante_slug = slugify_diseno(variante_nombre).upper()
        precio_cfg = self._precio_config()
        existentes = existentes or {}

        resultado = []
        for talla in sorted({t for t in tallas if t}):
            previa = existentes.get(talla) or {}
            var = {
                "sku": previa.get("sku") or f"{tipo_code}-SORPRESA-{variante_slug}-{talla}",
                "color": self.COLOR_SORPRESA,
                "talla": talla,
                "cantidad": 0,
                "tracked": False,
                "requiere_color": 1,
                "requiere_talla": 1,
            }
            if precio_cfg is not None:
                var["precio"] = precio_cfg
                # El precio de Sorpresa es un precio de venta final: no sumarle el recargo
                var["precio_ya_final"] = True
            elif previa.get("price"):
                var["precio"] = str(previa["price"])
                # El precio ya viene de Shopify: no sumarle el recargo otra vez
                var["precio_ya_final"] = True
            if marcar_variante_tpv:
                var["tpv_variante_nombre"] = variante_nombre
            resultado.append(var)
        return resultado

    def _precio_config(self) -> Optional[float]:
        """Precio de Sorpresa configurado en CONFIG > TIPOS (None si no hay o no es válido)."""
        raw = self.config_service.get_config().get("precio_sorpresa")
        if not raw or str(raw).strip().lower() == "none":
            return None
        try:
            limpio = str(raw).replace("€", "").replace(",", ".").strip()
            return float(read_from_db(prepare_for_db(limpio)))
        except (ArithmeticError, ValueError):
            logger.warning(f"Precio de Sorpresa no válido en la configuración: {raw!r}")
            return None
