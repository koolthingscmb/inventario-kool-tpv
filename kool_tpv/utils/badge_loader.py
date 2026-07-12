"""Helper para cargar badges de niveles de fidelidad como imágenes de CustomTkinter."""
import logging
import customtkinter as ctk
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

def get_badges_path() -> Path:
    """Obtener la ruta a la carpeta de badges de forma robusta."""
    this_path = Path(__file__).resolve()
    # Buscar la carpeta root del paquete `kool_tpv`
    for p in this_path.parents:
        if (p / '__init__.py').exists() and p.name == 'kool_tpv':
            return p / 'assets' / 'badges'
    
    # Fallback si no se encuentra (entorno de desarrollo/test)
    return this_path.parents[1] / 'assets' / 'badges'

def load_badge_image(filename: str, size: tuple = (64, 64)) -> ctk.CTkImage:
    """Cargar un badge desde assets/badges/ como CTkImage.
    
    Args:
        filename: Nombre del archivo (ej: 'badge_level_1.png')
        size: Tupla (ancho, alto) para el reescalado
        
    Returns:
        ctk.CTkImage o None si no se encuentra o hay error
    """
    if not filename or not isinstance(filename, str):
        return None
        
    try:
        badges_dir = get_badges_path()
        img_path = badges_dir / filename
        
        if not img_path.exists():
            # logger.warning(f"Badge NO encontrado: {img_path}")
            return None
            
        img = Image.open(img_path).convert('RGBA')
        
        # Crear un fondo blanco del mismo tamaño
        fondo_blanco = Image.new('RGBA', img.size, (255, 255, 255, 255))
        # Componer la imagen sobre el fondo blanco
        img_final = Image.alpha_composite(fondo_blanco, img)
        
        ctk_img = ctk.CTkImage(img_final, size=size)
        return ctk_img
        
    except Exception:
        logger.exception(f"Error cargando badge: {filename}")
        return None
