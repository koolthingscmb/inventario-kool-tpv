# Resumen técnico del proyecto TPV — 01 Mayo 2026

Fecha: 2026-05-01

Este documento resume el estado del proyecto `kool_tpv` analizado en el workspace.

**Resumen general**

- **Qué hace**: Es una aplicación de Punto de Venta (TPV) de escritorio escrita en Python. Permite buscar y añadir artículos a un carrito, gestionar devoluciones, aplicar descuentos y canje de puntos, seleccionar cliente y cajero, elegir forma de pago (efectivo, tarjeta, web o mixto), persistir tickets en una base de datos SQLite, actualizar stock y puntos de fidelización, y generar/imprimir el ticket (modo texto y soporte opcional ESC/POS).
- **Punto de entrada**: `main.py` (raíz) y el lanzador `kool_tpv/main.py` para desarrollo.

**Tecnologías usadas**

- **Lenguaje**: Python 3.x.
- **UI**: CustomTkinter (`customtkinter`) para la interfaz gráfica.
- **Imágenes**: Pillow (`PIL`).
- **Base de datos**: SQLite con wrapper en `kool_tpv/base_datos/db_wrapper.py` y archivo `kool_bd.db`.
- **Precisión monetaria**: `decimal.Decimal` para evitar errores por floats.
- **Impresión**: Generadores de ticket en texto; soporte opcional ESC/POS (módulos bajo `modulos/impresion/escpos`).
- **Dependencias**: listadas en `requirements.txt` (ej.: `customtkinter`, `pillow`, `reportlab`, `darkdetect`).

**Estructura de carpetas y explicación**

- `kool_tpv/` — paquete principal del proyecto.
  - `config/` — archivos JSON de configuración: layouts, colores, fuentes y botones (controlan la UI).
  - `assets/` — imágenes y logos usados por la UI y ticket.
  - `base_datos/` — wrapper de DB, scripts de inicialización, servicios de persistencia (`ticket_service.py`, `producto_service.py`, `configuracion_service.py`, migraciones y backups de `kool_bd.db`).
  - `modulos/` — módulos funcionales:
    - `tpv/` — todo lo relativo al punto de venta: vistas (`tpv_view_new.py`), controlador (`tpv_controller.py`), servicio de negocio (`tpv_service.py`), carrito (`carrito/`), acciones (buscar artículo, cajero, devoluciones, tickets, cierres), subviews y mapeadores de botones.
    - `clientes/` — UI y servicios de fidelización y gestión de clientes.
    - `impresion/` — generadores de ticket, renderers y adaptadores opcionales para ESC/POS.
  - `utils/` — widgets reutilizables (por ejemplo `ticket_carrito`, `carrito_nav_list`, `button_factory`), utilidades (formatters, config loader, auth, dialogs) y gestores (keyboard manager).
- `scripts/`, `tests/`, `logs/` — utilidades, pruebas unitarias/parciales y logs de la aplicación.
- `RESUMENES/` — carpeta para documentación/resúmenes (se creará el archivo de este resumen aquí).

**Qué partes están ya programadas y qué falta**

- Implementadas y funcionales (según análisis del código fuente):
  - Interfaz principal y navegación (barra lateral, creación de vistas y botón Power) (`main.py`).
  - Vista TPV con grid de acciones y panel de búsqueda de artículos (`kool_tpv/modulos/tpv/tpv_view_new.py`, `actions/buscar_articulo.py`).
  - Servicio de carrito completo: añadir, eliminar, actualizar cantidades, aplicar descuentos y canje de puntos, cálculo de subtotal/IVA/total (`carrito_service.py`).
  - Widget `TicketCarrito` que muestra líneas, totales, cliente, cajero y controla payment controllers (`utils/widgets/ticket_carrito.py`).
  - Payment controllers: efectivo, simple (tarjeta/web) y multi (mixto) (`utils/widgets/payment_controllers/*`).
  - Controlador orquestador del TPV que rebindea botones, crea servicios y finaliza la venta (`tpv_controller.py`).
  - Servicio de negocio `TpvService` que valida y delega persistencia/impresión (`tpv_service.py`).
  - Persistencia atómica del ticket: `ticket_service.py` inserta ticket, líneas, actualiza stock, pagos, auditoría y puntos en una transacción y guarda un snapshot textual post-commit.
  - Generador/servicio de impresión (texto) y soporte opcional para ESC/POS (`modulos/impresion/impresora_service.py` y generadores).

