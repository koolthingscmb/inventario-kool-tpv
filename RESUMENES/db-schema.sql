CREATE TABLE codigos_barras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            ean TEXT NOT NULL,
            FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
        );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                que_vende TEXT,
                nif_cif TEXT,
                iva_intracom TEXT,
                dir_fiscal TEXT,
                dir_envio TEXT,
                email TEXT,
                telefono TEXT,
                forma_pago TEXT,
                persona_comercial TEXT,
                telefono_comercial TEXT,
                email_comercial TEXT,
                web TEXT,
                notas TEXT
            , mapeo_csv TEXT);
CREATE TABLE configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        );
CREATE TABLE niveles_fidelidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER NOT NULL UNIQUE,
            nombre_nivel TEXT NOT NULL,
            grafismo_nivel TEXT,
            gasto_minimo REAL NOT NULL DEFAULT 0.0
        , tipo_recompensa TEXT, detalle_recompensa TEXT, producto_sku TEXT);
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    password TEXT NOT NULL,
    rol TEXT NOT NULL,
    permiso_cierre INTEGER DEFAULT 0,
    permiso_descuento INTEGER DEFAULT 0,
    permiso_devolucion INTEGER DEFAULT 0,
    permiso_tickets INTEGER DEFAULT 0
, created_at TEXT, telefono TEXT, email TEXT);
CREATE TABLE payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  metodo TEXT,
  importe REAL NOT NULL,        -- positivo si cliente paga, negativo si tienda devuelve
  referencia TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(ticket_id) REFERENCES "tickets_backup"(id) ON DELETE CASCADE
);
CREATE TABLE stock_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  producto_id INTEGER NOT NULL,
  cantidad INTEGER NOT NULL,    -- positivo = entrada (devolución), negativo = salida (venta)
  motivo TEXT,
  ticket_line_id INTEGER,       -- referencia a ticket_lines.id (si aplica)
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(producto_id) REFERENCES productos(id),
  FOREIGN KEY(ticket_line_id) REFERENCES ticket_lines(id)
);
CREATE TABLE points_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cliente_id INTEGER NOT NULL,
  puntos REAL NOT NULL,         -- positivo/negativo
  motivo TEXT,
  ticket_id INTEGER,            -- referencia opcional al ticket
  usuario_id INTEGER,           -- usuario que aplicó el movimiento
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(cliente_id) REFERENCES "clientes_old"(id),
  FOREIGN KEY(ticket_id) REFERENCES "tickets_backup"(id)
);
CREATE TABLE audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entidad TEXT,
  entidad_id INTEGER,
  accion TEXT,
  usuario_id INTEGER,
  datos_previos TEXT,
  datos_nuevos TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "cierres_caja" (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cierre_num INTEGER,
  fecha_hora TIMESTAMP,
  cajero TEXT,
  total_ingresos REAL,
  num_ventas INTEGER,
  rango_inicio_ticket INTEGER,
  rango_fin_ticket INTEGER,
  total_efectivo REAL DEFAULT 0.0,
  total_tarjeta REAL DEFAULT 0.0,
  total_web REAL DEFAULT 0.0,
  total_devoluciones REAL DEFAULT 0.0,
  total_descuentos REAL DEFAULT 0.0,
  tesoro_ganado REAL DEFAULT 0.0,
  tesoro_gastado REAL DEFAULT 0.0,
  tesoro_total_ganado REAL DEFAULT 0.0,
  tesoro_total_gastado REAL DEFAULT 0.0,
  cierre_text TEXT,
  usuario_id INTEGER
, total_base_imponible REAL DEFAULT 0.0, total_iva REAL DEFAULT 0.0, base_21 REAL DEFAULT 0.0, iva_21 REAL DEFAULT 0.0, base_4 REAL DEFAULT 0.0, iva_4 REAL DEFAULT 0.0, iva_desglose TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS "ticket_lines" (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  sku TEXT,
  nombre TEXT,
  cantidad REAL,
  precio REAL,
  iva REAL,
  line_tipo TEXT DEFAULT 'venta',
  producto_id INTEGER,
  FOREIGN KEY(ticket_id) REFERENCES "tickets_backup"(id) ON DELETE CASCADE,
  FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
);
CREATE INDEX idx_payments_ticket ON payments(ticket_id);
CREATE INDEX idx_stock_mov_producto ON stock_movements(producto_id);
CREATE INDEX idx_points_mov_cliente ON points_movements(cliente_id);
CREATE INDEX idx_audit_entidad ON audit_logs(entidad, entidad_id);
CREATE INDEX idx_cierres_cierre_num ON cierres_caja(cierre_num);
CREATE INDEX idx_cierres_fecha_hora ON cierres_caja(fecha_hora);
CREATE INDEX idx_ticket_lines_ticket ON ticket_lines(ticket_id);
CREATE TABLE IF NOT EXISTS "categorias" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"nombre" TEXT UNIQUE,
	"descripcion" TEXT,
	"created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
	"updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
	"shopify_taxonomy" TEXT,
	"fide_porcentaje" REAL
);
CREATE TABLE IF NOT EXISTS "tipos" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"nombre" TEXT UNIQUE,
	"descripcion" TEXT,
	"created_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
	"updated_at" DATETIME DEFAULT CURRENT_TIMESTAMP,
	"shopify_taxonomy" TEXT,
	"fide_porcentaje" REAL
);
CREATE TABLE IF NOT EXISTS "precios" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"producto_id" INTEGER,
	"pvp" REAL DEFAULT 0.0,
	"coste" REAL DEFAULT 0.0,
	"fecha_registro" DATETIME DEFAULT CURRENT_TIMESTAMP,
	"activo" INTEGER DEFAULT 1,
	FOREIGN KEY("producto_id") REFERENCES "productos"("id") ON DELETE CASCADE
);
CREATE INDEX "idx_precios_activo" ON "precios" ("producto_id", "activo");
CREATE TABLE albaranes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_albaran INTEGER UNIQUE,
    proveedor_id INTEGER,
    fecha DATE,
    total_neto REAL DEFAULT 0.0,
    total_iva_4 REAL DEFAULT 0.0,
    total_iva_10 REAL DEFAULT 0.0,
    total_iva_21 REAL DEFAULT 0.0,
    total REAL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, tipo TEXT NOT NULL DEFAULT 'ENTRADA',
    FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
);
CREATE TABLE albaran_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    albaran_id INTEGER,
    producto_id INTEGER,
    ean TEXT,
    nombre TEXT,
    cantidad INTEGER,
    coste REAL,
    descuento REAL DEFAULT 0.0,
    importe REAL,
    tipo_iva INTEGER DEFAULT 21,
    editorial TEXT,
    fabricante TEXT,
    pvpr_cents INTEGER DEFAULT 0,
    FOREIGN KEY(albaran_id) REFERENCES albaranes(id) ON DELETE CASCADE,
    FOREIGN KEY(producto_id) REFERENCES productos(id)
);
CREATE TABLE IF NOT EXISTS "clientes" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    telefono TEXT,
    email TEXT,
    dni TEXT,
    direccion TEXT,
    ciudad TEXT,
    cp TEXT,
    pais TEXT,
    fecha_nacimiento DATE,
    tags TEXT,
    notes_internas TEXT,
    tesoro_total REAL DEFAULT 0.0,
    tesoro_gastado_total REAL DEFAULT 0.0,
    tesoro_historico REAL DEFAULT 0.0,
    id_nivel INTEGER,
    fidelidad_activa INTEGER DEFAULT 1,
    fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento_tesoro DATE,
    fecha_ultima_compra DATETIME,   -- AQUÍ EL CAMBIO
    total_compras INTEGER DEFAULT 0,
    total_compras_euros REAL DEFAULT 0.0,
    total_unidades INTEGER DEFAULT 0,
    fecha_ultima_comunicacion DATETIME
);
CREATE TABLE IF NOT EXISTS "tickets" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cajero TEXT,
    cliente TEXT,
    cliente_id INTEGER,
    num_ticket TEXT,
    forma_pago TEXT,
    total REAL NOT NULL,
    pagado REAL,
    cambio REAL,
    importe_efectivo REAL DEFAULT 0.0,
    importe_tarjeta REAL DEFAULT 0.0,
    descuento_euros REAL,
    descuento_tipo TEXT,
    descuento_valor REAL,
    cierre_id INTEGER,
    tesoro_ganado REAL DEFAULT 0,
    tesoro_gastado REAL DEFAULT 0,
    tesoro_total_ticket REAL DEFAULT 0,
    ticket_text TEXT,
    usuario_id INTEGER,
    num_ventas INTEGER DEFAULT 0,
    subtotal REAL DEFAULT 0.0
