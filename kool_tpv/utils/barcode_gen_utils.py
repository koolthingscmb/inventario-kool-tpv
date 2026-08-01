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

def calculate_ean13_checksum(code12: str) -> str:
    """Calcula el dígito de control para un código EAN-13 de 12 dígitos."""
    if len(code12) != 12 or not code12.isdigit():
        raise ValueError("El código base debe tener 12 dígitos numéricos")
    
    # Pesos: 1 para posiciones impares, 3 para pares
    suma = 0
    for i, digit in enumerate(code12):
        weight = 3 if i % 2 != 0 else 1
        suma += int(digit) * weight
    
    check_digit = (10 - (suma % 10)) % 10
    return str(check_digit)

def generate_internal_number(db=None, prefix: str = "99") -> str:
    """Genera un número EAN-13 válido (13 dígitos) para uso interno.
    Formato: prefix + timestamp (YYMMDD) + 4 dígitos aleatorios + dígito control.
    """
    if len(prefix) != 2:
        prefix = "99"
    
    while True:
        now = datetime.datetime.now()
        timestamp = now.strftime("%y%m%d") # 6 dígitos
        random_part = "".join([str(random.randint(0, 9)) for _ in range(4)]) # 4 dígitos
        
        code12 = f"{prefix}{timestamp}{random_part}"
        checksum = calculate_ean13_checksum(code12)
        final_code = f"{code12}{checksum}"
        
        # Si tenemos DB, verificar que no existe ya en la tabla codigos_barras
        if db:
            try:
                res = db.fetch_one("SELECT 1 FROM codigos_barras WHERE ean = ?", (final_code,))
                if not res:
                    return final_code
                else:
                    logger.warning(f"Código interno {final_code} colisionó, reintentando...")
            except Exception:
                logger.exception("Error verificando unicidad de código de barras")
                return final_code # Fallback si falla la consulta
        else:
            return final_code

def generate_barcode_image(code: str, sku: str, nombre: str = "") -> Optional[str]:
    """Generar imagen del código de barras usando python-barcode."""
    ensure_barcodes_dir()
    
    # Prioridad para el nombre del archivo: Nombre del producto, si no SKU
    base_name = nombre if nombre else sku
    # Limpiar caracteres no permitidos en nombres de archivo (Windows/Mac/Linux)
    safe_filename = "".join([c if c.isalnum() or c in (' ', '-', '_') else '_' for c in base_name]).strip()
    # Reemplazar espacios por guiones para que sea más limpio
    safe_filename = safe_filename.replace(' ', '-')
    
    if not safe_filename:
        safe_filename = f"barcode_{code}"
        
    output_base = os.path.join(BARCODES_DIR, safe_filename)
    
    try:
        # Usar EAN13 en lugar de Code128
        EAN13 = barcode.get_barcode_class('ean13')
        # ImageWriter usa Pillow internamente para generar PNG/JPG
        writer = ImageWriter()
        # Ajustar opciones para mejor legibilidad
        options = {
            'module_height': 15.0,
            'module_width': 0.3, # Un poco más ancho para EAN13
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 6.0 # EAN13 necesita más zona de silencio
        }
        
        # Si se proporciona un nombre, lo usamos como texto en lugar del código numérico
        if nombre:
            options['text'] = nombre.upper()
        
        # El código debe tener 13 dígitos
        my_barcode = EAN13(code, writer=writer)
        # save() añade la extensión automáticamente si no se indica en el path
        full_path = my_barcode.save(output_base, options=options)
        
        logger.info(f"Código de barras EAN-13 generado: {full_path} (Code: {code})")
        return full_path
    except Exception:
        logger.exception(f"Error generando imagen de código de barras EAN-13 para SKU {sku}")
        return None

def get_barcode_path(sku: str) -> str:
    """Devuelve la ruta esperada para el código de barras de un SKU."""
    safe_sku = "".join([c for c in sku if c.isalnum() or c in ('-', '_')]).strip()
    return os.path.join(BARCODES_DIR, f"{safe_sku}.png")
