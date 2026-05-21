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
