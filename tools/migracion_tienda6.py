import csv
import sys
import os
import logging
from decimal import Decimal
from typing import Dict, Optional

# Añadir el directorio raíz al path para poder importar kool_tpv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.almacen.producto_repository import ProductoRepository
from kool_tpv.base_datos.money_adapter import prepare_for_db

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigradorTienda6:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.db.connect()
        self.repo = ProductoRepository(self.db)
        self._cache_categorias = self._cargar_mapeo("SELECT id, nombre FROM categorias")
        self._cache_tipos = self._cargar_mapeo("SELECT id, nombre FROM tipos")
        self._cache_proveedores = self._cargar_mapeo("SELECT id, nombre FROM proveedores")

    def _cargar_mapeo(self, query: str) -> Dict[str, int]:
        """Carga un mapeo de nombre -> id desde la BD."""
        rows = self.db.fetch_all(query)
        # Normalizamos a mayúsculas y quitamos espacios para comparar mejor
        return {str(row['nombre']).strip().upper(): row['id'] for row in rows}

    def _get_id(self, nombre: str, cache: Dict[str, int], tipo_dato: str) -> Optional[int]:
        """Busca un ID por nombre en el cache normalizado."""
        if not nombre:
            return None
        nombre_norm = nombre.strip().upper()
        res = cache.get(nombre_norm)
        if res is None:
            logger.warning(f"{tipo_dato} '{nombre}' no encontrado en la base de datos.")
        return res

    def migrar(self, csv_path: str):
        if not os.path.exists(csv_path):
            logger.error(f"Archivo no encontrado: {csv_path}")
            return

        exitos = 0
        errores = 0
        
        with open(csv_path, mode='r', encoding='utf-8') as f:
            # Detectar delimitador (coma o punto y coma)
            content = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in content else ','
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row in reader:
                try:
                    ean = row['EAN'].strip()
                    nombre = row['NOMBRE'].strip()
                    sku = row.get('SKU', '').strip() or ean  # Si no hay SKU, usamos EAN
                    
                    # Costes y PVP (Decimal)
                    coste = Decimal(row['COSTE'].replace(',', '.')) if row['COSTE'] else Decimal('0')
                    pvp = Decimal(row['PVP'].replace(',', '.')) if row['PVP'] else Decimal('0')
                    
                    # Stock (Int)
                    stock_str = row.get('UNIDADES (stock_actual)', '0').replace(',', '.')
                    stock = int(float(stock_str)) if stock_str else 0
                    
                    # IVA (Int)
                    iva_str = row.get('TIPO_IVA', '21').replace(',', '.')
                    iva = int(float(iva_str)) if iva_str else 21
                    
                    # Buscar IDs
                    cat_id = self._get_id(row['Categoría'], self._cache_categorias, "Categoría")
                    tipo_id = self._get_id(row['TIPO'], self._cache_tipos, "Tipo")
                    prov_id = self._get_id(row['Proveedor'], self._cache_proveedores, "Proveedor")
                    
                    if not cat_id or not tipo_id:
                        logger.error(f"Fila saltada (falta Cat/Tipo): {nombre} ({ean})")
                        errores += 1
                        continue

                    # Guardar producto completo
                    self.repo.guardar_producto_completo(
                        nombre=nombre,
                        nombre_boton=nombre[:20],
                        sku=sku,
                        categoria_id=cat_id,
                        tipo_id=tipo_id,
                        proveedor_id=prov_id,
                        iva=iva,
                        stock_actual=stock,
                        stock_min=0,
                        activo=1,
                        pvp=pvp,
                        coste=coste,
                        codigos_barras=[ean]
                    )
                    
                    exitos += 1
                    if exitos % 100 == 0:
                        logger.info(f"Progreso: {exitos} productos migrados...")
                        
                except Exception as e:
                    logger.error(f"Error procesando fila {row.get('EAN', 'S/N')}: {e}")
                    errores += 1

        logger.info("-" * 30)
        logger.info(f"MIGRACIÓN FINALIZADA")
        logger.info(f"Éxitos: {exitos}")
        logger.info(f"Errores: {errores}")
        logger.info("-" * 30)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python migracion_tienda6.py <ruta_al_csv>")
        sys.exit(1)
        
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../kool_tpv/base_datos/kool_bd.db'))
    csv_path = sys.argv[1]
    
    migrador = MigradorTienda6(db_path)
    migrador.migrar(csv_path)
