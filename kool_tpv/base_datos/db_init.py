import logging
from pathlib import Path

from .db_wrapper import Database
from kool_tpv.paths import get_resource_path, MIGRACIONES_DIR


def _read_migrations_sql() -> str:
	sql_path = MIGRACIONES_DIR / "base.sql"
	if not sql_path.exists():
		raise FileNotFoundError(f"Migration file not found: {sql_path}")
	return sql_path.read_text(encoding="utf-8")


def initialize_database(db_path: str) -> None:
	"""Initialize database from migrations if needed.

	If db_path == ':memory:' this will execute the migrations in the
	in-memory database.
	"""
	try:
		db = Database(db_path)
		db.connect()
	except Exception as e:
		logging.exception('No se pudo conectar a la DB en initialize_database')
		raise

	try:
		# Run migrations script if critical tables missing
		required_tables = ["productos", "tickets", "cierres"]

		# Check existence
		existing = []
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
			existing = [r[0] for r in rows or []]
		except Exception:
			logging.exception('Error leyendo sqlite_master')

		missing = [t for t in required_tables if t not in existing]

		if missing:
			logging.info(f"Tablas faltantes detectadas: {missing}. Aplicando migraciones.")
			sql = _read_migrations_sql()
			try:
				# execute whole script
				cur = db.connection.cursor()
				cur.executescript(sql)
				db.connection.commit()
				logging.info('Migraciones aplicadas correctamente')
			except Exception:
				logging.exception('Error aplicando migraciones')
				try:
					db.connection.rollback()
				except Exception:
					pass
				raise

		# After base migrations, ensure num_ticket column is TEXT; if it's INTEGER, apply specific migration
		try:
			rows = db.fetch_all("PRAGMA table_info('tickets')")
			# rows have columns: cid, name, type, notnull, dflt_value, pk
			col_type = None
			for r in rows or []:
				if r[1] == 'num_ticket':
					col_type = (r[2] or '').upper()
					break
			if col_type and 'INT' in col_type:
				# apply migration file 002 if present
				mig_path = MIGRACIONES_DIR / '002_num_ticket_text.sql'
				if mig_path.exists():
					try:
						logging.info('num_ticket column is INTEGER; applying 002_num_ticket_text.sql migration')
						cur = db.connection.cursor()
						cur.executescript(mig_path.read_text(encoding='utf-8'))
						db.connection.commit()
						logging.info('Migration 002 applied successfully')
					except Exception:
						logging.exception('Error applying migration 002')
						try:
							db.connection.rollback()
						except Exception:
							pass
				else:
					logging.warning('Migration file 002_num_ticket_text.sql not found; skipping')
		except Exception:
			logging.exception('Error checking/updating tickets.num_ticket type')

		# Migration 003: tabla devoluciones + columna total_devoluciones en clientes
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('clientes')") or [])]
			if 'total_devoluciones' not in cols:
				mig_path = MIGRACIONES_DIR / '003_devoluciones.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 003: devoluciones')
					db.connection.execute('ALTER TABLE clientes ADD COLUMN total_devoluciones INTEGER DEFAULT 0')
					db.connection.execute('''CREATE TABLE IF NOT EXISTS devoluciones (
						id          INTEGER PRIMARY KEY AUTOINCREMENT,
						ticket_id   INTEGER NOT NULL,
						cliente_id  INTEGER,
						cajero      TEXT,
						total_cents INTEGER NOT NULL DEFAULT 0,
						created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
						FOREIGN KEY(ticket_id)  REFERENCES tickets(id),
						FOREIGN KEY(cliente_id) REFERENCES clientes(id)
					)''')
					db.connection.commit()
					logging.info('Migración 003 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 003')

		# Migration 004: Control de Presencia
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='presencia'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '004_presencia.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 004: control de presencia')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 004 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 004')

		# Migration 005: Sistema de Favoritos (Colores e Iconos + tabla favoritos)
		try:
			# 1. Columnas color e icono en categorias y tipos
			for table in ['categorias', 'tipos']:
				cols = [r[1] for r in (db.fetch_all(f"PRAGMA table_info('{table}')") or [])]
				if 'color' not in cols:
					logging.info(f'Añadiendo columna color a {table}')
					db.connection.execute(f'ALTER TABLE {table} ADD COLUMN color TEXT')
				if 'icono' not in cols:
					logging.info(f'Añadiendo columna icono a {table}')
					db.connection.execute(f'ALTER TABLE {table} ADD COLUMN icono TEXT')
			
			# 2. Tabla favoritos
			db.connection.execute('''CREATE TABLE IF NOT EXISTS favoritos (
				id          INTEGER PRIMARY KEY AUTOINCREMENT,
				producto_id INTEGER NOT NULL,
				nombre      TEXT,
				posicion    INTEGER,
				created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY(producto_id) REFERENCES productos(id) ON DELETE CASCADE
			)''')
			
			db.connection.commit()
			logging.info('Migración 005 (Favoritos) aplicada correctamente o ya existente')
		except Exception:
			logging.exception('Error aplicando migración 005')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 010: Columna mapeo_colores en proveedores
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('proveedores')") or [])]
			if 'mapeo_colores' not in cols:
				logging.info('Aplicando migración 010: mapeo_colores en proveedores')
				db.connection.execute('ALTER TABLE proveedores ADD COLUMN mapeo_colores TEXT')
				db.connection.commit()
				logging.info('Migración 010 (mapeo_colores) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 010')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 011: Columna coste_medio en produccion_stock_colores_tallas
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('produccion_stock_colores_tallas')") or [])]
			if 'coste_medio' not in cols:
				logging.info('Aplicando migración 011: coste_medio en produccion_stock_colores_tallas')
				db.connection.execute('ALTER TABLE produccion_stock_colores_tallas ADD COLUMN coste_medio INTEGER DEFAULT 0')
				db.connection.commit()
				logging.info('Migración 011 (coste_medio) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 011')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 014: Columna mapeo_tallas en proveedores
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('proveedores')") or [])]
			if 'mapeo_tallas' not in cols:
				logging.info('Aplicando migración 014: mapeo_tallas en proveedores')
				db.connection.execute("ALTER TABLE proveedores ADD COLUMN mapeo_tallas TEXT DEFAULT '{}'")
				db.connection.commit()
				logging.info('Migración 014 (mapeo_tallas) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 014')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 035: Saneamiento de vínculos huérfanos en stock base (talla_id / color_id NULL)
		try:
			logging.info('Comprobando integridad de stock base (Migración 035)...')
			# 1. Reparar talla_id usando el nombre de la talla (limpiando espacios)
			db.connection.execute("""
				UPDATE produccion_stock_colores_tallas
				SET talla_id = (
					SELECT id FROM produccion_tallas 
					WHERE TRIM(UPPER(produccion_tallas.nombre)) = TRIM(UPPER(produccion_stock_colores_tallas.talla))
					LIMIT 1
				)
				WHERE talla_id IS NULL AND talla IS NOT NULL AND talla != ''
			""")
			
			# 2. Reparar color_id usando el nombre del color (limpiando espacios)
			# Nota: Solo si color_id es NULL pero tenemos el nombre del color en alguna parte o podemos deducirlo.
			# En esta tabla el color_id es obligatorio, pero si hubiera basura, lo intentamos rescatar.
			db.connection.execute("""
				UPDATE produccion_stock_colores_tallas
				SET color_id = (
					SELECT id FROM produccion_colores 
					WHERE TRIM(UPPER(produccion_colores.nombre)) = (
						SELECT TRIM(UPPER(c.nombre)) FROM produccion_colores c WHERE c.id = color_id
					)
					LIMIT 1
				)
				WHERE color_id IS NULL
			""")
			
			db.connection.commit()
			logging.info('Migración 035 (Saneamiento de stock) finalizada con éxito.')
		except Exception:
			logging.exception('Error aplicando migración 035 (Saneamiento)')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 036: Refuerzo de Foreign Keys (Cursiva en DB Browser)
		try:
			# Comprobar si ya tenemos las FKs reales (buscando 'REFERENCES' en el SQL de creación)
			schema = db.fetch_one("SELECT sql FROM sqlite_master WHERE type='table' AND name='produccion_stock_colores_tallas'")
			if schema and 'REFERENCES produccion_tallas' not in schema[0]:
				logging.info('Aplicando migración 036: Reforzando Foreign Keys en stock base...')
				
				with db.transaction() as cur:
					# 1. Crear tabla nueva con estructura robusta
					cur.execute("""
						CREATE TABLE produccion_stock_colores_tallas_new (
							id INTEGER PRIMARY KEY AUTOINCREMENT,
							tipo_id INTEGER NOT NULL,
							variante_id INTEGER,
							color_id INTEGER,
							talla TEXT,
							sku TEXT,
							cantidad INTEGER DEFAULT 0,
							coste_medio INTEGER DEFAULT 0,
							talla_id INTEGER,
							FOREIGN KEY (tipo_id) REFERENCES tipos(id) ON DELETE CASCADE,
							FOREIGN KEY (variante_id) REFERENCES tipos_variantes(id) ON DELETE CASCADE,
							FOREIGN KEY (color_id) REFERENCES produccion_colores(id) ON DELETE CASCADE,
							FOREIGN KEY (talla_id) REFERENCES produccion_tallas(id) ON DELETE SET NULL
						)
					""")
					
					# 2. Migrar datos
					cur.execute("""
						INSERT INTO produccion_stock_colores_tallas_new 
						(id, tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id)
						SELECT id, tipo_id, variante_id, color_id, talla, sku, cantidad, coste_medio, talla_id
						FROM produccion_stock_colores_tallas
					""")
					
					# 3. Intercambiar tablas
					cur.execute("DROP TABLE produccion_stock_colores_tallas")
					cur.execute("ALTER TABLE produccion_stock_colores_tallas_new RENAME TO produccion_stock_colores_tallas")
					
					# 4. Recrear índice de SKU (importante para rendimiento)
					cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_base_sku ON produccion_stock_colores_tallas(sku)")
					
				logging.info('Migración 036 (Foreign Keys) aplicada correctamente.')
		except Exception:
			logging.exception('Error aplicando migración 036 (Refuerzo FKs)')

		# Migración 037: Añadir tipo_id y variante_id a produccion_disenos_metodos
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('produccion_disenos_metodos')") or [])]
			if 'variante_id' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '037_disenos_metodos_variantes.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 037: tipo_id/variante_id en produccion_disenos_metodos')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 037 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 037')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 038: usuario_id en stock_movements
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('stock_movements')") or [])]
			if 'usuario_id' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '038_add_usuario_to_stock_movements.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 038: usuario_id en stock_movements')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 038 aplicada correctamente')
			else:
				logging.info('Migración 038 ya existente en base de datos')
		except Exception:
			logging.exception('Error aplicando migración 038')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 015: tipos_variantes
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='tipos_variantes'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '015_tipos_variantes.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 015: tipos_variantes')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 015 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 015')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 017: requerimientos en tipos_variantes
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('tipos_variantes')") or [])]
			if 'requiere_talla' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '017_tipos_variantes_requerimientos.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 017: requiere_talla/color en tipos_variantes')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 017 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 017')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 039: Agrupación de tallas en producción
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='produccion_tallas_grupo_items'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '039_produccion_tallas_grupos.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 039: Agrupación de tallas en producción (N:M)')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 039 aplicada correctamente')
			else:
				# Si la tabla existe, asegurar que la columna grupo_talla_id está en tipos_variantes
				cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('tipos_variantes')") or [])]
				if 'grupo_talla_id' not in cols:
					logging.info('Añadiendo columna grupo_talla_id a tipos_variantes (parche 039)')
					db.connection.execute('ALTER TABLE tipos_variantes ADD COLUMN grupo_talla_id INTEGER REFERENCES produccion_tallas_grupos(id) ON DELETE SET NULL')
					db.connection.commit()
				logging.info('Migración 039 ya existente o actualizada en base de datos')
		except Exception:
			logging.exception('Error aplicando migración 039')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 018: permiso_cajon en usuarios
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('usuarios')") or [])]
			if 'permiso_cajon' not in cols:
				logging.info('Aplicando migración 018: permiso_cajon en usuarios')
				db.connection.execute('ALTER TABLE usuarios ADD COLUMN permiso_cajon INTEGER DEFAULT 0')
				db.connection.commit()
				logging.info('Migración 018 (permiso_cajon) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 018')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 019: campo origen en produccion_ordenes
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('produccion_ordenes')") or [])]
			if 'origen' not in cols:
				logging.info('Aplicando migración 019: origen en produccion_ordenes')
				db.connection.execute("ALTER TABLE produccion_ordenes ADD COLUMN origen TEXT DEFAULT 'KOOL'")
				db.connection.commit()
				logging.info('Migración 019 (origen produccion_ordenes) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 019')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 020: campo origen en produccion_lineas
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('produccion_lineas')") or [])]
			if 'origen' not in cols:
				logging.info('Aplicando migración 020: origen en produccion_lineas')
				db.connection.execute("ALTER TABLE produccion_lineas ADD COLUMN origen TEXT DEFAULT 'KOOL'")
				db.connection.commit()
				logging.info('Migración 020 (origen produccion_lineas) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 020')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 021: campo talla_id en produccion_stock_colores_tallas (INTEGER)
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('produccion_stock_colores_tallas')") or [])]
			if 'talla_id' not in cols:
				logging.info('Aplicando migración 021: talla_id en produccion_stock_colores_tallas')
				db.connection.execute("ALTER TABLE produccion_stock_colores_tallas ADD COLUMN talla_id INTEGER")
				
				# Intentar sincronizar talla_id desde produccion_tallas comparando por nombre
				db.connection.execute("""
					UPDATE produccion_stock_colores_tallas
					SET talla_id = (
						SELECT id FROM produccion_tallas 
						WHERE produccion_tallas.nombre = produccion_stock_colores_tallas.talla
						LIMIT 1
					)
					WHERE talla_id IS NULL
				""")
				
				db.connection.commit()
				logging.info('Migración 021 (talla_id en produccion_stock_colores_tallas) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 021')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migración 023: Tabla produccion_tipo_color_tallas y limpieza stock
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='produccion_tipo_color_tallas'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '023_matriz_config_table.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 023: Tabla produccion_tipo_color_tallas y limpieza stock')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 023 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 023')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 027: campo lore_recompensa en niveles_fidelidad
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('niveles_fidelidad')") or [])]
			if 'lore_recompensa' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '027_lore_recompensa.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 027: lore_recompensa en niveles_fidelidad')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 027 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 027')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 028: columnas de descuento en niveles_fidelidad (codigo_recompensa, descuento_tipo, descuento_valor)
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('niveles_fidelidad')") or [])]
			if 'codigo_recompensa' not in cols:
				logging.info('Aplicando migración 028: columnas de descuento en niveles_fidelidad')
				db.connection.execute('ALTER TABLE niveles_fidelidad ADD COLUMN codigo_recompensa TEXT')
				db.connection.execute('ALTER TABLE niveles_fidelidad ADD COLUMN descuento_tipo TEXT')
				db.connection.execute('ALTER TABLE niveles_fidelidad ADD COLUMN descuento_valor REAL')
				db.connection.commit()
				logging.info('Migración 028 (descuento en niveles_fidelidad) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 028')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 029: tabla pedidos_clientes
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='pedidos_clientes'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '029_pedidos_clientes.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 029: pedidos_clientes')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 029 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 029')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 030: refactor pedidos_clientes v2 (lines)
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('pedidos_clientes')") or [])]
			if 'contacto_email' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '030_pedidos_clientes_v2.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 030: pedidos_clientes_v2')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 030 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 030')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 031: IDs de Tipo y Proveedor en líneas
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('pedidos_clientes_lines')") or [])]
			if 'tipo_id' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '031_pedidos_v3.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 031: IDs de tipo/proveedor en pedidos')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 031 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 031')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 032: campo vale_id en pedidos_clientes
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('pedidos_clientes')") or [])]
			if cols and 'vale_id' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '032_pedidos_vale_id.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 032: vale_id en pedidos_clientes')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 032 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 032')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 033: Google Drive Config
		try:
			cols = db.fetch_all("SELECT clave FROM configuracion WHERE clave IN ('backup_drive_enabled', 'backup_drive_folder_name')")
			if not cols or len(cols) < 2:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '033_google_drive_config.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 033: Google Drive Config')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 033 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 033')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 034: Personalización visual de usuarios (ui_color, banner_path)
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('usuarios')") or [])]
			if 'ui_color' not in cols:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '034_usuarios_visual_customization.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 034: ui_color/banner_path en usuarios')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 034 aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 034')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Migration 040: Módulo Shopify (Mapping y Sync Log)
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='shopify_product_mapping'")
			if not rows:
				mig_path = get_resource_path("kool_tpv", "base_datos", "migraciones") / '040_shopify_module.sql'
				if mig_path.exists():
					logging.info('Aplicando migración 040: Módulo Shopify')
					cur = db.connection.cursor()
					cur.executescript(mig_path.read_text(encoding='utf-8'))
					db.connection.commit()
					logging.info('Migración 040 aplicada correctamente')
			else:
				logging.info('Migración 040 ya existente en base de datos')
		except Exception:
			logging.exception('Error aplicando migración 040')
			try:
				db.connection.rollback()
			except Exception:
				pass

		# Validate again
		try:
			rows = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
			existing = [r[0] for r in rows or []]
		except Exception:
			logging.exception('Error leyendo sqlite_master post-migration')

		still_missing = [t for t in required_tables if t not in existing]
		if still_missing:
			logging.error(f"Después de migraciones faltan tablas críticas: {still_missing}")
			raise RuntimeError(f"Tablas críticas faltantes: {still_missing}")

	finally:
		try:
			db.close_connection()
		except Exception:
			pass
