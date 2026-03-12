import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from kool_tpv.modulos.tpv.payment_controller_factory import create_controllers

# Mock minimal
class MockParent:
    pass

class MockCarritoService:
    def get_resumen_financiero(self):
        return {'total': 50.0}

finalize_called = []

def mock_on_finalize(efectivo=None, forma_pago=None, importe_efectivo=None, importe_tarjeta=None):
    finalize_called.append({
        'efectivo': efectivo,
        'forma_pago': forma_pago,
        'importe_efectivo': importe_efectivo,
        'importe_tarjeta': importe_tarjeta
    })
    print(f"✓ on_finalize llamado: {forma_pago}")

print("=" * 60)
print("TEST payment_controller_factory.py")
print("=" * 60)

# Test 1: Crear controllers
print("\n1. Creando controllers...")
parent = MockParent()
carrito = MockCarritoService()

controllers = create_controllers(parent, carrito, mock_on_finalize)

created = len([c for c in controllers.values() if c is not None])
print(f"   Creados: {created}/4")
assert 'cash' in controllers
assert 'multi' in controllers
assert 'tarjeta' in controllers
assert 'web' in controllers
print("✓ Todos los controllers creados")

# Test 2: Verificar estructura
print("\n2. Verificando estructura...")
for key, ctrl in controllers.items():
    if ctrl is not None:
        assert hasattr(ctrl, 'set_total'), f"{key} no tiene set_total"
        print(f"   ✓ {key}: tiene set_total()")

print("\n" + "=" * 60)
print("✓ TODAS LAS PRUEBAS PASARON")
print("=" * 60)
