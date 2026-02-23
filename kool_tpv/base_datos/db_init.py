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
		required_tables = ["productos", "tickets", "cierres_caja"]

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
