import logging
import sys
import os
import tkinter as tk
import customtkinter as ctk

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kool_tpv.modulos.almacen.almacen_view import AlmacenView
from kool_tpv.base_datos.db_wrapper import Database

logging.basicConfig(level=logging.DEBUG)

root = tk.Tk()
root.geometry('800x600')

# Use existing DB path from project
db_path = 'kool_tpv/base_datos/kool_bd.db'
db = Database(db_path)
try:
    db.connect()
except Exception as e:
    logging.exception('No pude conectar DB para la prueba')

view = AlmacenView(root, db=db)
view.pack = lambda *a, **k: None
# mount on root
view.sidebar.pack(side='left', fill='y')
view.main_frame.pack(side='right', fill='both', expand=True)

# Simulate opening crear with an example product id (try 1)
try:
    view.show_crear(producto_id=1)
    logging.info('Invocada show_crear con producto_id=1')
except Exception:
    logging.exception('Error llamando show_crear')

# run mainloop briefly and exit
root.after(2000, root.destroy)
root.mainloop()

print('Test finished')
