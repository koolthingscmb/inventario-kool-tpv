-- Script SQL inicial con el esquema mínimo necesario para pruebas
PRAGMA foreign_keys = ON;

-- Full schema derived from kool_bd_schema_2026-02-15

-- audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	entidad TEXT,
	entidad_id INTEGER,
	accion TEXT,
	usuario_id INTEGER,
	datos_previos TEXT,
	datos_nuevos TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- categorias
CREATE TABLE IF NOT EXISTS categorias (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nombre TEXT UNIQUE,
	descripcion TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	shopify_taxonomy TEXT,
	fide_porcentaje REAL
);

-- tipos
CREATE TABLE IF NOT EXISTS tipos (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nombre TEXT UNIQUE,
	descripcion TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	shopify_taxonomy TEXT,
	fide_porcentaje REAL
);

-- proveedores
CREATE TABLE IF NOT EXISTS proveedores (
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
);

-- configuracion
CREATE TABLE IF NOT EXISTS configuracion (
	clave TEXT PRIMARY KEY,
	valor TEXT
);

-- niveles_fidelidad
CREATE TABLE IF NOT EXISTS niveles_fidelidad (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	level INTEGER NOT NULL UNIQUE,
	nombre_nivel TEXT NOT NULL,
	grafismo_nivel TEXT,
	tesoro_minimo REAL NOT NULL DEFAULT 0.0,
	tipo_recompensa TEXT,
	detalle_recompensa TEXT,
	producto_sku TEXT
);

-- cierres_caja
CREATE TABLE IF NOT EXISTS cierres_caja (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	cierre_num INTEGER,
	fecha_hora DATETIME,
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
	usuario_id INTEGER,
	total_base_imponible REAL DEFAULT 0.0,
	total_iva REAL DEFAULT 0.0,
	base_21 REAL DEFAULT 0.0,
	iva_21 REAL DEFAULT 0.0,
	base_4 REAL DEFAULT 0.0,
	iva_4 REAL DEFAULT 0.0,
	iva_desglose TEXT DEFAULT '{}'
);

-- productos
CREATE TABLE IF NOT EXISTS productos (
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
	estado TEXT,
	etiquetas TEXT,
	shop_link TEXT,
	shopify_taxonomy TEXT,
	FOREIGN KEY (categoria) REFERENCES categorias(id) ON DELETE RESTRICT,
	FOREIGN KEY (tipo) REFERENCES tipos(id) ON DELETE RESTRICT,
	FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
);

-- precios
CREATE TABLE IF NOT EXISTS precios (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	producto_id INTEGER,
	pvp REAL DEFAULT 0.0,
	coste REAL DEFAULT 0.0,
	fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
	activo INTEGER DEFAULT 1,
	FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

-- codigos_barras
CREATE TABLE IF NOT EXISTS codigos_barras (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	producto_id INTEGER,
	ean TEXT NOT NULL,
	creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

-- clientes
CREATE TABLE IF NOT EXISTS clientes (
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
	fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- stock_movements
CREATE TABLE IF NOT EXISTS stock_movements (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	producto_id INTEGER NOT NULL,
	cantidad INTEGER NOT NULL,
	motivo TEXT,
	ticket_line_id INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY(producto_id) REFERENCES productos(id),
	FOREIGN KEY(ticket_line_id) REFERENCES ticket_lines(id)
);

-- tickets
CREATE TABLE IF NOT EXISTS tickets (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	cajero TEXT,
	cliente TEXT,
	cliente_id INTEGER,
	num_ticket INTEGER,
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
);

-- ticket_lines
CREATE TABLE IF NOT EXISTS ticket_lines (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	ticket_id INTEGER NOT NULL,
	sku TEXT,
	nombre TEXT,
	cantidad REAL,
	precio REAL,
	iva REAL,
	line_tipo TEXT DEFAULT 'venta',
	producto_id INTEGER,
	FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
	FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE SET NULL
);

-- payments
CREATE TABLE IF NOT EXISTS payments (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	ticket_id INTEGER NOT NULL,
	metodo TEXT,
	importe REAL NOT NULL,
	referencia TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

-- points_movements
CREATE TABLE IF NOT EXISTS points_movements (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	cliente_id INTEGER NOT NULL,
	puntos REAL NOT NULL,
	motivo TEXT,
	ticket_id INTEGER,
	usuario_id INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY(cliente_id) REFERENCES clientes(id),
	FOREIGN KEY(ticket_id) REFERENCES tickets(id)
);

-- usuarios
CREATE TABLE IF NOT EXISTS usuarios (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nombre TEXT NOT NULL,
	password TEXT NOT NULL,
	rol TEXT NOT NULL,
	permiso_cierre INTEGER DEFAULT 0,
	permiso_descuento INTEGER DEFAULT 0,
	permiso_devolucion INTEGER DEFAULT 0,
	permiso_tickets INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_precios_activo ON precios(producto_id, activo);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);
CREATE INDEX IF NOT EXISTS idx_productos_tipo ON productos(tipo);
CREATE INDEX IF NOT EXISTS idx_stock_mov_producto ON stock_movements(producto_id);
CREATE INDEX IF NOT EXISTS idx_ticket_lines_ticket ON ticket_lines(ticket_id);
CREATE INDEX IF NOT EXISTS idx_codigos_producto ON codigos_barras(producto_id);

-- Triggers
CREATE TRIGGER IF NOT EXISTS trg_ticket_lines_after_delete
AFTER DELETE ON ticket_lines
BEGIN
  UPDATE tickets SET num_ventas = COALESCE((SELECT COUNT(*) FROM ticket_lines WHERE ticket_id = OLD.ticket_id),0) WHERE id = OLD.ticket_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_ticket_lines_after_insert
AFTER INSERT ON ticket_lines
BEGIN
  UPDATE tickets SET num_ventas = COALESCE((SELECT COUNT(*) FROM ticket_lines WHERE ticket_id = NEW.ticket_id),0) WHERE id = NEW.ticket_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_ticket_lines_after_update_ticketid
AFTER UPDATE OF ticket_id ON ticket_lines
BEGIN
  UPDATE tickets SET num_ventas = COALESCE((SELECT COUNT(*) FROM ticket_lines WHERE ticket_id = OLD.ticket_id),0) WHERE id = OLD.ticket_id;
  UPDATE tickets SET num_ventas = COALESCE((SELECT COUNT(*) FROM ticket_lines WHERE ticket_id = NEW.ticket_id),0) WHERE id = NEW.ticket_id;
END;

-- Seed data: default category, type and basic configuration keys
INSERT OR IGNORE INTO categorias (nombre, descripcion, shopify_taxonomy, fide_porcentaje) VALUES ('GENERAL', 'Categoría por defecto', '', 0.0);
INSERT OR IGNORE INTO tipos (nombre, descripcion, shopify_taxonomy, fide_porcentaje) VALUES ('PRODUCTO', 'Tipo por defecto', '', 0.0);
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('fide_porcentaje_general', '0');
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ticket_nombre_negocio', 'Mi Negocio');
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ticket_direccion', 'Dirección');
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ticket_nif', '');
INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('ticket_pie_texto', 'Gracias por su compra');


-- Tabla para almacenar códigos de barras (EAN) por producto
CREATE TABLE IF NOT EXISTS codigos_barras (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	producto_id INTEGER NOT NULL,
	ean TEXT NOT NULL,
	creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_codigos_producto ON codigos_barras(producto_id);

