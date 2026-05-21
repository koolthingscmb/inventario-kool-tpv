# PR Draft: Tickets overlay + TicketDisplay global

Branch: `feature/tickets-overlay`

Summary
-------
Implementa una subvista profesional para `TICKETS` y convierte `TicketDisplay` en un visor global (overlay) gestionado por `TpvController`.

Why
---
- Evita usar `ticket_text` snapshot (deprecated) y genera tickets on‑demand vía `ImpresoraService`.
- Mejora la UX: la lista de tickets mantiene ancho completo y el visor no reduce espacio (overlay sobre `ticket_carrito`).
- Centraliza caché en memoria para respuestas rápidas.

Changes (high level)
--------------------
- `kool_tpv/modulos/ticket/ticket_repository.py`: add `listar_tickets(termino)` (read API).
- `kool_tpv/modulos/tpv/subviews/tickets_subview.py`: new subview using `SearchablePaginatedNavList`; delegates display to controller.
- `kool_tpv/modulos/tpv/tpv_controller.py`: added `setup_ticket_display()`, `show_ticket(ticket_id)`, `hide_ticket()` and `_ticket_display_cache`.
- `kool_tpv/utils/widgets/ticket_display.py`: reused existing widget as overlay (no API changes required).
- `tests/test_ticket_repository_listar_tickets.py`: new unit test (in‑memory DB) — passed locally.
- `RESUMENES/PROYECTOGLOBAL.md`: documentation updated with explanation and instructions.

Files modified/added (concise)
-----------------------------
- Modified: `kool_tpv/modulos/tpv/tpv_controller.py`
- Modified: `kool_tpv/modulos/tpv/subviews/tickets_subview.py`
- Modified: `kool_tpv/modulos/ticket/ticket_repository.py`
- Added: `tests/test_ticket_repository_listar_tickets.py`
- Added: `RESUMENES/PROYECTOGLOBAL.md`

How to test (manual)
--------------------
1. Activar venv: `source .venv/bin/activate`
2. Run app: `python main.py`
3. In TPV: Click `TICKETS` → the list appears with full width.
4. Click a ticket row → the ticket viewer should appear above the `ticket_carrito` (overlay).
5. Close the `TICKETS` subview → the overlay must disappear.

How to test (automated)
------------------------
- Unit test added: `pytest tests/test_ticket_repository_listar_tickets.py` (passes locally).
- TODO: add unit tests for `TpvController.show_ticket`/`hide_ticket` with mocked `ImpresoraService`.

Checklist before merging
------------------------
- [x] Code compiles and unit tests pass locally (ran the new test).
- [ ] Add tests for `show_ticket`/`hide_ticket` (mock `ImpresoraService`).
- [ ] Manual UI verification (recommended: screenshot/video in PR).
- [ ] Assign 1–2 reviewers.
- [ ] Ensure CI is green.

Notes and risks
---------------
- Cache is in‑memory; consider LRU or TTL if memory becomes concern.
- The legacy `TicketsUI` files were left in repo (not deleted) until this PR is validated.

Suggested reviewers
-------------------
- `@backend-dev` (DB/repo)
- `@frontend-dev` (UI/visor)

Screenshots
-----------
- (Attach a screenshot or short recording demonstrating overlay behavior)

End of draft.
