# ROADMAP — 01 Mayo 2026

Fecha de generación: 2026-05-01

Propósito: plan de trabajo operativo y priorizado para llevar el proyecto `kool_tpv` desde su estado actual a un MVP estable y mantenible, seguido de integración y mejora continua.

Resumen de fases
- Fase 1 — MVP (2-4 semanas): funcionalidades mínimas para ventas en tienda operativa.
- Fase 2 — Estabilización y Calidad (2-3 semanas): tests, manejo de errores y CI.
- Fase 3 — Integraciones y Hardware (3-6 semanas): ESC/POS, adaptadores, fiscal.
- Fase 4 — Escalado y Mantenimiento (continuo): monitoreo, backups, migraciones.

Fase 1 — MVP (2-4 semanas)
Objetivo: Permitir ventas completas en tienda con persistencia segura y generación de ticket en texto.

Entregables:
- `save_ticket()` robusto y transaccional probado.
- Flujo de venta completo UI → `TpvController` → `TpvService` → `ticket_service`.
- Generador de ticket en texto (`ImpresoraService`) funcionando localmente.
- Documentación mínima: `README.md`, `INSTRUCCIONES_IA.md`, `ROADMAP_01MAYO26.md`.

Tareas (priorizadas):
1. Revisar y arreglar casos críticos de transacción en `ticket_service.py` (1 semana).
2. Añadir tests unitarios para `carrito_service` y `ticket_service` (2-3 tests clave) (4 días).
3. Validaciones de entrada y normalización (`Decimal`) en puntos de entrada UI (3 días).
4. Mejorar mensajes de error y logging en la persistencia (2 días).
5. Checklist de aceptación y pruebas manuales de flujo de venta (2 días).

Estimación: 2–4 semanas (dependiendo de pruebas y correcciones encontradas).

Criterios de aceptación (MVP):
- Crear y persistir tickets correctamente en BD con cambios de stock aplicados.
- UI no bloquea durante persistencia (operación en background o confirmación clara).
- Ticket texto generado y almacenado en BD; impresión en modo texto funciona.
- Tests unitarios principales pasan en entorno local.

Riesgos conocidos:
- Adaptadores ESC/POS afectan a impresión (se gestiona en Fase 3).
- BD existente (schema) puede requerir migraciones; hacer backup antes de pruebas.

Fase 2 — Estabilización y Calidad (2-3 semanas)
Objetivo: aumentar fiabilidad, cobertura de tests y preparar CI.

Entregables:
- Suite de tests unitarios e integración para flujo `finalize_sale`.
- Pipeline básico de CI que ejecuta tests y lint.
- Manejo de errores consistente y monitorización básica de logs.

Tareas:
1. Escribir tests de integración que usen BD temporal (sqlite in-memory/file temporal) (5-7 días).
2. Añadir linters y formateadores (`black`, `isort`, `flake8`) y reglas mínimas (2 días).
3. Configurar CI (GitHub Actions / similar) para ejecutar tests y reportar (3 días).
4. Añadir tests para adaptadores de impresión en modo stub (2 días).

Criterios de aceptación:
- CI ejecuta tests y muestra resultados en PRs.
- Cobertura mínima para `carrito_service` y `ticket_service` razonable (>60%).

Fase 3 — Integraciones y Hardware (3-6 semanas)
Objetivo: soportar impresión ESC/POS en plataformas objetivo y prepararse para integración fiscal si aplica.

Entregables:
- Adaptadores ESC/POS por plataforma (macOS/Linux/Windows) con stubs y tests.
- Documentación de hardware y fallback a modo texto.
- Evaluación e integración con dispositivo fiscal (si es requerido por normativa local).

Tareas:
1. Implementar/adaptar `PrinterAdapter` para macOS/Linux (2 semanas).
2. Añadir pruebas de integración de impresión usando stubs/mocks (1 semana).
3. Si aplica, diseñar integración con controlador fiscal (requisitos legales) (2-4 semanas según requisitos).
4. Verificar rendimiento de impresión y concurrencia (hilos/procesos) (3 días).

Criterios de aceptación:
- Impresión ESC/POS funcional en al menos 1 plataforma objetivo y con fallback probado.
- Documentación de instalación y configuración para impresoras.

Fase 4 — Escalado y Mantenimiento (continuo)
Objetivo: procesos de mantenimiento, backups automáticos, migraciones y plan de despliegue.

Entregables y tareas:
- Backups programados de `kool_bd.db` y scripts de restauración.
- Sistema de migraciones versionadas para cambios de esquema.
- Monitorización de logs y alertas básicas (disk/DB errors).
- Plan de releases y changelog.

Roadmap de hitos (cronología propuesta)
- Semana 1–2: Fase 1 tareas críticas, tests básicos.
- Semana 3: Completar tests y preparar CI (Fase 2 inicio).
- Semana 4–6: Integraciones ESC/POS y adaptadores (Fase 3 inicio).
- Posterior: estabilización continua y mantenimiento.

Recursos y responsabilidades (sugerido)
- Responsable técnico: mantener `ticket_service`, `tpv_service` y coordinar integraciones.
- QA/Dev: escribir tests y configurar CI.
- Infra/Soporte: pruebas hardware e impresoras en tienda.

Riesgos y mitigaciones
- Riesgo: impresión ESC/POS no compatible con todas las impresoras → Mitigación: desarrollar adaptadores, documentar modelos soportados y fallback texto.
- Riesgo: cambios en esquema BD que rompan integridad → Mitigación: migraciones versionadas y backups automáticos antes de aplicar cambios.
- Riesgo: bloqueo de UI por operaciones largas → Mitigación: mover persistencia/impresión a hilos o procesos y comunicar estado a UI.

Siguientes pasos inmediatos (primeros 3 días)
1. Ejecutar pruebas manuales del flujo de venta y documentar fallos críticos.
2. Implementar y correr los 3–5 tests unitarios más críticos (carrito y persistencia).
3. Crear backup de la BD actual y preparar entorno de tests con BD temporal.

Notas finales
- Este roadmap es una propuesta priorizada. Ajustar estimaciones según disponibilidad de recursos y hallazgos en pruebas.
- Para cambios que afecten a la BD o a la API pública, actualizar `INSTRUCCIONES_IA.md` y añadir notas en `README.md`.
