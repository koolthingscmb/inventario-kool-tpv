# Especificaciones Módulo Producción

**Fecha:** Junio 2026
**Contexto:** App TPV Kool Things - Producción propia de merchandise

---

## 1. CONTEXTO DEL NEGOCIO

- **Equipo:** Propietario + Andrea (2 personas)
- **Productos:** Camisetas, tazas, gorras, libretas, posters, carteras...
- **Diseños:** Cientos organizados por colecciones (DB, OP, SW, Anime...)
- **Nomenclatura:** `op_wanted_4B` = One Piece, Wanted, 4 colores, base Negra
- **Problema:** No se pueden poner códigos de barras en todas las prendas

---

## 2. DECISIONES TÉCNICAS

### Base de Datos: **UNA SOLA BD**

Ventajas:
- Stock se actualiza automáticamente al producir
- Informes cruzados (costes vs ventas)
- Un único backup
- Integridad total entre módulos

**NO usar dos BD** para evitar sincronización manual.

---

## 3. MÓDULO A: PRODUCCIÓN (Stock Interno)

### Tablas:

```sql
CREATE TABLE disenos (
    codigo TEXT PRIMARY KEY,      -- ej: op_wanted_4B
    coleccion TEXT NOT NULL,      -- ej: OP, DB, SW
    nombre TEXT NOT NULL,         -- ej: Wanted
    variante TEXT,                -- parseado del sufijo
    tipo_producto TEXT,           -- camiseta, taza, gorra...
    imagen_path TEXT,
    activo INTEGER DEFAULT 1
);

CREATE TABLE colores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,  -- ej: Negro, Blanco, Rojo
    codigo_hex TEXT               -- opcional para UI
);

CREATE TABLE stock_colores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diseno_codigo TEXT NOT NULL,
    color_id INTEGER NOT NULL,
    cantidad INTEGER DEFAULT 0,
    FOREIGN KEY (diseno_codigo) REFERENCES disenos(codigo),
    FOREIGN KEY (color_id) REFERENCES colores(id),
    UNIQUE(diseno_codigo, color_id)
);

CREATE TABLE produccion_estados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,  -- ej: maquinaria_encendida_2_usuarios
    tiempo_base_minutos INTEGER NOT NULL,
    descripcion TEXT
);

CREATE TABLE produccion_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estado_actual_id INTEGER NOT NULL,
    usuarios_activos INTEGER DEFAULT 2,
    plancha_encendida INTEGER DEFAULT 1,
    FOREIGN KEY (estado_actual_id) REFERENCES produccion_estados(id)
);

CREATE TABLE produccion_ordenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER,
    notas TEXT,
    tiempo_estimado_minutos INTEGER,  -- calculado automáticamente
    estado TEXT DEFAULT 'PENDIENTE'   -- PENDIENTE, EN_PRODUCCION, COMPLETADO
);

CREATE TABLE produccion_lineas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id INTEGER NOT NULL,
    diseno_codigo TEXT NOT NULL,
    tipo_producto TEXT,
    talla TEXT,
    color_id INTEGER,
    cantidad INTEGER DEFAULT 1,
    produccion_mixta INTEGER DEFAULT 0,  -- 0 = normal, 1 = delante y detrás
    FOREIGN KEY (orden_id) REFERENCES produccion_ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (diseno_codigo) REFERENCES disenos(codigo),
    FOREIGN KEY (color_id) REFERENCES colores(id)
);
```

### Flujo UI (Producción Rápida):

1. **¿Qué producto?** → Botones: [Camiseta] [Taza] [Gorra]...
2. **¿Talla?** (si aplica) → [S] [M] [L] [XL]
3. **¿Color?** → Botones/Chips de colores disponibles
4. **¿Qué diseño?** → Entry de búsqueda + lista resultados
5. **Doble clic** para seleccionar (puede añadir múltiples diseños)
6. **¿Cuántas unidades?** → Entry (Enter vacío = +1 automático)
7. **¿Producción mixta?** (delante y detrás) → Checkbox (solo camisetas)
8. **Resumen** → Lista de diseños añadidos + tiempo estimado
9. **Confirmar** → Persistencia en BD + stock TPV actualizado

### Características UX:
- Navegación 100% por teclado (Tab, Enter)
- Búsqueda predictiva en tiempo real
- Múltiples diseños por orden de producción
- Atajos: Enter sin cantidad = +1, Enter en resumen = confirmar

---

### Cálculo de Tiempo de Entrega (Cola de Producción)

**Algoritmo de cálculo:**
```
tiempo_total = tiempo_base_estado + (ordenes_anteriores * tiempo_por_unidad) + modificadores_extra
```

**Configuración de estados (tiempo_base):**
- `maquinaria_encendida_2_usuarios`: 15 min
- `un_usuario_o_plancha_apagada`: 30 min
- `produccion_mixta` (delante y detrás): +15 min adicional

**Modificadores:**
- Número de órdenes pendientes antes del pedido actual
- Tipo de producto (camiseta = más tiempo, taza = menos tiempo)
- Producción mixta (solo camisetas)

**Información al cliente:**
- "Hay X camisetas antes de la suya"
- "Tiempo estimado de recogida: Y minutos"
- Cálculo automático basado en cola y estado actual