, iva_desglose TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS "productos" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nombre_boton TEXT,
    sku TEXT NOT NULL UNIQUE,
    categoria INTEGER NOT NULL,
    tipo INTEGER NOT NULL,
    proveedor_id INTEGER,
    tipo_iva INTEGER DEFAULT 0,
    stock_actual INTEGER DEFAULT 0 NOT NULL,
    stock_minimo INTEGER DEFAULT 0,
    ventas_totales INTEGER DEFAULT 0,
    pvp_variable INTEGER DEFAULT 0,
    descripcion_shopify TEXT,
    notas_internas TEXT,
    titulo TEXT,
    activo INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    pending_sync INTEGER DEFAULT 0,
    seo_title TEXT,
    seo_description TEXT,
    tipo_shop TEXT,
    etiquetas TEXT,
    shop_link TEXT,
    shopify_taxonomy TEXT,
    fidelizacion_tipo TEXT DEFAULT 'porcentaje',
    fidelizacion_valor REAL DEFAULT 0.0,
    FOREIGN KEY (categoria) REFERENCES categorias(id) ON DELETE RESTRICT,
    FOREIGN KEY (tipo) REFERENCES tipos(id) ON DELETE RESTRICT,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);
CREATE TRIGGER audit_productos_update
AFTER UPDATE ON productos
FOR EACH ROW
WHEN OLD.stock_actual != NEW.stock_actual 
  OR OLD.activo != NEW.activo
  OR OLD.fidelizacion_tipo != NEW.fidelizacion_tipo
  OR OLD.fidelizacion_valor != NEW.fidelizacion_valor
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos, datos_nuevos)
  VALUES (
    'productos',
    NEW.id,
    'UPDATE',
    json_object('sku', OLD.sku, 'stock', OLD.stock_actual, 'activo', OLD.activo, 'fide_tipo', OLD.fidelizacion_tipo, 'fide_valor', OLD.fidelizacion_valor),
    json_object('sku', NEW.sku, 'stock', NEW.stock_actual, 'activo', NEW.activo, 'fide_tipo', NEW.fidelizacion_tipo, 'fide_valor', NEW.fidelizacion_valor)
  );