- Elementos a revisar, incompletos o con riesgo:
  - Integración ESC/POS depende de adaptadores opcionales (hay referencias a `WindowsPrinterAdapter`); puede requerir adaptadores adicionales para macOS/Linux.
  - Documentación: `kool_tpv/README.md` contiene plantillas y menciona placeholders; conviene actualizar documentación real del proyecto.
  - Cobertura de tests de integración (persistencia + impresión + hardware) limitada; añadir pruebas automáticas para el flujo crítico recomendado.
  - Robustez en casos de tablas faltantes o BD corrupta: código contiene muchos `try/except` que evitan fallos en UI, pero conviene añadir validaciones y tests.
  - Integración fiscal/legal: `num_ticket` se obtiene desde `ConfiguracionService`, pero no hay integración con dispositivos fiscales externos; si es requisito legal, hay que añadirlo.

**Resumen del flujo de venta (breve)**

1. El usuario añade un artículo mediante el panel de búsqueda o botones del grid → `CarritoService.add_item()`.
2. La UI (`TicketCarrito`) refresca la lista mostrando líneas y totales; totales calculados por `CarritoService.get_resumen_financiero()` (subtotal, desglose IVA, total, descuentos/puntos aplicados).
3. El cajero selecciona la forma de pago en la zona de `payment controllers` (efectivo/tarjeta/web/multi), el controller recoge importes y validaciones (ej. cambio en efectivo).
4. Al confirmar, el payment controller llama al callback `on_finalizar` → mapea a `TpvController.finalize_sale()` con datos de pago.
5. `TpvController` valida cajero y carrito no vacío, prepara `ticket_data` y delega a `TpvService.finalize_sale_ticket()`.
6. `TpvService` llama a `save_ticket(...)` para persistir el ticket y sus líneas en la BD dentro de una transacción:
   - Inserta fila `tickets`, líneas en `ticket_lines`, registra `payments`, actualiza `productos` (stock/ventas), inserta movimientos de stock y puntos/auditoría.
   - Calcula y aplica puntos de fidelización (gasto/ganado/restado) usando `FidelizacionService`.
   - Hace commit y luego genera un `ticket_text` final (snapshot) mediante `ImpresoraService.generar_ticket_desde_id()` y lo guarda en la BD.
7. `TpvService` intenta imprimir el ticket (modo texto/ESC-POS). La UI muestra diálogo de éxito/fracaso y se limpia el carrito en caso de éxito.

---

**Diagrama de flujo (Mermaid)**

```mermaid
flowchart TD
    A[Usuario añade artículo] --> B[CarritoService.add_item()]
    B --> C[TicketCarrito.update_carrito()]
    C --> D{Usuario selecciona forma de pago}
    D -->|Efectivo| E[PaymentControllerEfectivo]
    D -->|Tarjeta/Web| F[PaymentControllerSimple]
    D -->|Mixto| G[PaymentControllerMulti]
    E --> H[Callback on_finalizar -> TpvController.finalize_sale]
    F --> H
    G --> H
    H --> I[TpvService.finalize_sale_ticket()]
    I --> J[save_ticket() - iniciar transacción]
    J --> K[Insert ticket + ticket_lines]
    K --> L[Actualizar stock y ventas]
    L --> M[Insert payments + audit_logs + points_movements]
    M --> N[Commit transaction]
    N --> O[ImpresoraService.generar_ticket_desde_id()] 
    O --> P[Guardar ticket_text en BD]
    P --> Q[Imprimir ticket (texto/ESC-POS)]
    Q --> R[UI: mostrar resultado y limpiar carrito]

    style J fill:#f9f,stroke:#333,stroke-width:1px
    style N fill:#9f9,stroke:#333,stroke-width:1px
```

---

Si deseas, puedo: 1) generar un diagrama PNG/HTML del Mermaid, 2) añadir checklist de pruebas o 3) actualizar `kool_tpv/README.md` con esta documentación.
