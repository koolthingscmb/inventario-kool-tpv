# kool_tpv

Aplicación de Punto de Venta (TPV) desarrollada en Python para entornos de escritorio.

Resumen

- Propósito: gestionar ventas, devoluciones, clientes, fidelización, pagos e impresión de tickets.
- Lenguaje y dependencias: Python 3.x, CustomTkinter, Pillow; ver `requirements.txt`.

Quickstart

1. Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Inicializar la base de datos (si procede):

```bash
python -m kool_tpv.base_datos.db_init
```

4. Ejecutar la aplicación (desarrollo):

```bash
python main.py
```

Estructura del proyecto

- `main.py` — lanzador principal (raíz del repo).
- `kool_tpv/` — paquete principal con submódulos:
  - `config/` — archivos de configuración (JSON): layouts, colores, fuentes.
  - `assets/` — imágenes y recursos para la UI y tickets.
  - `base_datos/` — wrapper de SQLite, scripts de inicialización y servicios de persistencia.
  - `modulos/` — dominios funcionales: `tpv`, `clientes`, `impresion`, `configuracion`.
  - `utils/` — widgets y utilidades comunes (`TicketCarrito`, `KeyboardManager`, formateadores).
- `scripts/` — herramientas de mantenimiento y migración.
- `tests/` y `test_*.py` — pruebas unitarias/parciales (usar `pytest`).

Flujo de venta (breve)

1. Añadir artículo → `CarritoService`.
2. UI muestra `TicketCarrito` con líneas y totales.
3. Seleccionar forma de pago → `PaymentController*`.
4. Confirmar venta → `TpvController` → `TpvService.save_ticket()` (transacción que persiste ticket, líneas, pagos y actualiza stock).
5. Generar snapshot de `ticket_text` y opción de impresión (texto/ESC-POS).

Notas importantes

- ESC/POS: la integración depende de adaptadores y del entorno; testear en el hardware objetivo.
- Precision monetaria: se utiliza `decimal.Decimal` para cálculos monetarios en código.
- Copias de seguridad: mantener backups regulares de `kool_bd.db` antes de migraciones.

Desarrollo y pruebas

- Ejecutar pruebas unitarias:

```bash
pytest -q
```

- Ejecutar solo los tests de fidelización:

```bash
pytest tests/test_fidelizacion_service.py -q
```

- Para desarrollo de UI: ejecuta `python main.py` y utiliza logging en `logs/` para depuración.

Contribuciones

1. Crea una branch a partir de `main`.
2. Añade tests para cambios funcionales.
3. Envía PR con descripción y tests passing.

Contacto y ayuda

Para preguntas o soporte, abre un issue en el repositorio o contacta al maintainer del proyecto.

FidelizacionRepository

Este módulo centraliza la persistencia relacionada con la fidelización (tesoro) de clientes.

- `actualizar_cliente_loyalty(...)` → actualiza los totales del cliente (tesoro_total, tesoro_historico, tesoro_gastado_total, total_compras, total_compras_euros, total_unidades, fecha_ultima_compra).
- `insertar_movimiento_puntos(...)` → inserta un registro en `points_movements`.
 - `insertar_movimiento_puntos(...)` → inserta un registro en `points_movements` (almacena `puntos` en céntimos).
- `recalcular_nivel_cliente(...)` → actualiza `clientes.id_nivel` según `niveles_fidelidad`.
- `obtener_tesoro_cliente(...)` → devuelve los valores de tesoro convertidos a euros usando `read_from_db`.

Ejemplo de uso:

```python
from kool_tpv.modulos.fidelizacion.fidelizacion_repository import FidelizacionRepository
from kool_tpv.base_datos.db_wrapper import Database
from decimal import Decimal

db = Database(...)
repo = FidelizacionRepository(db)
repo.actualizar_cliente_loyalty(
  cliente_id=1,
  puntos_otorgar=Decimal('1.50'),
  puntos_restar=Decimal('0.00'),
  puntos_gastados=Decimal('0.00'),
  total_ticket=Decimal('15.00'),
  unidades_vendidas=2,
  fecha='2026-05-08'
)
```

