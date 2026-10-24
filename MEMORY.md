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
- Rebaja ficha (migr. 069, sin commit): `shopify_rebaja_activa`/`shopify_descuento_porcentaje` en
  productos; % en centésimas, NULL = sin configurar (manga/cómic -> 5 % inicial). UPDATE con COALESCE:
  otros flujos (menú/albarán/TPV) no pisan los campos. `price`=final, `compareAtPrice`=base o null.
  `es_comic_o_manga` por nombre de tipo/categoría. Simulado OK; falta prueba real en Shopify.

## Reglas y fuentes OBTENER
- Mac = BD de pruebas; Windows = tienda. Enlaces Shopify locales: subir en Mac no enlaza Windows.
  Sync Windows e impresión térmica de vales comprobados por usuario.
- Stock: todo cambio normal por `StockMovementService.aplicar_movimiento` dentro de transacción:
  UPDATE + movimiento + cola; rollback conjunto. Tras confirmar `procesar_pendientes_async()`.
  Albaranes encolan una vez por producto al final; cola serial durable con reintento manual.
- Vales = pago, no descuento; consumo atómico. OBTENER: géneros a METACAMPOS, no TAGS; nunca PVP.
- Fuentes vivas: `almacen/services/fuentes/`, registro por plataforma; principal y luego reserva.
  `shopify_publico` (Milky Way): SOLO `suggest.json` trae ficha completa (sinopsis, tags, portada);
  la página del producto es extra opcional tolerante a 429 (avance/ISBN/metacampos).
  LINK multi `url (etiqueta); url2 (etiqueta2)`; avance_comic solo con etiqueta Avance.
- Astiberri por EAN verificado/subido (`b7a8ccf`): /search XHR, verifica ISBN de ficha; reserva por título/slugs.
  /search tiene Disallow en robots.txt; uso aprobado por usuario. No prometer ausencia de bloqueos o riesgo legal.
- Sin adaptador propio, configurar Azeta (Penguin, Kibook y otros); no reinvestigar sin petición.
- Portadas locales gitignored; máxima calidad variable: Astiberri ~2400px, Ivrea 400, Planeta 300, Norma 229.
- Fragilidad: Panini Queue-it, Azeta reCAPTCHA, Ivrea límites AJAX (usa sitemap). Credenciales nunca en logs/chat.

## Deuda conocida
- crear_producto_ui grande; tests de base no verdes; openai sin usar; documentación antigua. No corregir sin permiso.
