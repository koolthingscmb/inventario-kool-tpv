import pytest
from unittest.mock import MagicMock
from decimal import Decimal

from kool_tpv.modulos.ticket.ticket_processor import VentaProcessor, VentaFidelizacionProcessor


@pytest.fixture
def mock_db_and_repo(monkeypatch):
    mock_db = MagicMock()
    # Create processor but replace internal repo and fidel_repo with mocks
    processor = VentaProcessor(mock_db)
    processor.repo = MagicMock()
    processor.fidel_repo = MagicMock()
    processor.fidel_service = MagicMock()
    return processor


def test_venta_processor_orchestrates_repo_calls(mock_db_and_repo):
    processor = mock_db_and_repo
    carrito_items = [
        {'id': 10, 'sku': 'S1', 'nombre': 'P1', 'cantidad': 2, 'precio_cents': 500, 'iva': 21, 'line_tipo': 'venta'},
    ]
    processor.repo.insert_ticket.return_value = 123
    processor.process(carrito_items=carrito_items, resumen={}, created_at='2026-05-08 12:00:00', num_ticket=1, cajero='u', cliente='C', cliente_id=1, subtotal_cents=1000, total_cents=1200, pagado_cents=1200, cambio_cents=0, pagos=[('efectivo', 1200)])

    # insert_ticket called
    assert processor.repo.insert_ticket.called
    # insert_ticket_line called for each item
    assert processor.repo.insert_ticket_line.called
    # payments inserted
    assert processor.repo.insert_payment.called
    # audit log inserted
    assert processor.repo.insert_audit_log.called


def test_venta_fidelizacion_processor_updates_fidelity(mock_db_and_repo):
    processor = VentaFidelizacionProcessor(mock_db_and_repo.db)
    # replace repos with mocks
    processor.repo = MagicMock()
    processor.fidel_repo = MagicMock()
    processor.fidel_service = MagicMock()
    processor.repo.insert_ticket.return_value = 200
    processor.process(carrito_items=[], resumen={}, created_at='2026-05-08', num_ticket=2, cajero='u', cliente='C', cliente_id=5, subtotal_cents=0, total_cents=0, pagado_cents=0, cambio_cents=0, puntos_otorgar_cents=150, puntos_gastados_cents=0, puntos_restar_cents=0, total_unidades=1)

    # points movement and actualizar_cliente_loyalty should be called
    assert processor.repo.insert_points_movement_raw.called
    assert processor.fidel_repo.actualizar_cliente_loyalty.called
