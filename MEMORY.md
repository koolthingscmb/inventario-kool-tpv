# MEMORY.md — Kool TPV
Memoria entre sesiones. Actualización: 2026-10-24, rama `windows-beta`. Máximo ~50 líneas.

## Editoriales y fuentes — subido en `cfe6cdb`
- UI 50/50: editorial arriba (ID, nombre, WEB, principal/reserva con buscador); fuente abajo
  (ID, nombre, plataforma, URL, credenciales). Chips y CRUD independientes; NUEVA limpia ambas zonas.
- WEB de editorial solo sirve para IR; URL de fuente sirve para OBTENER. No confundirlas.
- Seleccionar editorial carga su fuente; chip de fuente desactiva editorial. Seleccionar no guarda.
- Fuentes sin editoriales se conservan; editar una usada avisa de afectados; borrar una usada se bloquea.
- PLATAFORMA se mantiene por ahora: selecciona el adaptador de consulta de `TIPOS_FUENTE`.
  Fuente = configuración local; adaptador = código. Una URL nueva no crea un adaptador.
- Mac y Windows tienen configuraciones independientes en BD: `git pull` no copia fuentes ni accesos.
  En Windows faltaba UDL y había dos Norma (causa del duplicado no comprobada).
- Usuario confirmó conversión de una ficha de Windows a UDL (`udl_web`); avisó de Astiberri/Penguin
  afectados y después indicó que estaba hecho. Sin lectura independiente ni prueba OBTENER posterior.
- No ocultar PLATAFORMA sin acordar cómo se elegirá el adaptador al crear/editar fuentes.
- Verificado: compilación, CRUD/validaciones en SQLite en memoria y estructura UI. Prueba Windows
  por usuario; no dar por verificadas todas las conexiones ni todos los flujos de borrado.

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
- Rebaja ficha (migr. 069, subido `9c4e224`): `shopify_rebaja_activa`/`shopify_descuento_porcentaje`
  en productos; % en centésimas, NULL = sin configurar (manga/cómic -> 5 % inicial). UPDATE con
  COALESCE: otros flujos no pisan los campos. `price`=final, `compareAtPrice`=base o null.
  `es_comic_o_manga` por nombre de tipo/categoría. Verificado por usuario con subida real.
- Label estado web en la fila de rebaja (subido `e572daa`, verificado por usuario): `estado_subida`
  devuelve `ultima_sincronizacion`; UI pinta EN LA WEB + fecha, NO SUBIDO A LA WEB o CAMBIOS PENDIENTES.
  Refresco al abrir (cargar_producto), al guardar y tras subir. No llamadas a Shopify.
- SEO IA (subido `5c42d10`): 429 insufficient_quota de OpenAI se traduce a "La IA no tiene saldo..."
  en openai_service.generate_json; SeoFichaService deja toda falla del GENERAR SEO en
  shopify_sync_log con accion SEO_IA (la ficha pasa producto_id en datos). Causa real del
  fallo de nov-2026: cuenta OpenAI sin créditos, no bug de código.
- IA multiproveedor (subido `5c42d10`): OpenAIService habla OpenAI y Gemini (endpoint compatible
  /v1beta/openai/); desde_config(cfg) decide proveedor/llaves/modelo. Modelo por defecto Gemini
  cambiado a `gemini-3.6-flash` (3.8-flash sufre sobrecarga HTTP 503 en Google).
  Varias API keys de Gemini: campos individuales A-E en el chip GEMINI (se persisten
  juntas como una por línea en `shopify_ia_gemini_api_keys`). Rotación equitativa round-robin
  entre peticiones (A -> B -> C -> A) y fallback automático a la siguiente si la que toca
  falla o agota cuota. La letra usada sale en el toast de GENERAR SEO ("Gemini [A]") y en el
  log de sync.
  CONFIG IA con chips CHATGPT/GEMINI/GOOGLE BOOKS, patrón copiado de IA PROMPTS
  (paleta por parámetros, ButtonFactory, volcado a memoria al cambiar de chip). Cada
  proveedor guarda su modelo (`ia_model_openai`/`ia_model_gemini`); USAR ESTA IA marca el
  activo (ia_proveedor + ia_model al guardar). PROBAR CONEXIÓN prueba el chip visible.
  Sin migración: solo filas clave-valor en `configuracion`. producto_content_service
  también respeta el proveedor. temperature fuera en gemini.
  SEO con IA: toast informativo con la IA en uso ("Generando SEO con Gemini (gemini-3.6-flash)..."),
  callback UI protegido contra destrucción de ventana y registro de éxito/fallo en
  `shopify_sync_log` (acción `SEO_IA`) visible en Shopify -> SINC -> Logs.

## Metaobjetos Shopify (`kool_tpv/METAOBJETOS-API.md`)
- METACAMPOS admite `metaobject_reference` único: botón "SELECCIONAR <tipo>" con selector de una
  opción (reutiliza `show_reference_select_dialog`); nombre resuelto en hilo; GID directo al guardar.
