# Metaobjetos y metacampos de Kool Things — guía para la app de productos

La tienda usa **metaobjetos de Shopify** para clasificar productos. La app debe dejar de escribir metacampos de texto sueltos y escribir **referencias a entradas de metaobjeto** (GIDs `gid://shopify/Metaobject/<id>`).

## Dos tipos de metaobjeto

1. **Compartidos** (muchos productos apuntan a las mismas entradas: "DTG", "Seinen", "One Piece"). La app asigna el GID de la entrada existente; si no existe, la crea.
2. **Por producto** (`ficha_juego`): cada juego tiene SU propia entrada con sus números. La app crea una entrada por producto y la referencia.

## Metaobjetos (tipo → campos)

Clasificación compartida (todas con `nombre` + `icono`; enlaces opcionales):

| Tipo | Campos extra | Product metafield | Único/Lista |
|---|---|---|---|
| `demografia` | `coleccion` (ref colección) | `custom.demografia` | único |
| `genero_comic` | — | `custom.genero_comic` | **lista** |
| `subgenero_comic` | — | `custom.subgenero_comic` | **lista** |
| `contenido_adultos` | — | `custom.contenido_adultos` | **lista** |
| `tecnica` | `url` | `custom.tecnica_textil` | único |
| `composicion` | — | `custom.composicion_textil` | **lista** |
| `familia` | `coleccion` | `custom.familia` | único |
| `genero_textil` | `sufijo` (ej. `-mujer`) | `custom.genero_textil` | único |
| `sellos_kool` | `url` | `custom.sellos_kool` | **lista** |
| `mecanicas_juego_de_mesa` | `coleccion` | `custom.mecanicas_juegos_de_mesa` | **lista** |
| `tipo_juego` | `coleccion` | `custom.tipo_juego` | único |
| `tematica` (def "Temática Juegos") | `coleccion` | `custom.tematica` | **lista** |

Por producto:

| Tipo | Campos | Product metafield |
|---|---|---|
| `ficha_juego` | `jugadores`, `tiempo`, `edad` (texto), `fundas_gratis` (booleano), `ambientacion`, `concentracion`, `dificultad`, `azar` (enteros 0-10) | `custom.ficha_juego` (único, UNA entrada por juego) |

## Metacampos que SIGUEN siendo sueltos (escribir como antes)

`componentes` (rich text), `como_jugar` (texto largo), `reglamento` (archivo), `tutoriales` (lista textos), `tiene_tutorial`, `es_preventa`, `medidas_caja`, `ventajas` (lista textos), `avance_comic` (url), `coleccion_de_familia` (ref colección, pendiente de migrar a `familia`).

## Metacampos ELIMINADOS (no escribir)

`tecnica`, `composicion`, `gramaje`, `medidas`, `produccion`, `hecho_sin_ia`, `unico_en_el_mundo`, `jugadores`, `tiempo`, `edad`, `nivel_dificultad`, `nivel_concentracion`, `nivel_ambientacion`, `incluye_fundas`, `preventa_condiciones`.

## Colecciones

- `custom.navegacion_tipo` (texto): tipo de metaobjeto a mostrar en la fila de chips (`demografia`, `familia`, `tipo_juego`, `tematica`, `mecanicas_juegos_de_mesa`, o `ninguna` = ocultar). Vacío = demografía.
- `custom.navegacion_padre` (ref colección): chip de "volver".

## Cómo escribir referencias (GraphQL Admin API)

**1) Resolver GID de una entrada por nombre** (buscar en `shop.metaobjects.<tipo>.values` o query `metaobjects`):

```graphql
{ metaobjects(type: "tecnica", first: 50) { edges { node { id handle fields { key value } } } } }
```

**2) Asignar metacampo único:**

```graphql
metafieldsSet(metafields: [{
  ownerId: "gid://shopify/Product/<id>",
  namespace: "custom", key: "tecnica_textil",
  type: "metaobject_reference",
  value: "gid://shopify/Metaobject/<gid_entrada>"
}])
```

**3) Asignar metacampo lista** (JSON array de GIDs):

```graphql
metafieldsSet(metafields: [{
  ownerId: "gid://shopify/Product/<id>",
  namespace: "custom", key: "tematica",
  type: "list.metaobject_reference",
  value: "[\"gid://shopify/Metaobject/<g1>\",\"gid://shopify/Metaobject/<g2>\"]"
}])
```

**4) `ficha_juego` (por producto):** crear la entrada con `metaobjectCreate` y luego asignarla:

```graphql
metaobjectCreate(metaobject: {
  type: "ficha_juego",
  fields: [
    { key: "jugadores", value: "2-4" },
    { key: "tiempo", value: "45 min" },
    { key: "edad", value: "8+" },
    { key: "fundas_gratis", value: "true" },
    { key: "dificultad", value: "6" },
    { key: "concentracion", value: "8" },
    { key: "ambientacion", value: "7" },
    { key: "azar", value: "2" }
  ]
}) { metaobject { id } }
```

Luego `metafieldsSet` con `key: "ficha_juego"`, `type: "metaobject_reference"`, `value: <gid devuelto>`.

## Notas

- Verificar los `type` reales con `metaobjectDefinitions` (la app tiene sus propios permisos).
- En metacampos lista, escribir el array COMPLETO (sobreescribe; no es append).
- Campo `sufijo` de `genero_textil` enlaza variantes del mismo producto por handle (`producto-hombre`, `producto-mujer`, `producto-infantil`): los handles de las variantes de género deben terminar así.
