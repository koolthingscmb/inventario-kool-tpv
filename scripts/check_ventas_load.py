import sys, os, pprint
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kool_tpv.modulos.almacen.ui.Productos.crear_producto_ui import CrearProductoUI
from kool_tpv.modulos.almacen.ui.Productos.cargar_producto import CargarProductoUI
from kool_tpv.base_datos.db_wrapper import Database

import tkinter as tk

# create root
root = tk.Tk()
root.withdraw()

# connect db
db = Database('kool_tpv/base_datos/kool_bd.db')
db.connect()

ui = CrearProductoUI(root, db=db)
loader = CargarProductoUI(root, db=db)
res = loader.apply_to_ui(1, ui)
print('apply_to_ui returned', res)
# try to read e_ventas widget
try:
    val = ui.e_ventas.get()
    print('e_ventas.get():', repr(val))
except Exception as e:
    print('e_ventas.get() error', e)

# also check widget state
try:
    st = ui.e_ventas.cget('state')
    print('e_ventas.state:', st)
except Exception:
    print('e_ventas has no cget(state)')

# inspect delete/insert availability
print('has delete', hasattr(ui.e_ventas, 'delete'), 'has insert', hasattr(ui.e_ventas, 'insert'))

# destroy
root.destroy()
