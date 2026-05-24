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
 - Timestamps en BD: almacenar en UTC (política estándar).  <-- NOTE: timestamps en BD = UTC
 - Nuevo util de tiempo: `kool_tpv/utils/time_utils.py` con `now_utc_str()` y `utc_str_to_local_str()`; garantiza que los timestamps se guarden en UTC y se conviertan a horario local solo al mostrar.
- Se ha abordado un problema crítico con el manejo de dinero (mezcla céntimos/Decimal) y aplicado fixes y helpers (`prepare_for_db`, `read_from_db`, `ensure_cents` en utils).
- Se añadió una subvista profesional para `TICKETS` con paginación y búsqueda, y se re-diseñó el `TicketDisplay` como visor global (overlay) gestionado por el `TpvController`.

Cambios claves (resumen)
------------------------
- `kool_tpv/modulos/ticket/ticket_repository.py`: añadido `listar_tickets(termino)` para lectura de tickets desde la BD (usar repo en vez de SQL en UI).
- `kool_tpv/modulos/tpv/subviews/tickets_subview.py`: nueva subvista `TicketsSubView` con `SearchablePaginatedNavList` en la izquierda y delegación al visor central.
- `kool_tpv/modulos/tpv/tpv_controller.py`: creado `setup_ticket_display()`, `show_ticket(ticket_id)` y `hide_ticket()`; cache en memoria por `ticket_id`.
- `kool_tpv/utils/widgets/ticket_display.py`: widget existente reutilizado; ahora usado como overlay gestionado por el controlador.
 - Widget añadido / centralizado: `TicketDisplay` (CTkFrame) usado como overlay global por `TpvController` — facilita previews (tickets/cierres) y evita duplicación de UI.
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

## Nueva sección: Cierres (21/05/2026)

Se ha incorporado soporte para cierres de caja (Cierre Z) y un historial asociado.

- Migraciones:
  - `scripts/migrate_cierres.sql` crea `cierres` y `cierres_lineas` (índices: fecha, num y relaciones tickets).

- Flujo implementado:
  - `CierreCajaProcessor.process()` calcula totales, crea una entrada en `cierres` y genera líneas en `cierres_lineas` por cada ticket incluido. El método es atómico y **no imprime**.
  - La impresión del cierre la realiza la UI a través de `ImpresoraService` y `CierreTicketGenerator`.
  - Se añadió `TicketsSubView(pending_only=True)` para mostrar tickets pendientes de cierre (filtro `cierre_id IS NULL`).

- Cambios en el controlador/UI:
  - `tpv_controller` expone un proxy `view._cierre_ui.show()` para mantener compatibilidad con el mapeo de botones existente.
  - `CierresSubView` lista cierres y permite abrir la vista de tickets pendientes y ejecutar cierres desde la UI.

- Recomendaciones para el siguiente desarrollador:
  - Revisar `scripts/migrate_cierres.sql`, ejecutar migración en entorno de pruebas.
  - Probar cierre completo: abrir `CIERRES` → ver pendientes → seleccionar rango/entradas → ejecutar cierre → verificar tablas `cierres` y `cierres_lineas`.
  - Verificar que el `CierreCajaProcessor` devuelve la estructura esperada y que la UI marca `printed` sólo tras la operación de impresión.

  ## Update 22/05/2026 — Cambios recientes (tickets / cierres)

  Resumen breve de lo implementado hoy:

  - Añadidos `date_from` y `date_to` (`date_picker_entry`) en la cabecera de la subvista `TicketsSubView` y conectados al filtrado de la lista (refresh automático al cambiar fechas).
  - Añadido botón pequeño configurable `X` en la cabecera (config-driven) protegido por autenticación admin (flujo via `AuthService`).
  - Flujo de cierre: al pulsar `X` y tras autenticación se construye la selección de tickets (rango si fechas, sino pendientes), se ejecuta `CierreCajaProcessor.process()` (inserta `cierres` y `cierres_lineas`) y se genera texto de cierre con `CierreTicketGenerator` para mostrar un preview en el `TicketDisplay` global. La fase de preview ejecuta `process()` (ya persiste en BD); la confirmación final solo completa UI (ocultar visor, limpiar cache y refrescar lista).
  - Corrección crítica en `kool_tpv/modulos/ticket/cierre_caja_processor.py`: `num_ticket` ahora se inserta en `cierres_lineas` como texto (no convertir a int) para evitar pérdida/formato incorrecto.
  - `CierresSubView._map_cierre()` ahora convierte `total_ingresos` de céntimos a euros al leer de BD (mostrar valores legibles en la UI).
  - Añadido `TpvController.show_cierre(cierre_id)` que genera el texto del cierre desde la BD y lo muestra en el `TicketDisplay` global.
  - Pequeño fix sintáctico en `tpv_controller.py` (try/except faltante) y varios `logger.info` de trazabilidad en el flujo de cierre.

  Notas operativas:

  - Los cambios están en la rama `feature/tickets-overlay` y han sido commiteados y empujados al remoto.
  - Pendiente: mover operaciones pesadas (generación/tareas DB) a hilo de fondo para no bloquear la UI; decidir si `process()` debe ejecutarse solo tras la confirmación final (ahora se ejecuta durante preview, por intención del flujo actual).

  Fin: update 22/05/2026

## Update 23/05/2026 — Cambios implementados (captura admin y cierre)

- `AuthService.validate_admin_password` ahora devuelve una tupla `(is_valid, user_obj)` donde `user_obj` contiene al menos `id` y `nombre` del admin autenticado. Esto permite propagar identificación del autorizador en flujos sensibles sin recurrir a estado mutable.
- `TicketsSubView` (handler del botón `X`) desempaqueta la respuesta de `validate_admin_password`, NO guarda el usuario en `self` y pasa `usuario_id` y `cajero` como parámetros locales a `CierreCajaProcessor.process(...)`.
- `CierreCajaProcessor.process(...)` ya acepta `usuario_id` y `cajero` y los transmite a `CierreService.create_cierre_atomic(...)`, de forma que la columna `cierres.usuario_id` y `cierres.cajero` quedan pobladas al crear el cierre.
- Se añadieron tests unitarios básicos en `tests/test_auth_service.py` para verificar la nueva API de `AuthService.validate_admin_password` (casos: éxito y fallo); los tests se ejecutaron localmente y pasan.
- Se actualizó la UI y puntos de validación en `ConfigView` para ser compatibles con la nueva API (manteniendo compatibilidad hacia atrás con llamadas que esperen `bool`).
- Commit y push: los cambios locales fueron commiteados y enviados al remoto (`feature/tickets-overlay` workflow). Ver log para el hash de commit.

Impacto y recomendaciones:
- Flujo más robusto: la identidad del autorizador se transmite explícitamente, evitando estados mutables en las vistas y mejorando trazabilidad/auditoría.
- Recomendado: revisar `create_cierre_atomic` en pruebas integradas para asegurar que los valores `usuario_id` y `cajero` queden visibles en la UI (preview/imprimir) y en la BD.


