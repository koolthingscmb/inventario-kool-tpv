"""Servicio de proveedores - CRUD completo."""
import logging


class ProveedorService:
    def __init__(self, db):
        self.db = db

    def get_all_proveedores(self):
        """Obtener todos los proveedores."""
        try:
            query = "SELECT * FROM proveedores ORDER BY nombre ASC"
            rows = self.db.fetch_all(query)
            proveedores = []
            for r in rows or []:
                proveedores.append({
                    'id': r[0],
                    'nombre': r[1] or '',
                    'que_vende': r[2] or '',
                    'nif_cif': r[3] or '',
                    'iva_intracom': r[4] or '',
                    'dir_fiscal': r[5] or '',
                    'dir_envio': r[6] or '',
                    'email': r[7] or '',
                    'telefono': r[8] or '',
                    'forma_pago': r[9] or '',
                    'persona_comercial': r[10] or '',
                    'telefono_comercial': r[11] or '',
                    'email_comercial': r[12] or '',
                    'web': r[13] or '',
                    'notas': r[14] or ''
                })
            return proveedores
        except Exception:
            logging.exception('Error obteniendo proveedores')
            return []

    def get_proveedores_con_mapeos(self):
        """Obtener solo proveedores que tienen algún mapeo configurado."""
        try:
            query = """SELECT * FROM proveedores
                       WHERE (mapeo_colores IS NOT NULL AND mapeo_colores != '' AND mapeo_colores != '{}')
                          OR (mapeo_tipos IS NOT NULL AND mapeo_tipos != '' AND mapeo_tipos != '{}')
                          OR (mapeo_generos IS NOT NULL AND mapeo_generos != '' AND mapeo_generos != '{}')
                          OR (mapeo_tallas IS NOT NULL AND mapeo_tallas != '' AND mapeo_tallas != '{}')
                       ORDER BY nombre ASC"""
            rows = self.db.fetch_all(query)
            proveedores = []
            for r in rows or []:
                proveedores.append({
                    'id': r[0],
                    'nombre': r[1] or '',
                    'que_vende': r[2] or '',
                    'nif_cif': r[3] or '',
                    'iva_intracom': r[4] or '',
                    'dir_fiscal': r[5] or '',
                    'dir_envio': r[6] or '',
                    'email': r[7] or '',
                    'telefono': r[8] or '',
                    'forma_pago': r[9] or '',
                    'persona_comercial': r[10] or '',
                    'telefono_comercial': r[11] or '',
                    'email_comercial': r[12] or '',
                    'web': r[13] or '',
                    'notas': r[14] or ''
                })
            return proveedores
        except Exception:
            logging.exception('Error obteniendo proveedores con mapeos')
            return []

    def get_proveedor(self, proveedor_id):
        """Obtener un proveedor por ID.

        Args:
            proveedor_id: ID del proveedor

        Returns:
            dict con datos del proveedor o None si no existe
        """
        try:
            query = "SELECT * FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))

            if not row:
                return None

            return {
                'id': row[0],
                'nombre': row[1] or '',
                'que_vende': row[2] or '',
                'nif_cif': row[3] or '',
                'iva_intracom': row[4] or '',
                'dir_fiscal': row[5] or '',
                'dir_envio': row[6] or '',
                'email': row[7] or '',
                'telefono': row[8] or '',
                'forma_pago': row[9] or '',
                'persona_comercial': row[10] or '',
                'telefono_comercial': row[11] or '',
                'email_comercial': row[12] or '',
                'web': row[13] or '',
                'notas': row[14] or '',
                'mapeo_csv': row[15] or None
            }
        except Exception:
            logging.exception(f'Error obteniendo proveedor {proveedor_id}')
            return None

    def save_proveedor(self, nombre, que_vende='', nif_cif='', iva_intracom='', 
                       dir_fiscal='', dir_envio='', email='', telefono='', 
                       forma_pago='', persona_comercial='', telefono_comercial='', 
                       email_comercial='', web='', notas=''):
        """Crear nuevo proveedor."""
        try:
            query = """INSERT INTO proveedores 
                       (nombre, que_vende, nif_cif, iva_intracom, dir_fiscal, dir_envio, 
                        email, telefono, forma_pago, persona_comercial, telefono_comercial, 
                        email_comercial, web, notas) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            self.db.execute_query(query, (nombre, que_vende, nif_cif, iva_intracom, 
                                         dir_fiscal, dir_envio, email, telefono, 
                                         forma_pago, persona_comercial, telefono_comercial, 
                                         email_comercial, web, notas))
            return True
        except Exception:
            logging.exception('Error guardando proveedor')
            return False

    def update_proveedor(self, prov_id, nombre, que_vende='', nif_cif='', iva_intracom='', 
                        dir_fiscal='', dir_envio='', email='', telefono='', 
                        forma_pago='', persona_comercial='', telefono_comercial='', 
                        email_comercial='', web='', notas=''):
        """Actualizar proveedor existente."""
        try:
            query = """UPDATE proveedores SET 
                       nombre=?, que_vende=?, nif_cif=?, iva_intracom=?, 
                       dir_fiscal=?, dir_envio=?, email=?, telefono=?, 
                       forma_pago=?, persona_comercial=?, telefono_comercial=?, 
                       email_comercial=?, web=?, notas=? 
                       WHERE id=?"""
            self.db.execute_query(query, (nombre, que_vende, nif_cif, iva_intracom, 
                                         dir_fiscal, dir_envio, email, telefono, 
                                         forma_pago, persona_comercial, telefono_comercial, 
                                         email_comercial, web, notas, prov_id))
            return True
        except Exception:
            logging.exception('Error actualizando proveedor')
            return False

    def delete_proveedor(self, prov_id):
        """Eliminar proveedor."""
        try:
            query = "DELETE FROM proveedores WHERE id = ?"
            self.db.execute_query(query, (prov_id,))
            return True
        except Exception:
            logging.exception('Error eliminando proveedor')
            return False

    def get_mapeo_csv(self, proveedor_id):
        """Obtener configuración de mapeo CSV del proveedor.

        Args:
            proveedor_id: ID del proveedor

        Returns:
            str: JSON string con mapeo o None si no existe
        """
        try:
            query = "SELECT mapeo_csv FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_csv proveedor {proveedor_id}')
            return None

    def save_mapeo_csv(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo CSV del proveedor.

        Args:
            proveedor_id: ID del proveedor
            mapeo_json: String JSON con configuración de mapeo

        Returns:
            bool: True si OK, False si error
        """
        try:
            query = "UPDATE proveedores SET mapeo_csv = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo CSV actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_csv proveedor {proveedor_id}')
            return False

    def get_mapeo_colores(self, proveedor_id):
        """Obtener configuración de mapeo de colores del proveedor."""
        try:
            query = "SELECT mapeo_colores FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_colores proveedor {proveedor_id}')
            return None

    def save_mapeo_colores(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo de colores del proveedor."""
        try:
            query = "UPDATE proveedores SET mapeo_colores = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo colores actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_colores proveedor {proveedor_id}')
            return False

    def get_mapeo_tipos(self, proveedor_id):
        """Obtener configuración de mapeo de tipos del proveedor."""
        try:
            query = "SELECT mapeo_tipos FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_tipos proveedor {proveedor_id}')
            return None

    def save_mapeo_tipos(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo de tipos del proveedor."""
        try:
            query = "UPDATE proveedores SET mapeo_tipos = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo tipos actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_tipos proveedor {proveedor_id}')
            return False

    def get_mapeo_generos(self, proveedor_id):
        """Obtener configuración de mapeo de géneros del proveedor."""
        try:
            query = "SELECT mapeo_generos FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_generos proveedor {proveedor_id}')
            return None

    def save_mapeo_generos(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo de géneros del proveedor."""
        try:
            query = "UPDATE proveedores SET mapeo_generos = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo géneros actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_generos proveedor {proveedor_id}')
            return False

    def get_mapeo_tallas(self, proveedor_id):
        """Obtener configuración de mapeo de tallas del proveedor."""
        try:
            query = "SELECT mapeo_tallas FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_tallas proveedor {proveedor_id}')
            return None

    def save_mapeo_tallas(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo de tallas del proveedor."""
        try:
            query = "UPDATE proveedores SET mapeo_tallas = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo tallas actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_tallas proveedor {proveedor_id}')
            return False
