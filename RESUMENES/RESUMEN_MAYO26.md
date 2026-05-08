# Resumen técnico del proyecto TPV — Mayo 2026

Fecha: 2026-05-08

Este documento sintetiza el estado actual del proyecto `kool_tpv` ubicado en este workspace.

Resumen rápido

- Propósito: Aplicación de Punto de Venta (TPV) de escritorio en Python para gestionar ventas, devoluciones, clientes, fidelización, pagos (efectivo, tarjeta, web, mixto) e impresión de tickets.
- Punto(s) de entrada: `main.py` en la raíz (lanzador de despliegue) y los módulos bajo `kool_tpv/` para desarrollo y pruebas.
- Stack: Python 3.x, CustomTkinter para UI, Pillow para imágenes, SQLite para persistencia; dependencias listadas en `requirements.txt`.

Estructura principal del proyecto

- `kool_tpv/` — paquete principal
  - `config/` — JSON y assets de configuración (layouts, colores, fuentes, botones)
  - `assets/` — imágenes y recursos visuales
  - `base_datos/` — wrapper y servicios de BD (SQLite), scripts de inicialización y migración
  - `modulos/` — funcionalidades por dominio: `tpv`, `clientes`, `impresion`, etc.
  - `utils/` — widgets reutilizables, loaders, formateadores y helpers (ej. `TicketCarrito`, `KeyboardManager`)
- `scripts/` — utilidades y migraciones
- `tests/` y archivos `test_*.py` en raíz — pruebas unitarias/parciales (usar `pytest`)
- `logs/`, `reports/`, `RESUMENES/` — logs, informes y documentación del proyecto

Flujo de venta (simplificado)

1. El usuario añade artículos desde el buscador o botones → `CarritoService`.
2. UI: `TicketCarrito` muestra líneas y totales calculados por `CarritoService`.
3. Selección forma de pago → `PaymentController*` gestiona validaciones y recaba montos.
4. Confirmación dispara `TpvController` → `TpvService.finalize_sale_ticket()`.
5. `save_ticket()` persiste ticket, líneas, pagos, movimientos de stock y auditoría en una transacción.
6. Se genera snapshot de `ticket_text` y se intenta impresión (texto/ESC-POS).

Aspectos implementados y maduros

- Interfaz principal y navegación (menú lateral, vistas principales) (`main.py`).
- Lógica completa del carrito: añadir/quitar ítems, descuentos, canje de puntos, totales.
- Persistencia atómica de tickets con actualización de stock y registros de pagos.
- Generación de ticket en texto y adaptadores para ESC/POS (según entorno/hardware).

Riesgos y tareas recomendadas

- ESC/POS: adaptadores/hardware específicos pueden faltar o requerir configuración.
- Tests de integración (persistencia + impresión + dispositivo) son limitados; añadir pruebas e2e.
- Documentación del deploy y configuración (`kool_tpv/README.md` y `requirements.txt`) debería actualizarse para pasos reproducibles.
- Manejo de errores en BD corrupta o migraciones: añadir validaciones y rollback tests.

Cómo ejecutar (entorno local)

1. Crear y activar un entorno virtual (ejemplo):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Ejecutar la aplicación en desarrollo:

```bash
python main.py
```

3. Ejecutar tests:

```bash
pytest -q
```

Siguientes pasos sugeridos

- Añadir una sección de "Setup rápido" en `kool_tpv/README.md` con instrucciones reproducibles.
- Implementar pruebas e2e que cubran save_ticket + impresión (mockear impresoras físicas si hace falta).
- Revisar y documentar adaptadores ESC/POS por plataforma (macOS/Linux/Windows).
- Automatizar migraciones y backups de la BD (scripts en `scripts/`).

---

Si quieres, actualizo también `kool_tpv/README.md` y genero un diagrama PNG del flujo (Mermaid) o añado checklist de pruebas.
