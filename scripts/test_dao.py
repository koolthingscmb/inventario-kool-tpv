import os
import sys
# ensure project root is on sys.path when running this script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modulos.almacen.articulos.dao_articulos import get_products_page
from database import DB_PATH

DB = DB_PATH

if __name__ == '__main__':
    print('DB:', DB)
    try:
        page = 1
        page_size = 10
        items = get_products_page(DB, page=page, page_size=page_size+1)
        has_next = len(items) > page_size
        if has_next:
            items = items[:page_size]
        print(f'Página {page}, filas devueltas: {len(items)}, hay siguiente: {has_next}')
        for it in items:
            print(it)
    except Exception as e:
        print('Error ejecutando DAO:', e)
