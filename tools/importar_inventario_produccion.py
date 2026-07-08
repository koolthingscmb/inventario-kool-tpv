# -*- coding: utf-8 -*-
"""Importar inventario materias primas a produccion desde CSV."""
import csv, sys, os, logging, unicodedata, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.produccion.services.produccion_tipos_variantes_service import ProduccionTiposVariantesService
from kool_tpv.modulos.produccion.services.produccion_colores_service import ProduccionColoresService
from kool_tpv.modulos.produccion.services.produccion_stock_base_service import ProduccionStockBaseService
from kool_tpv.modulos.produccion.repositories.produccion_tallas_repository import ProduccionTallasRepository
from kool_tpv.modulos.produccion.repositories.produccion_relaciones_repository import ProduccionRelacionesRepository
from kool_tpv.modulos.produccion.models.produccion_talla_model import ProduccionTalla

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def _csku(s):
    s = unicodedata.normalize('NFD', s.upper()).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^A-Z0-9]', '', s)

def _cents(v):
    try:
        return int(round(float(v.strip().replace(',', '.')) * 100))
    except:
        return 0

class Importador:
    def __init__(self, db_path):
        self.db = Database(db_path)
        self.db.connect()
        self.sv = ProduccionTiposVariantesService(self.db)
        self.sc = ProduccionColoresService(self.db)
        self.ss = ProduccionStockBaseService(self.db)
        self.rt = ProduccionTallasRepository(self.db)
        self.rr = ProduccionRelacionesRepository(self.db)
        self._tipos = {r[1].strip().upper(): r[0] for r in self.db.fetch_all("SELECT id,nombre FROM tipos")}
        self._col = {c.nombre.strip().upper(): c.id for c in self.sc.obtener_todos()}
        self._tal = {t.nombre.strip().upper(): t.id for t in self.rt.get_todas()}
        self._var = {(v.tipo_id, v.nombre.strip().upper()): v.id for v in self.sv.obtener_todos()}

    def _color(self, n):
        if not n or not n.strip():
            return None
        k = n.strip().upper()
        if k in self._col:
            return self._col[k]
        self.sc.crear(n.strip().title())
        r = self.db.fetch_all("SELECT last_insert_rowid()")
        if r:
            self._col[k] = r[0][0]
            log.info(f"Color creado: {n}")
            return r[0][0]
        return None

    def _talla(self, n):
        if not n or not n.strip():
            return None
        k = n.strip().upper()
        if k in self._tal:
            return self._tal[k]
        ts = self.rt.get_todas()
        o = max((t.orden for t in ts), default=-1) + 1
        tid = self.rt.crear(ProduccionTalla(id=None, nombre=k, orden=o, activo=1))
        if tid:
            self._tal[k] = tid
            log.info(f"Talla creada: {n}")
            return tid
        return None

    def _variante(self, tid, n, cost, req_tal=1, req_col=1):
        k = (tid, n.strip().upper())
        if k in self._var:
            # Si ya existe, podríamos actualizar los requerimientos si fuera necesario
            return self._var[k]
        vid = self.sv.crear(tipo_id=tid, nombre=n.strip(), coste_base=cost, requiere_talla=req_tal, requiere_color=req_col)
        if vid:
            self._var[k] = vid
            log.info(f"Variante creada: {n} (Req Talla:{req_tal}, Color:{req_col})")
            return vid
        return None

    def importar(self, csv_path):
        ok, err, sk = 0, 0, 0
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Detectar delimitador (coma o punto y coma)
            content = f.read(1024)
            f.seek(0)
            delimiter = ';' if ';' in content else ','
            
            for i, r in enumerate(csv.DictReader(f, delimiter=delimiter), 2):
                if not (r.get('NOMBRE') or '').strip():
                    sk += 1
                    continue
                tnom = r.get('TIPO', '').strip()
                cnom = r.get('COLOR', '').strip()
                talla = r.get('TALLA', '').strip()
                vnom = r.get('VARIANTE', '').strip()
                uds = r.get('UNIDADES (stock_actual)', '0').strip()
                cost = _cents(r.get('COSTE', '0'))
                
                tid = self._tipos.get(tnom.upper())
                if not tid:
                    log.error(f"F{i}: tipo '{tnom}' no encontrado")
                    err += 1
                    continue

                # Determinar si requiere talla/color por presencia en CSV
                req_col = 1 if cnom else 0
                req_tal = 1 if talla else 0
                
                cid = self._color(cnom)
                talid = self._talla(talla)
                
                vid = self._variante(tid, vnom, cost, req_tal, req_col)
                if not vid:
                    err += 1
                    continue

                # Construcción de SKU inteligente
                sku_parts = [_csku(tnom)[:3], _csku(vnom)[:3]]
                if cnom:
                    sku_parts.append(_csku(cnom)[:3])
                if talla:
                    sku_parts.append(_csku(talla))
                sku = "-".join(sku_parts)

                try:
                    uds_i = int(uds)
                except ValueError:
                    uds_i = 0
                
                # cid y talid pueden ser None si no son requeridos
                self.ss.repo.crear_o_actualizar(tid, cid, (talla.upper() if talla else None), sku, uds_i, cost, vid, talid)
                self.rr.asegurar_relacion(tid, cid, talid, vid)
                
                ok += 1
                log.info(f"F{i}: OK {sku}")
        log.info(f"--- {ok} OK, {err} errores, {sk} skip ---")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python tools/importar_inventario_produccion.py <csv>")
        sys.exit(1)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'kool_tpv', 'base_datos', 'kool_bd.db')
    imp = Importador(db_path)
    imp.importar(sys.argv[1])
