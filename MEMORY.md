# MEMORY.md — Kool TPV
Memoria entre sesiones. Actualización: 2026-10-24, rama `windows-beta`. Máximo ~50 líneas.

## Trabajo actual — pendiente de prueba del usuario
- Editoriales y fuentes: UI dividida 50/50. Arriba editorial (ID, nombre, web, fuente principal/reserva
  con SearchableCombo); abajo fuente (ID, nombre, plataforma, URL y credenciales). Chips y CRUD propios.
- Seleccionar editorial carga su fuente principal; pulsar chip de fuente desactiva editorial.
  NUEVA limpia ambas zonas. Seleccionar no guarda; cada zona tiene su botón GUARDAR.
- Fuentes independientes: ya no se eliminan automáticamente al borrar/guardar editoriales.
  Editar fuente en uso pide confirmación mostrando editoriales afectadas, incluidas reservas.
  Borrar fuente en uso se bloquea: hay que reasignar primero; el DELETE también está protegido.
- Plataforma desde `TIPOS_FUENTE` del registro, no lista duplicada en UI. Opciones de fuentes
  desde BD con ID visible para distinguir nombres iguales. Crear un adaptador nuevo sigue requiriendo código.
- Capas: `editorial_repository` -> `fuentes_editorial_service` -> `editoriales_ui`.
  `guardar_asignacion` solo modifica editorial; guardar fuente sin `editoriales` no cambia asignaciones.
- Verificado: compilación de 3 Python, diff sin errores, CRUD y validaciones con SQLite en memoria
  usando esquema real (solo lectura); estructura UI 50/50 y flujos de selección/guardado/borrado.
  No se escribió en BD real ni se consultaron portales. Apariencia no inspeccionada. Sin commit/push.

## Shopify — estado y decisiones
- SUBIDA: NUEVO/EDITAR comparten base, componentes y builders sin widgets; imágenes en rejilla de 3.
- Stock: subidas con `changeFromQuantity: null`; SINC lee `on_hand`, no `available`.
- METACAMPOS: `reglamento` file_reference se sube al guardar; reabrir antes de actualizar pierde lo preparado.
- Masiva Shopify: `metafieldsSet` en bloques de 25, nunca `productSet` (borra omitidos).
  Excluye rich_text/file_reference; listas admiten `[]`; modos AÑADIR/CAMBIAR/VACIAR.
- Colecciones API 2026-07: `collectionUpdate` selectionsToAdd/Remove y filtro `inCollection`.
  Colección manual vacía = 0 fuentes; familia nueva con borrador PRODUCTO FANTASMA; Family- por tag es legado.
- Familia: AÑADIR solo sin familia; CAMBIAR todos; entrar nueva -> metacampo -> salir antigua.
- Espejo cómic en EDICIÓN MASIVA almacén: 4 claves de `MetacamposComicService.GRUPOS`, ausente = borrar,
  claves ajenas conservadas; pending_sync + auditoría. Verificado por usuario y subido (`8844ef9`).
- CONFIG/EQUIVALENCIAS: valores vivos agrupados, palabras por comas; huérfanas preservadas SIN EFECTO.
  JSON propiedad de `ComparadorMetacamposService`. Verificado/subido (`73764c7`).
- Duplicados tras subida: una opción por fila sin recorte explícito; verificado/subido (`c992e41`).

## Reglas y fuentes OBTENER
- Mac = BD de pruebas; Windows = tienda. Enlaces Shopify locales: subir en Mac no enlaza Windows.
  Sync Windows e impresión térmica de vales comprobados por usuario.
- Stock: todo cambio normal por `StockMovementService.aplicar_movimiento` dentro de transacción:
  UPDATE + movimiento + cola; rollback conjunto. Tras confirmar `procesar_pendientes_async()`.
  Albaranes encolan una vez por producto al final; cola serial durable con reintento manual.
- Vales = pago, no descuento; consumo atómico. OBTENER: géneros a METACAMPOS, no TAGS; nunca PVP.
- Fuentes vivas: `almacen/services/fuentes/`, registro por plataforma; principal y luego reserva.
  LINK multi `url (etiqueta); url2 (etiqueta2)`; avance_comic solo con etiqueta Avance.
- Astiberri por EAN verificado/subido (`b7a8ccf`): /search XHR, verifica ISBN de ficha; reserva por título/slugs.
  /search tiene Disallow en robots.txt; uso aprobado por usuario. No prometer ausencia de bloqueos o riesgo legal.
- Sin adaptador propio, configurar Azeta (Penguin, Kibook y otros); no reinvestigar sin petición.
- Portadas locales gitignored; máxima calidad variable: Astiberri ~2400px, Ivrea 400, Planeta 300, Norma 229.
- Fragilidad: Panini Queue-it, Azeta reCAPTCHA, Ivrea límites AJAX (usa sitemap). Credenciales nunca en logs/chat.

## Deuda conocida
- crear_producto_ui grande; tests de base no verdes; openai sin usar; documentación antigua. No corregir sin permiso.
