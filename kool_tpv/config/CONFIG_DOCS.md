Guía fácil de configuración

Este documento explica, con lenguaje de niño de 12 años, qué hace cada bloque (cada { ... }) en los archivos dentro de `kool_tpv/config`.

Regla importante: los archivos originales son JSON y NO permiten comentarios. Este documento está fuera del JSON para que puedas leerlo sin romper nada.

1) `colors_config.json`
- ¿Qué es?: define colores para toda la app (fondos, textos, botones, menús).
- Cómo usarlo: cambia valores hex (`#RRGGBB`) para colorear cosas.
- Bloques principales:
  - `global`: colores que se usan en muchas partes (fondo general, texto, paleta de botones). Cambia `background` para cambiar el fondo de la app.
    - Ejemplo: `global.background: "#000000"` → fondo negro.
  - `main_menu`: colores para los botones del menú principal (cada entrada tiene `bg`, `hover`, `text`, `border`). Cambia `menu_clientes.text` para el color del texto del botón Clientes.
  - `<module>` (por ejemplo `clientes`, `almacen`, `tpv`): cada módulo tiene su propia paleta:
    - `primary`, `secondary`, `accent`: colores principales del módulo.
    - `text`: color por defecto para textos en ese módulo.
    - `background`, `bg_dark`, `bg_medium`: fondos usados en listas o tarjetas.
    - `description`: solo para humanos (explica el color).
    - `buttons`: define cómo se pintan los botones dentro del módulo. Por ejemplo `buttons.primary.bg` es el color de fondo del botón principal.
    - `nav_list`: colores de filas en tablas/listados (normal, hover, seleccionado).
  - `tpv` tiene bloques más pequeños como `grid_buttons` (cada botón del grid con `bg`, `hover`, `text`, `border`, `border_width`) y `ticket_carrito` (colores de header/body/footer del ticket).

  Qué cambiar si quieres algo concreto:
  - Cambiar el color de los botones grandes de clientes: `clientes.buttons.primary.bg`.
  - Cambiar el color del texto del ticket: `tpv.ticket_carrito.footer.text`.

2) `font_config.json`
- ¿Qué es?: le dice a la app qué fuente y tamaño usar.
- Bloques importantes:
  - `default.family` y `default.size`: fuente y tamaño por defecto.
  - `components.<element>.size|family`: controla fuentes para botones, títulos, entradas.
  - `scale.global_factor`: multiplica todos los tamaños (ej. 1.0 = normal, 1.2 = todo 20% más grande).

  Qué cambiar:
  - Si todo se ve pequeño, sube `scale.global_factor` a `1.1` o `1.2`.
  - Para aumentar solo botones, toca `components.action_button.size`.

3) `layout_config.json`
- ¿Qué es?: tamaños y espacios (anchos, alturas, márgenes) de la UI.
- Bloques importantes:
  - `global.window.width/height`: tamaño inicial de la ventana.
  - `global.spacing` (`xs`, `sm`, `md`, `lg`, `xl`): define separaciones entre elementos.
  - `components.action_button.width/height`: tamaño por defecto de botones.
  - `modules.<module>.ticket_carrito.width`: ancho del ticket en el TPV.

  Qué cambiar:
  - Para tickets más anchos, sube `modules.tpv.ticket_carrito.width`.
  - Para más espacio entre elementos, aumenta `global.spacing.md`.

4) `buttons_config.json` y `buttons_menu.json`
- ¿Qué son?: dicen qué botones aparecen y qué hacen.
- Bloques importantes:
  - `buttons` (lista): botones grandes del TPV; cada botón tiene `label`, `command`, `style`.
  - `main_menu`: botones laterales (texto, icono, comando, estilo).
  - En `buttons_menu.json` hay mapas por módulo con `title` y `buttons[]`.

  Qué cambiar:
  - Cambia `label` para que el botón muestre otro texto.
  - Cambia `command` solo si existe esa acción en el código (si pones un comando inexistente, el botón no hará nada).

5) `buttons_actions_config.json`
- ¿Qué es?: pequeñas plantillas para botones (texto y estilo).
- Bloques:
  - Cada entrada (ej. `guardar`) tiene `text` y `style`.
  - `style` se resuelve contra `colors_config.json` (ej. `components.action_buttons.primary`).

  Qué cambiar:
  - Cambia `text` si quieres otra etiqueta; cambia `style` para usar otra paleta.


Consejos rápidos y seguros (pasos a seguir):
- Antes de tocar: copia el archivo: `cp kool_tpv/config/colors_config.json colors_config.json.bak`.
- Cambia poco y prueba: modifica un color y reinicia la app para ver el resultado.
- Si el cambio no se ve, borra cachés o reinicia la app (muchas configs se cargan al inicio).
- Si quieres notas dentro del archivo, crea un archivo `colors_config.example.json` con explicaciones (no toques los JSON que usa el programa).

Si quieres, hago ahora un `colors_config.example.json` que incluya, justo antes de cada bloque, una línea de texto explicativa (pero en un archivo separado, porque el JSON real no admite comentarios). ¿Lo genero? (Responde sí/no)

*** Fin de la guía sencilla
