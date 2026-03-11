import sys
from pathlib import Path
import time
# ensure project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tkinter as tk
print('Starting interactive-like flow test (non-GUI interactions)')

from main import App

app = App()
# avoid mainloop; operate programmatically

# Open almacen module
app.open_almacen()
alm = getattr(app, 'almacen_view', None)
print('Almacen view created:', bool(alm))

# Instantiate EntradaManualUI directly and set as central content
from kool_tpv.modulos.almacen.ui.albaranes.entrada_manual import EntradaManualUI
entrada_ui = EntradaManualUI(alm.central_area, db=app.db)
# set as central content (this will also update breadcrumb)
alm.set_central_content(entrada_ui)
print('EntradaManualUI set as central content')

# Add one line to entrada_ui
try:
    entrada_ui.lines.append({'producto_id': None, 'ean': '000000', 'nombre': 'TEST PROD', 'cantidad': 1, 'coste': 1.0, 'descuento': 0.0, 'tipo_iva': 21})
    entrada_ui._render_lines()
    entrada_ui._update_totals()
    print('Added one line to EntradaManualUI, lines count:', len(entrada_ui.lines))
except Exception as e:
    print('Error adding line:', e)

# Simulate clicking breadcrumb ALBARANES by invoking callback
cb_map = getattr(alm, 'breadcrumb_callbacks', {})
print('breadcrumb_callbacks keys:', list(cb_map.keys()))
if 'ALBARANES' in cb_map:
    try:
        print('Invoking breadcrumb callback ALBARANES')
        cb_map['ALBARANES']()
    except Exception as e:
        print('Callback raised:', e)
else:
    print('No ALBARANES callback found')

# Inspect central_area children
children = alm.central_area.winfo_children()
print('central_area children after invoking callback:', [(type(c).__name__, c.winfo_manager()) for c in children])

# Destroy app
try:
    app.destroy()
except Exception:
    pass
print('Done')