END;
CREATE TRIGGER audit_productos_delete
AFTER DELETE ON productos
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos, datos_nuevos)
  VALUES (
    'productos',
    OLD.id,
    'DELETE',
    json_object('sku', OLD.sku, 'nombre', OLD.nombre, 'stock', OLD.stock_actual),
    NULL
  );
END;
CREATE TRIGGER audit_tickets_insert
AFTER INSERT ON tickets
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, usuario_id, datos_nuevos)
  VALUES (
    'tickets',
    NEW.id,
    'INSERT',
    NEW.usuario_id,
    json_object('num_ticket', NEW.num_ticket, 'total', NEW.total, 'cliente_id', NEW.cliente_id)
  );
END;
CREATE TRIGGER audit_tickets_delete
AFTER DELETE ON tickets
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos)
  VALUES (
    'tickets',
    OLD.id,
    'DELETE',
    json_object('num_ticket', OLD.num_ticket, 'total', OLD.total, 'fecha', OLD.fecha)
  );
END;
CREATE TRIGGER audit_clientes_update
AFTER UPDATE ON clientes
FOR EACH ROW
WHEN OLD.tesoro_total != NEW.tesoro_total OR OLD.nivel_fidelidad != NEW.nivel_fidelidad
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos, datos_nuevos)
  VALUES (
    'clientes',
    NEW.id,
    'UPDATE',
    json_object('tesoro', OLD.tesoro_total, 'nivel', OLD.nivel_fidelidad),
    json_object('tesoro', NEW.tesoro_total, 'nivel', NEW.nivel_fidelidad)
  );
