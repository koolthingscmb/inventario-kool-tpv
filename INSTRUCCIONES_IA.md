# INSTRUCCIONES_IA

Propósito: documento guía para que cualquier IA (o desarrollador) trabaje en este proyecto TPV sin romper la coherencia arquitectural, de datos ni la experiencia de usuario.

---

## Reglas Base (definidas por el equipo)

1. Usar siempre `customtkinter` para la UI.
2. Mantener la arquitectura: lógica en archivos terminados en `_service.py` y UI en archivos terminados en `_view.py`.
3. Usar estrictamente `decimal.Decimal` para todos los cálculos monetarios y conversión/normalización de importes.
4. Los logs deben escribirse en la carpeta `/logs` del proyecto; usar niveles adecuados (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
5. Explicar la lógica en lenguaje natural (breve) antes de proponer código nuevo.

---

## Reglas Adicionales Sugeridas (análisis del proyecto)

Estas reglas se añaden tras analizar la base de código actual y están destinadas a prevenir errores comunes, mantener consistencia y facilitar revisiones automáticas.

- Transacciones y BD:
  - Siempre ejecutar operaciones que modifiquen varias tablas dentro de una transacción explícita (BEGIN / COMMIT / ROLLBACK).
  - Cuando sea posible, pasar el cursor/connection desde el servicio superior a funciones más bajas para reutilizar la misma transacción (p. ej. `get_next_ticket_number(cur)`).
  - En capas de servicio, NO ejecutar commits parciales: commit solo al final del flujo de negocio que requiere atomicidad.

- Nombres y organización de código:
  - Prefijo de archivos: `*_service.py` para lógica de negocio y persistencia; `*_view.py` o `*_ui.py` para widgets/vistas y layouts.
  - Funciones que devuelven datos estructurados deben devolver diccionarios con claves documentadas y no `None` inesperado.
  - Usar nombres descriptivos: `carrito_service`, `ticket_service`, `tpv_controller`.

- Manejo de excepciones:
  - Evitar capturas amplias sin re-lanzar o sin logging (`except Exception:` solo si se hace `logging.exception(...)` y se toma una decisión clara).
  - En servicios críticos (persistencia de tickets, actualización stock) propagar la excepción hacia arriba después de loggear para que el controlador decida rollback y notificar al usuario.

- Rutas y archivos (assets/config):
  - Todas las rutas relativas a assets/config deben resolverse a partir del `project_root` o usando `Path(__file__).resolve().parents[...]` para evitar dependencias del cwd.
  - Validar existencia de ficheros (imágenes, DB, JSON) y fallar con mensajes claros si faltan.

- Formateo y validaciones de datos:
  - Normalizar entradas numéricas antes de convertir a `Decimal` (strip, replace(',', '.') y envolver en `Decimal(str(...))`).
  - Validar IDs (productos, clientes) y tipos antes de usarlos en consultas SQL.

- Logs y auditoría:
  - Registrar eventos clave: creación de ticket, rollback de transacción, errores de stock, cambios en cliente/puntos.
  - No loggear datos sensibles (tarjetas completas, contraseñas) en texto plano.

- Impresión / hardware:
  - El soporte ESC/POS debe estar desacoplado y encapsulado en adaptadores; la aplicación debe poder degradar a modo `texto` sin fallo.
  - Documentar adaptadores soportados por plataforma (Windows/Linux/macOS) y proveer stubs de prueba para CI.

- Concurrencia y UI:
  - Evitar bloqueos de la UI: tareas largas (persistencia, impresión, lectura de red) deben ejecutarse en hilos/threads separados o procesos y comunicar resultados a la UI via `after()` o colas seguras.

- Tests y calidad:
  - Añadir tests unitarios para servicios (ej: `carrito_service`, `ticket_service`) y tests de integración para el flujo `finalize_sale`.
  - Verificar que los tests ejecuten sobre una BD de prueba separada (archivo sqlite temporal) y no modifiquen `kool_bd.db` de producción.

- Migraciones y esquema:
  - Gestionar cambios en esquema con migraciones versionadas (script `migraciones/`); proporcionar funciones de rollback o backups automáticos antes de migrar.

- Internacionalización y formatos:
  - Separar cadenas visibles al usuario en archivos de recursos o favorecer plantillas; usar formato UTC en timestamps en BD y presentar en zona local en la UI si es necesario.

- Seguridad y secretos:
  - No almacenar credenciales en el repositorio; usar variables de entorno o archivos `config` excluidos por `.gitignore`.

- Documentación del cambio (commits):
  - Commits que modifiquen la BD o la API pública deben incluir nota en el README y un changelog breve.

- Contratos y compatibilidad:
  - Cambios en las firmas de funciones públicas (`save_ticket`, `finalize_sale_ticket`, etc.) deben mantener compatibilidad o documentar la migración.

- Estilo y tipado:
  - Usar type hints en nuevas funciones y métodos; mantener estilo PEP8 y formatear con `black`/`isort` donde aplique.

- Manejo de errores de negocio:
  - Validaciones de negocio (p. ej. impedir venta si hay una devolución activa) deben lanzarse como errores específicos (`BusinessError`) y manejarse en el controlador para mostrar mensajes al usuario.

- Regla de documentación previa a código:
  - Para cualquier cambio no trivial, incluir un breve bloque (3-6 líneas) explicando la lógica y el flujo antes del PR o del patch, tal y como reza la Regla Base 5.

---

## Cómo usar este documento

- Antes de implementar: leer y respetar las reglas base y las adicionales sugeridas.
- Si la IA detecta un caso no cubierto por las reglas, abrir una sección propuesta en este mismo archivo `INSTRUCCIONES_IA.md` explicando la excepción y proponiendo la regla que evita el problema.

---

Generado tras análisis del código disponible en el workspace el 2026-05-01. Actualiza este documento cuando se aprueben normas adicionales en el equipo.
