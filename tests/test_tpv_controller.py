import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from kool_tpv.modulos.tpv.tpv_controller import TpvController

# Mock view minimal
class MockView:
    def __init__(self):
        self.carrito_service = None
        self.ticket_carrito = None
        self.cajero_nombre = 'Test'
        self.container = None
        self.grid_buttons = []

print("=" * 60)
print("TEST TpvController")
print("=" * 60)

# Test 1: Instanciar controller
print("\n1. Instanciando controller...")
view = MockView()
controller = TpvController(view, db=None)

assert hasattr(controller, 'setup_services')
assert hasattr(controller, 'setup_actions')
assert hasattr(controller, 'setup_payment_controllers')
assert hasattr(controller, 'rebind_buttons')
assert hasattr(controller, 'finalize_sale')
print("✓ TpvController instanciado con todos los métodos")

# Test 2: Verificar servicios intentados
print("\n2. Verificando servicios...")
# Todos serán None porque no hay DB real, pero atributos deben existir
assert hasattr(controller, 'fidelizacion_service')
assert hasattr(controller, 'impresora_service')
assert hasattr(controller, 'tpv_service')
print("✓ Atributos de servicios presentes")

# Test 3: Verificar acciones intentadas
print("\n3. Verificando acciones...")
assert hasattr(controller, '_cliente_action')
assert hasattr(controller, '_cajero_action')
assert hasattr(controller, 'descuento_action')
assert hasattr(controller, '_devolucion_action')
assert hasattr(controller, '_stock_ui')
assert hasattr(controller, '_cierre_ui')
assert hasattr(controller, '_tickets_ui')
print("✓ Atributos de acciones presentes")

# Test 4: Verificar payment_controllers
print("\n4. Verificando payment_controllers...")
assert hasattr(controller, 'payment_controllers')
assert isinstance(controller.payment_controllers, dict)
print(f"✓ payment_controllers es dict con {len(controller.payment_controllers)} items")

# Test 5: Verificar finalize_sale callable
print("\n5. Verificando finalize_sale...")
import inspect
sig = inspect.signature(controller.finalize_sale)
params = list(sig.parameters.keys())

expected = ['efectivo', 'forma_pago', 'importe_efectivo', 'importe_tarjeta']
for exp in expected:
    assert exp in params, f"Parámetro {exp} no encontrado"

print("✓ finalize_sale con firma correcta")

print("\n" + "=" * 60)
print("✓ TODAS LAS PRUEBAS PASARON")
print("=" * 60)
