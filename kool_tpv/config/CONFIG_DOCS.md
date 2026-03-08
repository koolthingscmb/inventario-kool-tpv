# Documentación de configuración (keys editables)

Este archivo explica, en términos sencillos, qué claves puedes modificar en los archivos JSON dentro de `kool_tpv/config` y qué efecto tienen esos cambios.

Formato: los archivos son JSON (no admiten comentarios). Antes de editar haz copia de seguridad.

---

## layout_config.json
- `global.window.width`, `global.window.height`: tamaño por defecto de la ventana principal.
- `global.spacing`: separaciones globales (`xs`, `sm`, `md`, `lg`, `xl`) afectan paddings/margins en la UI.
- `components.action_button.width/height/corner_radius/border_width`: dimensiones por defecto de botones de acción.
- `modules.<module>.ticket_carrito.width`: ancho del ticket/carrito (ajusta visualización en el TPV).

Qué cambiar: para adaptar tamaños de botones o el ancho de tickets, edita las entradas de `components` o `modules` apropiadas.

## font_config.json
- `default.family`, `default.size`: fuente y tamaño por defecto usados cuando no hay override.
- `components.action_button.size` o `components.action_button.family`: fuente usada en botones de acción.
- `scale.global_factor`: factor global de escala que multiplica tamaños principales.

Qué cambiar: aumenta `default.size` o `scale.global_factor` para agrandar toda la UI. Cambia `components.*` para controlar elementos concretos.

## colors_config.json
- `global.background`, `global.text`: colores base de la app.
- `components.action_buttons.<style>.bg|text|hover|border`: paleta usada por `create_action_button`.
- `modules.<module>.primary/secondary/accent`: colores por módulo.

Qué cambiar: para temas, modifica `global` y/o `modules.<module>`; para cambiar estilo de botones ajusta `components.action_buttons`.

## buttons_config.json
- `buttons`: lista de botones principales del TPV (label, command, style). Cambiar `label` o `command` afectará la UI y la acción enlazada.
- `main_menu`: botones de la barra lateral; modifica `text`, `icon`, `command` o `style` para cambiar apariencia/acción.

Qué cambiar: ajusta texto/orden de botones o estilos (referenciando estilos en `buttons_actions_config.json` y `colors_config.json`).

## buttons_actions_config.json
- Cada entrada define `text`, `style` y opcionalmente `state` (`normal`/`disabled`).
- `style` es una llave que se resuelve contra `colors_config.json` (`components.action_buttons.<style>`).

Qué cambiar: cambia `text` para mostrar otra etiqueta; cambia `style` para aplicar otra paleta.

## buttons_menu.json
- Mapea menús por módulo: `modules.<module>.title` y `modules.<module>.buttons[]`.
- Cada botón dentro de `buttons` posee `text`, `action/command` y `style`.

Qué cambiar: para añadir o reorganizar botones del menú principal de un módulo, edita `buttons` (fíjate en `command` para que exista en la aplicación).

---

Buenas prácticas
- Haz backup antes de editar: `cp <file> <file>.bak`.
- Reinicia la aplicación después de cambiar JSONs (varias partes se cargan a inicio y quedan en caché).
- Para cambios no-destructivos, prueba en una rama Git y revisa visualmente.

Si quieres, puedo:
- Añadir comentarios más detallados por archivo (con ejemplos de valores).
- Generar archivos `*.example.json` con explicaciones dentro (si prefieres no tocar los originales).
