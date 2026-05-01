#!/usr/bin/env python3
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.clientes.cliente_service import ClienteService

# Use the project's DB file
db_path = repo_root / "kool_tpv" / "base_datos" / "kool_bd.db"

db = Database(str(db_path))
db.connect()

svc = ClienteService(db)
raw_clientes = svc.buscar_clientes("")

print(raw_clientes[0])
print(raw_clientes[0].keys())

# close connection
try:
    db.close()
except Exception:
    pass