END;
CREATE TRIGGER audit_cierres_insert
AFTER INSERT ON cierres_caja
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, usuario_id, datos_nuevos)
  VALUES ('cierres_caja', NEW.id, 'INSERT', NEW.usuario_id, json_object('cierre_num', NEW.cierre_num, 'total_general', NEW.total_general));
END;
CREATE INDEX idx_audit_fecha ON audit_logs(created_at);
CREATE TABLE facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_factura TEXT NOT NULL UNIQUE,
    serie TEXT DEFAULT 'A',
    fecha_emision DATE NOT NULL,
    fecha_operacion DATE,
    tipo_factura TEXT DEFAULT 'completa',
    cliente_id INTEGER,
    cliente_nif TEXT,
    cliente_nombre_fiscal TEXT,
    cliente_direccion_fiscal TEXT,
    cliente_cp TEXT,
    cliente_ciudad TEXT,
    cliente_pais TEXT,
    base_imponible REAL NOT NULL DEFAULT 0.0,
    total_iva REAL NOT NULL DEFAULT 0.0,
    total_recargo REAL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    iva_desglose TEXT DEFAULT '{}',
    ticket_id INTEGER,
    factura_rectificada_id INTEGER,
    notas TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
    FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE SET NULL,
    FOREIGN KEY(factura_rectificada_id) REFERENCES facturas(id) ON DELETE SET NULL
);
CREATE TABLE facturas_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    producto_id INTEGER,
    sku TEXT,
    descripcion TEXT NOT NULL,
    cantidad REAL NOT NULL DEFAULT 1.0,
    precio_unitario REAL NOT NULL DEFAULT 0.0,
    descuento REAL DEFAULT 0.0,
    base_imponible REAL NOT NULL DEFAULT 0.0,
    tipo_iva REAL NOT NULL DEFAULT 21.0,
    iva REAL NOT NULL DEFAULT 0.0,
    tipo_recargo REAL DEFAULT 0.0,
    recargo REAL DEFAULT 0.0,
    total_linea REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY(factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
    FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
);
CREATE INDEX idx_facturas_num ON facturas(num_factura);
CREATE INDEX idx_facturas_cliente ON facturas(cliente_id);
CREATE INDEX idx_facturas_fecha ON facturas(fecha_emision);
CREATE INDEX idx_facturas_lines_factura ON facturas_lines(factura_id);
CREATE TRIGGER audit_facturas_insert
AFTER INSERT ON facturas
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_nuevos)
  VALUES ('facturas', NEW.id, 'INSERT', json_object('num_factura', NEW.num_factura, 'total', NEW.total));
END;
CREATE TRIGGER audit_facturas_delete
AFTER DELETE ON facturas
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos)
  VALUES ('facturas', OLD.id, 'DELETE', json_object('num_factura', OLD.num_factura, 'total', OLD.total));
END;
CREATE TRIGGER audit_precios_insert
AFTER INSERT ON precios
FOR EACH ROW
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_nuevos)
  VALUES (
    'precios',
    NEW.id,
    'INSERT',
    json_object('producto_id', NEW.producto_id, 'pvp', NEW.pvp, 'coste', NEW.coste)
  );
END;
CREATE TRIGGER audit_precios_update
AFTER UPDATE ON precios
FOR EACH ROW
WHEN OLD.pvp != NEW.pvp OR OLD.coste != NEW.coste OR OLD.activo != NEW.activo
BEGIN
  INSERT INTO audit_logs (entidad, entidad_id, accion, datos_previos, datos_nuevos)
  VALUES (
    'precios',
    NEW.id,
    'UPDATE',
    json_object('producto_id', OLD.producto_id, 'pvp', OLD.pvp, 'coste', OLD.coste, 'activo', OLD.activo),
    json_object('producto_id', NEW.producto_id, 'pvp', NEW.pvp, 'coste', NEW.coste, 'activo', NEW.activo)
  );
END;
CREATE INDEX idx_tickets_cliente ON tickets(cliente_id);
CREATE INDEX idx_productos_proveedor ON productos(proveedor_id);
CREATE INDEX idx_productos_categoria ON productos(categoria);
CREATE INDEX idx_productos_tipo ON productos(tipo);
CREATE INDEX idx_ticket_lines_producto ON ticket_lines(producto_id);