**UI de configuración de estado:**
- Selector de estado actual (maquinaria encendida/apagada, usuarios activos)
- Actualización en tiempo real de tiempos estimados

---

## 4. MÓDULO B: PEDIDOS PERSONALIZADOS (Encargos)

**Escenario:** Cliente pide camiseta, se prepara en 30 min, viene a recogerla.

### Estados:
```
PENDIENTE → EN_PRODUCCION → LISTO_PARA_RECOGER → ENTREGADO
    ↓           ↓
CANCELADO   PAUSADO
```

### Tabla:

```sql
CREATE TABLE pedidos_personalizados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nombre TEXT,
    cliente_telefono TEXT,
    fecha_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega_estimada DATETIME,
    
    diseno_codigo TEXT,
    tipo_producto TEXT,
    talla TEXT,
    cantidad INTEGER DEFAULT 1,
    notas TEXT,
    
    estado TEXT DEFAULT 'PENDIENTE',
    pago_estado TEXT DEFAULT 'PENDIENTE',
    
    produccion_orden_id INTEGER,  -- Vincula a Módulo A
    ticket_id INTEGER,            -- Vincula a TPV cuando se entrega
    
    FOREIGN KEY (diseno_codigo) REFERENCES disenos(codigo),
    FOREIGN KEY (produccion_orden_id) REFERENCES produccion_ordenes(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
```

### Alertas:
- Tardanza: >45 min en EN_PRODUCCION
- No recogido: >24h en LISTO_PARA_RECOGER
- Lista visible de pedidos ordenados por urgencia

### Impresión de Ticket
Al finalizar la introducción de datos del pedido personalizado:
- Generar ticket automáticamente
- Imprimir 2 copias:
  - 1 para el cliente (con fecha, hora, descripción del pedido, tiempo estimado)
  - 1 para nosotros (control interno)
- Integración con sistema de impresión existente del TPV

---

## 5. INTEGRACIÓN CON TPV EXISTENTE

- Al producir: stock del producto sube automáticamente
- Al entregar pedido: puede generar ticket TPV automático
- Diseños vinculados a productos TPV por código

### Sistema de Avisos de Diseños Vendidos

**Contexto:** Al vender un producto fabricado por nosotros, el sistema debe permitir registrar qué diseño específico se vendió para estadísticas.

**Flujo:**
1. Al vender un producto en el TPV, el sistema detecta si es "fabricado_por_nosotros"
2. Aparece un **Toast/Notificación persistente** en una esquina de la pantalla
3. El Toast muestra: "Asignar diseño: [Tipo de producto] vendido"
4. Al pulsar el Toast, se abre una **subvista de asignación de diseño**
5. En la subvista:
   - Entry de búsqueda para escribir código de diseño (ej: 'naru_itac')
   - Lista de resultados filtrada en tiempo real
   - Doble clic para seleccionar diseño
6. Al seleccionar:
   - Se registra la venta en la tabla `disenos_ventas`
   - Se actualiza contador de ventas del diseño
   - El Toast desaparece
7. Si se cierra sin asignar, el Toast permanece visible hasta asignar o descartar

**Nueva tabla:**
```sql
CREATE TABLE disenos_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diseno_codigo TEXT NOT NULL,
    producto_id INTEGER NOT NULL,  -- ID del producto TPV vendido
    ticket_id INTEGER NOT NULL,
    fecha_venta DATETIME DEFAULT CURRENT_TIMESTAMP,
    cantidad INTEGER DEFAULT 1,
    FOREIGN KEY (diseno_codigo) REFERENCES disenos(codigo),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);
```

**UX del Toast:**
- Posición: Esquina inferior derecha
- Persistente hasta acción del usuario
- Botón: "Asignar" para abrir subvista
- Botón: "Descartar" para cerrar sin asignar
- Contador: "X avisos pendientes" si hay múltiples

---

## 6. INFORMES Y ESTADÍSTICAS

Desde `produccion_lineas`:
- Producción por día
- Producción por diseño (¿qué diseños más populares?)
- Producción por tipo de producto
- Costes de materiales (si se implementa tabla materiales)

Desde `disenos_ventas`:
- Ventas por diseño (diseños más vendidos)
- Ventas por colección
- Ventas por tipo de producto

---

## 7. PRÓXIMOS PASOS (Para futura sesión)

1. Crear migración SQL con nuevas tablas (colores, stock_colores, produccion_estados, produccion_config, disenos_ventas)
2. Desarrollar UI de Producción Rápida (con selección de color y producción mixta)
3. Implementar sistema de cálculo de tiempo de entrega (cola de producción)
4. Desarrollar UI de configuración de estado de producción
5. Desarrollar UI de Pedidos Personalizados
6. Implementar impresión de tickets para pedidos personalizados
7. Integrar con stock TPV existente
8. Desarrollar sistema de Toasts/Notificaciones para asignación de diseños vendidos
9. Desarrollar subvista de asignación de diseño post-venta
10. Añadir alertas y notificaciones (tardanza, no recogido)
11. Implementar informes de ventas por diseño

---

**Nota:** Este documento es el resultado del brainstorming del 8 de Junio 2026. Prioridades a definir por el usuario antes de implementar.