- Masiva admite únicos: `TIPOS_METAOBJETO_UNICO` aparte (no mezclado con listas); va por el camino
  escalar de `metafieldsSet` (value=GID suelto). Listas de metaobjetos ya iban antes.
- Secciones de METACAMPOS repartidas en 2 columnas (izquierda/derecha alternando); dentro de cada
  una los campos fluyen como antes.
- Stock sync es GENÉRICO por `productos` + `shopify_product_mapping` (lo crea la ficha de almacén).
  NUEVO guarda `shopify_diseno_mapping` (ruta producción por SKU) -> no da sync de stock de producto.
- `ficha_juego` (metaobjeto por producto) HECHO: `ShopifyMetafieldsService.crear_metaobjeto/
  actualizar_metaobjeto/obtener_campos_definicion_metaobjeto` (lee fieldDefinitions en vivo).
  Diálogo reusable `utils/dialogs/ficha_juego_dialog.py` (BaseDialog; botones vacíos en la base ->
  las subclases implementan _on_accept/_on_cancel). Campos reales: jugadores/tiempo/edad/fundas_gratis/
  ambientacion/concentracion/dificultad/azar. Subida: _preparar_ficha_juego crea o actualiza y pone el
  GID en custom.ficha_juego. OBTENER autorellena jugadores/edad/tiempo en tipos 'juego' (no pisar lo
  puesto). Verificado por usuario.
- Fuentes juegos: `sdgames_web` (playsdgames.com, pública por nombre, verifica_isbn=False, probada) y
  `devir_web` (b2bdevir.es, login Magento+form_key, busca por EAN, atributos 'Más información' ->
  jugadores min-max/edad/duracion, probada). Asmodee PENDIENTE: asmodee.es bloquea bots (Akamai 403);
  salida = b2b.asmodee.es con credenciales o navegador real.
- `metacampos_grupo` por tipo (migr. 070 + relleno única vez 071, marca `mig071_metacampos_grupo`):
  'comic'/'juego'/NULL en `tipos`; lo decide CONFIG->TIPOS (selector METACAMPOS NINGUNO/CÓMIC/JUEGO).
  Ficha de almacén muestra los 4 grupos del tipo (comic: demografia..contenido; juego: tematica,
  tipo_juego unico, mecanicas_juegos_de_mesa, sellos_kool). MetacamposComicService.GRUPOS_JUEGO y
  ShopifyFichaService.METACAMPOS_PROPIOS cubren las 8 claves. Verificado por usuario.

## Reglas y fuentes OBTENER
- Mac = BD de pruebas; Windows = tienda. Enlaces Shopify locales: subir en Mac no enlaza Windows.
  Sync Windows e impresión térmica de vales comprobados por usuario.
- Stock: todo cambio normal por `StockMovementService.aplicar_movimiento` dentro de transacción:
  UPDATE + movimiento + cola; rollback conjunto. Tras confirmar `procesar_pendientes_async()`.
  Albaranes encolan una vez por producto al final; cola serial durable con reintento manual.
- Vales = pago, no descuento; consumo atómico. OBTENER: géneros a METACAMPOS, no TAGS; nunca PVP.
- Fuentes vivas: `almacen/services/fuentes/`, registro por plataforma; principal y luego reserva.
  `shopify_publico` (Milky Way, `501f7e7`): `suggest.json` ya trae ficha completa (sinopsis, tags,
  portada); la página del producto es extra opcional tolerante a 429 (avance/ISBN/metacampos).
- Pendiente aprobado para futuro: usar Azeta como principal de la editorial Milky Way (datos base)
  y milkyway_web solo para extras (avance/metacampos). Hoy reserva solo se usa si principal falla;
  haría falta un paso de fusión. Sin comprobar aún si Azeta lleva el catálogo de Milky Way.
  LINK multi `url (etiqueta); url2 (etiqueta2)`; avance_comic solo con etiqueta Avance.
- Astiberri por EAN verificado/subido (`b7a8ccf`): /search XHR, verifica ISBN de ficha; reserva por título/slugs.
  /search tiene Disallow en robots.txt; uso aprobado por usuario. No prometer ausencia de bloqueos o riesgo legal.
- Sin adaptador propio, configurar Azeta (Penguin, Kibook y otros); no reinvestigar sin petición.
- Portadas locales gitignored; máxima calidad variable: Astiberri ~2400px, Ivrea 400, Planeta 300, Norma 229.
- Fragilidad: Panini Queue-it, Azeta reCAPTCHA, Ivrea límites AJAX (usa sitemap). Credenciales nunca en logs/chat.

## Deuda conocida
- crear_producto_ui grande; tests de base no verdes; openai sin usar; documentación antigua. No corregir sin permiso.
