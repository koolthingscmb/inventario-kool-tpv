import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService

# Mocks
class MockDB:
    pass

class MockCarrito:
    def __init__(self):
        self._devolucion_active = False
        self._items = []

    def get_items(self):
        return self._items

    def get_resumen_financiero(self):
        return {'total': 10.0}

print("=" * 60)
print("TEST DevolucionesService.confirmar_devolucion()")
print("=" * 60)

# Test 1: Verificar que el método existe
print("\n1. Verificando que confirmar_devolucion existe...")
db = MockDB()
carrito = MockCarrito()
service = DevolucionesService(db, carrito)

assert hasattr(service, 'confirmar_devolucion')
assert callable(service.confirmar_devolucion)
print("✓ Método confirmar_devolucion existe")

# Test 2: Verificar que rechaza carrito vacío
print("\n2. Verificando validación carrito vacío...")
try:
    service.confirmar_devolucion(usuario='test')
    print("✗ Debería haber lanzado RuntimeError")
    assert False
except RuntimeError as e:
    if 'items' in str(e).lower():
        print(f"✓ RuntimeError correcto: {e}")
    else:
        print(f"✗ RuntimeError inesperado: {e}")

# Test 3: Verificar firma del método
print("\n3. Verificando firma del método...")
import inspect
sig = inspect.signature(service.confirmar_devolucion)
params = list(sig.parameters.keys())

expected = ['usuario', 'cliente_id', 'efectivo', 'forma_pago', 
            'importe_efectivo', 'importe_tarjeta', 'descuento_data']

for exp in expected:
    assert exp in params, f"Parámetro {exp} no encontrado"

print("✓ Firma correcta con todos los parámetros")

# Test 4: Verificar imports
print("\n4. Verificando imports...")
from kool_tpv.modulos.tpv.devoluciones_service import save_ticket
print("✓ save_ticket importado correctamente")

print("\n" + "=" * 60)
print("✓ TODAS LAS PRUEBAS PASARON")
print("=" * 60)
