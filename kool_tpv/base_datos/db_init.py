import logging
from pathlib import Path

from .db_wrapper import Database


def _read_migrations_sql() -> str:
	base = Path(__file__).resolve().parents[0]
	sql_path = base / "migraciones" / "base.sql"
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
				mig_path = Path(__file__).resolve().parents[0] / 'migraciones' / '002_num_ticket_text.sql'
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
				mig_path = Path(__file__).resolve().parents[0] / 'migraciones' / '003_devoluciones.sql'
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
				mig_path = Path(__file__).resolve().parents[0] / 'migraciones' / '004_presencia.sql'
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

		# Migration 012: Columna mapeo_tipos en proveedores
		try:
			cols = [r[1] for r in (db.fetch_all("PRAGMA table_info('proveedores')") or [])]
			if 'mapeo_tipos' not in cols:
				logging.info('Aplicando migración 012: mapeo_tipos en proveedores')
				db.connection.execute('ALTER TABLE proveedores ADD COLUMN mapeo_tipos TEXT')
				db.connection.commit()
				logging.info('Migración 012 (mapeo_tipos) aplicada correctamente')
		except Exception:
			logging.exception('Error aplicando migración 012')
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
