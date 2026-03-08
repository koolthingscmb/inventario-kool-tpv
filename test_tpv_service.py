import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from kool_tpv.modulos.tpv.tpv_service import TpvService

print("=" * 60)
print("TEST TpvService")
print("=" * 60)

# Test 1: Instanciar servicio
print("\n1. Instanciando servicio...")
service = TpvService(db=None)
assert hasattr(service, 'finalize_sale_ticket')
assert callable(service.finalize_sale_ticket)
print("✓ TpvService instanciado correctamente")

# Test 2: Validar carrito vacío
print("\n2. Validando rechazo de carrito vacío...")
result = service.finalize_sale_ticket({'carrito_items': []})

assert result['success'] == False
assert 'vacío' in result['error'].lower()
print(f"✓ Rechazo correcto: {result['error']}")

# Test 3: Verificar estructura de retorno
print("\n3. Verificando estructura de retorno...")
# Con items pero sin DB (esperamos error de BD)
ticket_data = {
    'carrito_items': [{'id': 1, 'cantidad': 1}],
    'resumen': {'total': 10.0},
    'efectivo': Decimal('10'),
    'cajero': 'Test',
    'cliente': None,
    'forma_pago': 'Efectivo',
    'importe_efectivo': Decimal('10'),
    'importe_tarjeta': Decimal('0'),
    'descuento_data': None,
    'carrito_service': None
}

result = service.finalize_sale_ticket(ticket_data)

assert 'success' in result
assert isinstance(result['success'], bool)

if not result['success']:
    assert 'error' in result
    print(f"✓ Error esperado (sin DB): {result['error'][:50]}...")
else:
    assert 'ticket_id' in result
    assert 'num_ticket' in result
    print("✓ Estructura correcta con éxito")

# Test 4: Verificar método _print_ticket existe
print("\n4. Verificando método _print_ticket...")
assert hasattr(service, '_print_ticket')
assert callable(service._print_ticket)
print("✓ Método _print_ticket existe")

print("\n" + "=" * 60)
print("✓ TODAS LAS PRUEBAS PASARON")
print("=" * 60)
