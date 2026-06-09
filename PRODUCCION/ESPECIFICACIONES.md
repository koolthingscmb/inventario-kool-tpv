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

CREATE TABLE produccion_ordenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER,
    notas TEXT
);

CREATE TABLE produccion_lineas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id INTEGER NOT NULL,
    diseno_codigo TEXT NOT NULL,
    tipo_producto TEXT,
    talla TEXT,
    cantidad INTEGER DEFAULT 1,
    FOREIGN KEY (orden_id) REFERENCES produccion_ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (diseno_codigo) REFERENCES disenos(codigo)
);
```

### Flujo UI (Producción Rápida):

1. **¿Qué producto?** → Botones: [Camiseta] [Taza] [Gorra]...
2. **¿Talla?** (si aplica) → [S] [M] [L] [XL]
3. **¿Qué diseño?** → Entry de búsqueda + lista resultados
4. **Doble clic** para seleccionar (puede añadir múltiples diseños)
5. **¿Cuántas unidades?** → Entry (Enter vacío = +1 automático)
6. **Resumen** → Lista de diseños añadidos
7. **Confirmar** → Persistencia en BD + stock TPV actualizado

### Características UX:
- Navegación 100% por teclado (Tab, Enter)
- Búsqueda predictiva en tiempo real
- Múltiples diseños por orden de producción
- Atajos: Enter sin cantidad = +1, Enter en resumen = confirmar

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

---

## 5. INTEGRACIÓN CON TPV EXISTENTE

- Al producir: stock del producto sube automáticamente
- Al entregar pedido: puede generar ticket TPV automático
- Diseños vinculados a productos TPV por código

---

## 6. INFORMES Y ESTADÍSTICAS

Desde `produccion_lineas`:
- Producción por día
- Producción por diseño (¿qué diseños más populares?)
- Producción por tipo de producto
- Costes de materiales (si se implementa tabla materiales)

---

## 7. PRÓXIMOS PASOS (Para futura sesión)

1. Crear migración SQL con nuevas tablas
2. Desarrollar UI de Producción Rápida
3. Desarrollar UI de Pedidos Personalizados
4. Integrar con stock TPV existente
5. Añadir alertas y notificaciones

---

**Nota:** Este documento es el resultado del brainstorming del 8 de Junio 2026. Prioridades a definir por el usuario antes de implementar.
