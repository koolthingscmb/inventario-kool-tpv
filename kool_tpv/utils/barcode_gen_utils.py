"""barcode_gen_utils.py - Utilidades para generación de códigos de barras internos.

Usa python-barcode para generar imágenes de códigos de barras.
"""
import os
import logging
import datetime
import random
from typing import Optional
import barcode
from barcode.writer import ImageWriter

logger = logging.getLogger(__name__)

# Directorio base para los assets de códigos de barras
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARCODES_DIR = os.path.join(BASE_DIR, 'assets', 'barcodes')

def ensure_barcodes_dir():
    """Asegura que el directorio de códigos de barras existe."""
    if not os.path.exists(BARCODES_DIR):
        try:
            os.makedirs(BARCODES_DIR, exist_ok=True)
            logger.info(f"Directorio creado: {BARCODES_DIR}")
        except Exception:
            logger.exception(f"No se pudo crear el directorio: {BARCODES_DIR}")

def generate_internal_number() -> str:
    """Genera un número único de 13 dígitos para uso interno.
    Formato: 99 + timestamp (YYMMDD) + 5 dígitos aleatorios.
    """
    prefix = "99"
    now = datetime.datetime.now()
    timestamp = now.strftime("%y%m%d") # 6 dígitos
    random_part = "".join([str(random.randint(0, 9)) for _ in range(5)]) # 5 dígitos
    return f"{prefix}{timestamp}{random_part}"

def generate_barcode_image(code: str, sku: str) -> Optional[str]:
    """Generar imagen del código de barras usando python-barcode."""
    ensure_barcodes_dir()
    
    safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-', '_')]).strip()
    if not safe_sku:
        safe_sku = f"barcode_{code}"
        
    output_base = os.path.join(BARCODES_DIR, safe_sku)
    
    try:
        # Usar Code128
        CODE128 = barcode.get_barcode_class('code128')
        # ImageWriter usa Pillow internamente para generar PNG/JPG
        writer = ImageWriter()
        # Ajustar opciones para mejor legibilidad
        options = {
            'module_height': 15.0,
            'module_width': 0.2,
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 2.0
        }
        
        my_barcode = CODE128(code, writer=writer)
        # save() añade la extensión automáticamente si no se indica en el path
        full_path = my_barcode.save(output_base, options=options)
        
        logger.info(f"Código de barras generado: {full_path} (Code: {code})")
        return full_path
    except Exception:
        logger.exception(f"Error generando imagen de código de barras para SKU {sku}")
        return None

def get_barcode_path(sku: str) -> str:
    """Devuelve la ruta esperada para el código de barras de un SKU."""
    safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-', '_')]).strip()
    return os.path.join(BARCODES_DIR, f"{safe_sku}.png")
