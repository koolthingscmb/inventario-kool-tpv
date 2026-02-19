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
