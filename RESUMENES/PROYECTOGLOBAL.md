- # PROYECTO GLOBAL — Estado y notas (14–21 Mayo 2026)

Fecha: 2026-05-14 → 2026-05-21
Autor: Informe técnico/registro de sesiones

## Introducción al proyecto

Esta documentación ofrece un resumen técnico del proyecto `KOOL_TPV_V2` pensado para nuevos colaboradores.

- **Objetivo del proyecto:** TPV (terminal punto de venta) para gestión de ventas, clientes, fidelización, impresión de tickets y gestión de inventario.
- **Stack tecnológico:** Python 3.x, CustomTkinter para UI, SQLite para persistencia, Decimal para manejo de dinero, pytest para tests.
- **Entradas principales:** `main.py` arranca la aplicación; la vista principal está en `kool_tpv/modulos/tpv/tpv_view_new.py` y la orquestación en `kool_tpv/modulos/tpv/tpv_controller.py`.
- **Cómo ejecutar localmente:** activar el virtualenv y ejecutar `python main.py` desde la raíz del repo. Tests: `PYTHONPATH=. .venv/bin/python -m pytest -q`.
- **Dónde leer primero:** `RESUMENES/PROYECTOGLOBAL.md` (este archivo), luego `kool_tpv/modulos/tpv/tpv_view_new.py`, `kool_tpv/modulos/tpv/tpv_controller.py`, `kool_tpv/modulos/tpv/tpv_service.py` y `kool_tpv/base_datos/money_adapter.py`.

Resumen ejecutivo
------------------
- Estado general del TPV: UI en CustomTkinter, servicios modulares, persistencia SQLite.
- Se ha abordado un problema crítico con el manejo de dinero (mezcla céntimos/Decimal) y aplicado fixes y helpers (`prepare_for_db`, `read_from_db`, `ensure_cents` en utils).
- Se añadió una subvista profesional para `TICKETS` con paginación y búsqueda, y se re-diseñó el `TicketDisplay` como visor global (overlay) gestionado por el `TpvController`.

Cambios claves (resumen)
------------------------
- `kool_tpv/modulos/ticket/ticket_repository.py`: añadido `listar_tickets(termino)` para lectura de tickets desde la BD (usar repo en vez de SQL en UI).
- `kool_tpv/modulos/tpv/subviews/tickets_subview.py`: nueva subvista `TicketsSubView` con `SearchablePaginatedNavList` en la izquierda y delegación al visor central.
- `kool_tpv/modulos/tpv/tpv_controller.py`: creado `setup_ticket_display()`, `show_ticket(ticket_id)` y `hide_ticket()`; cache en memoria por `ticket_id`.
- `kool_tpv/utils/widgets/ticket_display.py`: widget existente reutilizado; ahora usado como overlay gestionado por el controlador.
- Tests: añadido `tests/test_ticket_repository_listar_tickets.py` (DB :memory:) — verde.

Detalles: `TicketsSubView` (qué y por qué)
---------------------------------------
Qué hace
- Implementa la vista de tickets con búsqueda y paginación infinita (reutiliza `SearchablePaginatedNavList`).
- No contiene ya un `TicketDisplay` embebido; delega la visualización al visor global para evitar que la columna derecha estreche la lista.

Por qué
- Mejora UX: la lista mantiene ancho razonable para lectura y selección. El visor aparece como overlay encima del área del carrito/ticket, no ocupa columna del subview.
- Reutilización: el mismo `TicketDisplay` puede usarse en otras partes si se necesita.

Comportamiento principal implementado
-----------------------------------
- Selección (single-click) en la lista → `TicketsSubView` delega a `view.controller.show_ticket(ticket_id)`.
- `TpvController.show_ticket(ticket_id)`:
  - consulta caché local (`self._ticket_display_cache`) por `ticket_id`.
  - si no hay caché, llama a `self.impresora_service.generar_ticket_desde_id(ticket_id)` (o instancia `ImpresoraService` como fallback).
  - guarda resultado en caché y llama `self._ticket_display.set_content(contenido)` y muestra el overlay mediante `place()` o `pack()` según disponibilidad.
- `TpvController.hide_ticket()` oculta el overlay y limpia contenido (`place_forget()` / `pack_forget()` + `clear()`).
- Ciclo de vida: `TicketsSubView.destroy()` invoca `view.controller.hide_ticket()` para asegurar que el visor desaparece cuando se cierra la subvista.

Anexo: cómo usar el visor global (`TicketDisplay`) — implementor notes
-----------------------------------------------------------------
Arquitectura y ownership
- `TicketDisplay` es un widget (CTkFrame) con API pública mínima: `set_content(contenido)`, `clear()`, `get_content()`.
- Ownership: lo crea y posee `TpvController` (`self._ticket_display`).

API de alto nivel expuesta por el controlador
- `controller.show_ticket(ticket_id)` — asegura generación/caché y muestra el visor sobre el `ticket_carrito`.
- `controller.hide_ticket()` — oculta y limpia el visor.

Por qué esta aproximación es buena práctica
- Centraliza la lógica de generación y caché (evita duplicación y race conditions).
- Separa responsabilidades: subviews son ligeras (presentación/listado) y el controlador maneja servicio y ciclo de vida del visor.
- Facilita tests: podemos mockear `ImpresoraService` y probar `show_ticket`/`hide_ticket` sin UI.

Consideraciones y riesgos
- Si el visor global queda olvidado en otras rutas, puede volverse "zombie" (widget creado pero no usado). Mitigación: ownership claro y llamadas `hide_ticket()` en `destroy()` de subviews.
- Cache en memoria: simple dict por `ticket_id`; si el dataset crece, considerar LRU o TTL.

Cómo probar manualmente (quick-check)
------------------------------------
1. `source .venv/bin/activate`
2. `python main.py`
3. Abrir TPV → botón `TICKETS` → confirmar que la lista ocupa el ancho esperado.
4. Hacer click en un ticket → debe aparecer el visor encima del carrito con el ticket generado.
5. Cerrar la subvista `TICKETS` → el visor debe desaparecer.

Próximos pasos recomendados
---------------------------
- Añadir tests unitarios para `TpvController.show_ticket`/`hide_ticket` (mock `ImpresoraService`) — pendiente.
- Añadir E2E para `finalize_sale` con BD en memoria y verificación de `tickets`, `ticket_lines`, `payments`.
- Revisar la caducidad o tamaño de la caché del visor (LRU) si es necesario.

Referencias y archivos modificados
---------------------------------
- `kool_tpv/modulos/tpv/subviews/tickets_subview.py` (nuevo)
- `kool_tpv/modulos/tpv/tpv_controller.py` (show/hide + cache)
- `kool_tpv/modulos/ticket/ticket_repository.py` (listar_tickets)
- `kool_tpv/utils/widgets/ticket_display.py` (widget usado)
- `tests/test_ticket_repository_listar_tickets.py` (nuevo)

---
Fin: PROYECTOGLOBAL.md — resumen actualizado con anexo del visor global.
