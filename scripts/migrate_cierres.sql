BEGIN TRANSACTION;

-- Crear nueva tabla 'cierres' con defaults enteros adecuados
CREATE TABLE IF NOT EXISTS cierres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cierre_num INTEGER,
  fecha_hora TIMESTAMP,
  cajero TEXT,
  total_ingresos INTEGER DEFAULT 0,
  num_ventas INTEGER,
  rango_inicio_ticket INTEGER,
  rango_fin_ticket INTEGER,
  total_efectivo INTEGER DEFAULT 0,
  total_tarjeta INTEGER DEFAULT 0,
  total_web INTEGER DEFAULT 0,
  total_devoluciones INTEGER DEFAULT 0,
  total_descuentos INTEGER DEFAULT 0,
  tesoro_ganado INTEGER DEFAULT 0,
  tesoro_gastado INTEGER DEFAULT 0,
  tesoro_total_ganado INTEGER DEFAULT 0,
  tesoro_total_gastado INTEGER DEFAULT 0,
  cierre_text TEXT,
  usuario_id INTEGER,
  total_base_imponible INTEGER DEFAULT 0,
  total_iva INTEGER DEFAULT 0,
  base_21 INTEGER DEFAULT 0,
  iva_21 INTEGER DEFAULT 0,
  base_4 INTEGER DEFAULT 0,
  iva_4 INTEGER DEFAULT 0,
  iva_desglose TEXT DEFAULT '{}',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  printed INTEGER DEFAULT 0,
  printed_at TIMESTAMP,
  printer_name TEXT
);

-- Copiar datos desde la tabla antigua `cierres_caja` si existe
INSERT INTO cierres (
  id, cierre_num, fecha_hora, cajero, total_ingresos, num_ventas,
  rango_inicio_ticket, rango_fin_ticket, total_efectivo, total_tarjeta,
  total_web, total_devoluciones, total_descuentos, tesoro_ganado,
  tesoro_gastado, tesoro_total_ganado, tesoro_total_gastado, cierre_text,
  usuario_id, total_base_imponible, total_iva, base_21, iva_21, base_4, iva_4, iva_desglose
)
SELECT
  id, cierre_num, fecha_hora, cajero, total_ingresos, num_ventas,
  rango_inicio_ticket, rango_fin_ticket, total_efectivo, total_tarjeta,
  total_web, total_devoluciones, total_descuentos, tesoro_ganado,
  tesoro_gastado, tesoro_total_ganado, tesoro_total_gastado, cierre_text,
  usuario_id, total_base_imponible, total_iva, base_21, iva_21, base_4, iva_4, iva_desglose
FROM cierres_caja
;

-- Crear tabla de líneas de cierre
CREATE TABLE IF NOT EXISTS cierres_lineas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cierre_id INTEGER NOT NULL,
  ticket_id INTEGER,
  ticket_num INTEGER,
  ticket_total INTEGER DEFAULT 0,
  forma_pago TEXT,
  efectivo INTEGER DEFAULT 0,
  tarjeta INTEGER DEFAULT 0,
  web INTEGER DEFAULT 0,
  descuentos INTEGER DEFAULT 0,
  devoluciones INTEGER DEFAULT 0,
  tesoro_ganado INTEGER DEFAULT 0,
  tesoro_gastado INTEGER DEFAULT 0,
  notas TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cierre_id) REFERENCES cierres(id) ON DELETE CASCADE
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_cierres_fecha ON cierres(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_cierres_num ON cierres(cierre_num);
CREATE INDEX IF NOT EXISTS idx_lineas_cierre ON cierres_lineas(cierre_id);
CREATE INDEX IF NOT EXISTS idx_lineas_ticket ON cierres_lineas(ticket_id);

-- (Opcional) Si quieres eliminar la tabla antigua, uncomment the next line
-- DROP TABLE IF EXISTS cierres_caja;

COMMIT;
