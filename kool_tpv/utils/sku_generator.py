import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_sku(db, categoria_nombre: str, tipo_nombre: str, producto_nombre: str) -> str:
    """
    Genera un SKU único basado en categoría, tipo y nombre.
    
    Formato: XXYY-NOMBRE-SUF
    - XX: 2 primeras letras de categoría
    - YY: 2 primeras letras de tipo
    - NOMBRE: primeras 10 letras del nombre (alfanumérico)
    - SUF: sufijo numérico secuencial (-001, -002, ...)
    """
    
    # 1. Normalizar y obtener prefijos (2 letras alfanuméricas)
    def clean_prefix(text: str, default: str) -> str:
        if not text:
            return default
        clean = re.sub(r'[^A-Z0-9]', '', text.upper())
        return clean[:2] if len(clean) >= 2 else (clean + default)[:2]

    cat_prefix = clean_prefix(categoria_nombre, 'XX')
    tipo_prefix = clean_prefix(tipo_nombre, 'YY')
    
    # 2. Normalizar nombre (10 letras alfanuméricas)
    nombre_clean = re.sub(r'[^A-Z0-9]', '', producto_nombre.upper())[:10]
    if not nombre_clean:
        nombre_clean = "PROD"
        
    # 3. Base del SKU
    sku_base = f"{cat_prefix}{tipo_prefix}-{nombre_clean}"
    
    # 4. Buscar sufijo único consultando la BD
    counter = 1
    while True:
        sku_candidato = f"{sku_base}-{counter:03d}"
        
        # Verificar si existe en la BD
        try:
            # Usamos una query directa para evitar dependencias circulares con repositorios si fuera necesario
            res = db.fetch_one("SELECT id FROM productos WHERE sku = ?", (sku_candidato,))
            if not res:
                return sku_candidato
        except Exception as e:
            logger.error(f"Error verificando SKU en BD: {e}")
            # Si hay error de BD, devolvemos el candidato pero logueamos el fallo
            return sku_candidato
            
        counter += 1
        if counter > 999:
            # Fallback de seguridad si hay demasiados (poco probable)
            import uuid
            return f"{sku_base}-{uuid.uuid4().hex[:4].upper()}"
