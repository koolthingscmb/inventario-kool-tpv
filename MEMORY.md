# MEMORY.md — Kool TPV
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no
aporte. (Última actualización: 2026-10-20, rama `windows-beta`.)

## Estado actual (Shopify)
- SUBIDA separada en NUEVO y EDITAR (`SubidaBaseView` + componentes + builders sin widgets).
  Stock en subidas: `changeFromQuantity: null`. SINC lee `on_hand` (no `available`).
- METACAMPOS: rejilla empaquetada; `reglamento` (`file_reference`) con ABRIR/NUEVO (el PDF
  se sube al guardar). MASIVA: texto/número/SÍ-NO, listas, familia y `list.metaobject_reference`
  con ELEGIR VALORES; modos AÑADIR/CAMBIAR/VACIAR (`[]` válido).
- NUEVO/EDITAR: imágenes en rejilla de 3 por fila.
- FIX Windows: Colecciones de METACAMPOS ya no abre diálogos desde el hilo (`frame.after`).

## Decisiones Shopify (y por qué)
- Metacampos en masa con `metafieldsSet` (bloques de 25); NUNCA `productSet` (borra lo omitido).
  `rich_text`/`file_reference` fuera de la masiva.
- Colecciones (API 2026-07): `collectionUpdate` con `selectionsToAdd/Remove`; filtrar siempre con
  `inCollection`. Colección manual VACÍA = 0 fuentes. Toda colección de familia nueva lleva el
  borrador 'PRODUCTO FANTASMA'; las `Family-...` por etiqueta son LEGADO. Sin exclusiones parche.
- Familia en masa: AÑADIR = solo productos sin familia; CAMBIAR = a todos. Orden: entrar en la nueva
  -> metacampo -> salir de la antigua. En EDITAR se conservan las colecciones del producto.

## Aprendizajes
- No decir sí a todo: opinión profesional con pros y contras. Preguntar antes de cambiar nada.
- Escrituras en Shopify: probar con borrador y verificar con lectura antes/después.
- En EDITAR, reabrir METACAMPOS antes de actualizar recarga y pierde lo preparado.
- Un dato mal configurado se corrige en su sitio, nunca con parche en el código (sin hardcodeo).
- Con el usuario enfadado: frases cortas, sin nombres de tablas; reproducir antes de explicar.

## Fuentes de datos de producto (OBTENER) — CERRADO el 2026-10-20
- Capas: `editorial_repository` (SQL) <- `fuentes_editorial_service` <- `ui/editoriales_ui`;
  `obtener_datos_service` (botón OBTENER) + `fuentes/registro.py` (plataforma -> clase) +
  `PortadasService` (`assets/portadas/<ean>.jpg`, `_2`...; carpeta se crea sola; no va en git).
- Tablas: `editoriales_fuentes` (plataforma, url, nif, usuario, password) y `editoriales`
  (fuente_id, `fuente_reserva_id` [mig. 063], `web_buscar`, `web_dominio`). OBTENER prueba la
  fuente principal y luego la RESERVA. Con plataforma `web` la URL va a `web_buscar` y IR la abre.
- Reglas: nunca precios/PVP; TAGS vacíos; LINK multi `url (etiqueta); url2 (etiqueta2)` (IR elige);
  credenciales solo en `editoriales_fuentes`, NUNCA en repo, chat ni logs.
- Plataformas: zonalibros (Norma, demografía de 'Materia'), planeta, shopify (Milky Way: autor y
  demografía de tags, avance), panini_web, ivrea_web (sitemap), udl_web (La Cúpula), astiberri_web
  (slug+EAN, imágenes `blobs`), arechi_web (sitemap+API, ceros a la izquierda ignorados),
  azeta_web (portal de cliente, por EAN). `azeta_web` será la RESERVA de casi todo.
- astiberri_web (2026-10-23): busca por EAN en `/search?key=keyword&value=` con
  cabecera XHR (el buscador indexa ISBN; verifica cada ficha por su EAN publicado).
  Plan B: slugs por nombre + candidatas del buscador por título. `/search` está
  Disallow en su robots.txt — decisión del propietario. Flag `busca_por_ean_y_nombre`.
- Sin fuente propia, van con `azeta_web` (config, sin código): Penguin/Distrito Manga, Kibook,
  Mangaline, Devir, Yermo, Nuevo Nueve, Dolmen, Grafito y los manga menores. No volver a investigar.
- Portadas máximas: Astiberri ~2400 px, Milky Way ~1030, Panini ~856, UDL ~800, Azeta ~650, Arechi
  ~624, Ivrea 400, Planeta 300, Norma 229. Google recomienda ~800: ampliar a mano en los más vendidos.
- Frágil: panini.es solo deja pasar con UA Googlebot (Queue-it); Azeta acepta el login sin token
  reCAPTCHA hoy; Ivrea limita su buscador AJAX por IP (por eso usa el sitemap).

## Reglas de arquitectura (permanentes)
- PUERTA ÚNICA DE STOCK (2026-10-23): todo cambio de `productos.stock_actual` debe
  pasar por `StockMovementService.aplicar_movimiento(pid, cantidad, motivo, usuario_id,
  ticket_line_id, ventas_change, encolar_sync, motivo_sync, cur)` = UPDATE +
  movimiento + encargo SYNC_PRODUCTO, en la transacción del llamador (rollback =
  desaparece todo). NO hacer UPDATE a mano. Tras confirmar: `procesar_pendientes_async()`.
  Albaranes: `encolar_sync=False` y encolan 1 por producto al final. Fuera a
  propósito: reseteo de tienda y tools. El log muestra "nombre (EAN) -> Stock: N".
- Cola sync: encolar dentro de la transacción; un solo trabajador serial; errores
  con motivo real en SYNC -> PENDIENTES (reintento manual del usuario); huérfanos
  'pendiente' se drenan al arrancar.
- Vales = forma de pago (no descuento), consumo atómico en la venta (mig. 065-067).
- `avance_comic`: solo se envía si LINK tiene entrada etiquetada 'Avance'.
- OBTENER: géneros van a METACAMPOS, no a TAGS. Fuentes vivas: `almacen/services/fuentes/`.

## Pendiente
- HECHO (2026-10-23): modo METACAMPOS en la EDICIÓN masiva del almacén: elige
  producto referente y copia sus 4 metacampos cómic (demografia, genero_comic,
  subgenero_comic, contenido_adultos) en ESPEJO al lote (ausente en el referente
  = se borra en el destino; claves ajenas del destino se conservan).
  `pending_sync=1` + audit `EDICION_MASIVA_METACAMPOS`; sin edición por fila.
  Las 4 claves salen de `MetacamposComicService.GRUPOS` (fuente única).
- HECHO (2026-10-23): pestaña EQUIVALENCIAS en Shopify -> CONFIG edita
  `metacampos_alias.json`: una fila por valor oficial (valores vivos vía
  `obtener_opciones`, agrupados por metacampo) con palabras por comas.
  Huérfanas en bloque "SIN EFECTO" preservadas tal cual. Validación y
  escritura en `ComparadorMetacamposService.guardar_alias`.
- Deuda: `crear_producto_ui.py` (1600+ líneas, refactor por partes); botón IR sin
  uso decidido; tests rotos, `openai` en requirements, docs desactualizados.
