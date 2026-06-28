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
                    'notas': r[14] or '',
                    'es_produccion': r[20] if len(r) > 20 else 0
                })
            return proveedores
        except Exception:
            logging.exception('Error obteniendo proveedores')
            return []

    def get_proveedores_con_mapeos(self):
        """Obtener proveedores marcados como de producción."""
        try:
            query = "SELECT * FROM proveedores WHERE es_produccion = 1 ORDER BY nombre ASC"
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
                    'notas': r[14] or '',
                    'es_produccion': r[20] if len(r) > 20 else 0
                })
            return proveedores
        except Exception:
            logging.exception('Error obteniendo proveedores de producción')
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
                'mapeo_csv': row[15] or None,
                'es_produccion': row[20] if len(row) > 20 else 0
            }
        except Exception:
            logging.exception(f'Error obteniendo proveedor {proveedor_id}')
            return None

    def save_proveedor(self, nombre, que_vende='', nif_cif='', iva_intracom='', 
                       dir_fiscal='', dir_envio='', email='', telefono='', 
                       forma_pago='', persona_comercial='', telefono_comercial='', 
                       email_comercial='', web='', notas='', es_produccion=0):
        """Crear nuevo proveedor."""
        try:
            query = """INSERT INTO proveedores 
                       (nombre, que_vende, nif_cif, iva_intracom, dir_fiscal, dir_envio, 
                        email, telefono, forma_pago, persona_comercial, telefono_comercial, 
                        email_comercial, web, notas, es_produccion) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            self.db.execute_query(query, (nombre, que_vende, nif_cif, iva_intracom, 
                                         dir_fiscal, dir_envio, email, telefono, 
                                         forma_pago, persona_comercial, telefono_comercial, 
                                         email_comercial, web, notas, es_produccion))
            return True
        except Exception:
            logging.exception('Error guardando proveedor')
            return False

    def update_proveedor(self, prov_id, nombre, que_vende='', nif_cif='', iva_intracom='', 
                        dir_fiscal='', dir_envio='', email='', telefono='', 
                        forma_pago='', persona_comercial='', telefono_comercial='', 
                        email_comercial='', web='', notas='', es_produccion=0):
        """Actualizar proveedor existente."""
        try:
            query = """UPDATE proveedores SET 
                       nombre=?, que_vende=?, nif_cif=?, iva_intracom=?, 
                       dir_fiscal=?, dir_envio=?, email=?, telefono=?, 
                       forma_pago=?, persona_comercial=?, telefono_comercial=?, 
                       email_comercial=?, web=?, notas=?, es_produccion=? 
                       WHERE id=?"""
            self.db.execute_query(query, (nombre, que_vende, nif_cif, iva_intracom, 
                                         dir_fiscal, dir_envio, email, telefono, 
                                         forma_pago, persona_comercial, telefono_comercial, 
                                         email_comercial, web, notas, es_produccion, prov_id))
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

    def get_mapeo_variantes(self, proveedor_id):
        """Obtener configuración de mapeo de variantes del proveedor."""
        try:
            query = "SELECT mapeo_variantes FROM proveedores WHERE id = ?"
            row = self.db.fetch_one(query, (proveedor_id,))
            if row and row[0]:
                return row[0]
            return None
        except Exception:
            logging.exception(f'Error obteniendo mapeo_variantes proveedor {proveedor_id}')
            return None

    def save_mapeo_variantes(self, proveedor_id, mapeo_json):
        """Guardar configuración de mapeo de variantes del proveedor."""
        try:
            query = "UPDATE proveedores SET mapeo_variantes = ? WHERE id = ?"
            self.db.execute_query(query, (mapeo_json, proveedor_id))
            logging.info(f'Mapeo variantes actualizado para proveedor {proveedor_id}')
            return True
        except Exception:
            logging.exception(f'Error guardando mapeo_variantes proveedor {proveedor_id}')
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
