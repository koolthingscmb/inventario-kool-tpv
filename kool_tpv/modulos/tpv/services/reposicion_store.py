"""ReposicionStore: gestión de reposiciones en JSON (sin BD).

Este servicio maneja la persistencia de líneas de reposición en archivos JSON,
siguiendo el mismo patrón que AlbaranBorradorService pero para datos volátiles
que no deben persistir en la base de datos principal.
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

from kool_tpv.base_datos.money_adapter import prepare_for_db

logger = logging.getLogger(__name__)

# Directorio para archivos de reposición (misma ubicación que borradores)
REPOSICION_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'borradores')
REPOSICION_FILE = os.path.join(REPOSICION_DIR, 'reposicion_pendiente.json')
TEMP_FILE = os.path.join(REPOSICION_DIR, 'reposicion_pendientes_temp.json')


class ReposicionStore:
    """Gestiona el almacenamiento de líneas de reposición en JSON."""
    
    def __init__(self):
        # Asegurar que el directorio existe
        os.makedirs(REPOSICION_DIR, exist_ok=True)
    
    def cargar(self) -> List[Dict[str, Any]]:
        """Carga todas las líneas de reposición desde el JSON.
        
        Returns:
            Lista de diccionarios con las líneas de reposición
        """
        try:
            if not os.path.exists(REPOSICION_FILE):
                return []
            
            with open(REPOSICION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.exception(f"Error cargando reposiciones desde {REPOSICION_FILE}")
            return []
    
    def guardar(self, lineas: List[Dict[str, Any]]) -> bool:
        """Guarda la lista completa de líneas de reposición en el JSON.
        
        Args:
            lineas: Lista de diccionarios con las líneas a guardar
            
        Returns:
            True si se guardó correctamente, False si hubo error
        """
        try:
            if not lineas:
                # Si no hay líneas, borrar el archivo
                self.borrar_archivo()
                return True
            
            with open(REPOSICION_FILE, 'w', encoding='utf-8') as f:
                json.dump(lineas, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.exception(f"Error guardando reposiciones en {REPOSICION_FILE}")
            return False
    
    def añadir(self, linea: Dict[str, Any]) -> bool:
        """Añade una nueva línea de reposición.
        
        Args:
            linea: Diccionario con los datos de la línea
            
        Returns:
            True si se añadió correctamente, False si hubo error
        """
        try:
            # Asegurar que tenga UUID y fecha
            if 'id' not in linea:
                linea['id'] = str(uuid.uuid4())
            if 'fecha' not in linea:
                linea['fecha'] = datetime.now().isoformat()
            
            lineas = self.cargar()
            lineas.append(linea)
            return self.guardar(lineas)
        except Exception as e:
            logger.exception("Error añadiendo línea de reposición")
            return False
    
    def borrar(self, linea_id: str) -> bool:
        """Borra una línea de reposición por su ID.
        
        Args:
            linea_id: UUID de la línea a borrar
            
        Returns:
            True si se borró correctamente, False si hubo error
        """
        try:
            lineas = self.cargar()
            lineas_filtradas = [l for l in lineas if l.get('id') != linea_id]
            
            if len(lineas) == len(lineas_filtradas):
                # No se encontró la línea
                return False
            
            return self.guardar(lineas_filtradas)
        except Exception as e:
            logger.exception(f"Error borrando línea {linea_id}")
            return False
    
    def restar(self, linea_id: str, cantidad: int) -> bool:
        """Resta cantidad de una línea de reposición. Si llega a 0, la borra.
        
        Args:
            linea_id: UUID de la línea a modificar
            cantidad: Cantidad a restar
            
        Returns:
            True si se modificó correctamente, False si hubo error
        """
        try:
            lineas = self.cargar()
            modificada = False
            
            for i, linea in enumerate(lineas):
                if linea.get('id') == linea_id:
                    cantidad_actual = int(linea.get('cantidad', 0))
                    nueva_cantidad = max(0, cantidad_actual - cantidad)
                    
                    if nueva_cantidad <= 0:
                        # Borrar la línea
                        del lineas[i]
                    else:
                        # Actualizar cantidad
                        linea['cantidad'] = nueva_cantidad
                    
                    modificada = True
                    break
            
            if not modificada:
                return False
            
            return self.guardar(lineas)
        except Exception as e:
            logger.exception(f"Error restando cantidad a línea {linea_id}")
            return False
    
    def borrar_archivo(self) -> bool:
        """Borra el archivo de reposiciones si existe.
        
        Returns:
            True si se borró o no existía, False si hubo error
        """
        try:
            if os.path.exists(REPOSICION_FILE):
                os.remove(REPOSICION_FILE)
            return True
        except Exception as e:
            logger.exception(f"Error borrando archivo {REPOSICION_FILE}")
            return False
    
    def guardar_pendientes_temp(self, ticket_id: int, productos: List[Dict[str, Any]]) -> bool:
        """Acumula productos pendientes en el archivo temporal.
        
        No sobrescribe: añade a los ya existentes. Cada producto se marca con su ticket_id y un temp_id único.
        
        Args:
            ticket_id: ID del ticket
            productos: Lista de productos pendientes [{producto_id, nombre, cantidad}]
            
        Returns:
            True si se guardó correctamente, False si hubo error
        """
        try:
            pendientes = self.cargar_pendientes_temp()
            
            from datetime import datetime
            import uuid
            now_iso = datetime.now().isoformat()
            
            for p in productos:
                # Si el producto ya tiene un temp_id, no lo volvemos a añadir si ya existe en la lista
                # (prevención de duplicados en cancelaciones)
                if 'temp_id' in p:
                    if any(item.get('temp_id') == p['temp_id'] for item in pendientes):
                        continue
                
                p['ticket_id'] = ticket_id
                if 'fecha' not in p:
                    p['fecha'] = now_iso
                if 'temp_id' not in p:
                    p['temp_id'] = str(uuid.uuid4())
                pendientes.append(p)
            
            with open(TEMP_FILE, 'w', encoding='utf-8') as f:
                json.dump(pendientes, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.exception(f"Error guardando pendientes temporales en {TEMP_FILE}")
            return False
    
    def cargar_pendientes_temp(self) -> List[Dict[str, Any]]:
        """Carga los productos pendientes del archivo temporal como lista plana.
        
        Returns:
            Lista de productos pendientes, o lista vacía si no hay archivo o error
        """
        try:
            if not os.path.exists(TEMP_FILE):
                return []
            
            with open(TEMP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Compatibilidad con formato antiguo (dict con ticket_id + productos)
                if isinstance(data, dict):
                    return data.get('productos', [])
                
                # Asegurar que todos tengan un temp_id si se cargan de una versión vieja
                if isinstance(data, list):
                    modificado = False
                    for item in data:
                        if 'temp_id' not in item:
                            item['temp_id'] = str(uuid.uuid4())
                            modificado = True
                    if modificado:
                        with open(TEMP_FILE, 'w', encoding='utf-8') as f_write:
                            json.dump(data, f_write, ensure_ascii=False, indent=2, default=str)
                
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.exception(f"Error cargando pendientes temporales desde {TEMP_FILE}")
            return []
    
    def borrar_pendiente_temp(self, temp_id: str) -> bool:
        """Borra un producto específico del archivo temporal usando su ID único.
        
        Se usa cuando el producto ha sido rellenado correctamente en el formulario.
        
        Args:
            temp_id: ID único (temp_id) del producto a borrar del temp
            
        Returns:
            True si se borró, False si no se encontró o hubo error
        """
        try:
            pendientes = self.cargar_pendientes_temp()
            filtrados = [p for p in pendientes if p.get('temp_id') != temp_id]
            
            if len(pendientes) == len(filtrados):
                return False
            
            if not filtrados:
                return self.borrar_pendientes_temp()
            
            with open(TEMP_FILE, 'w', encoding='utf-8') as f:
                json.dump(filtrados, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.exception(f"Error borrando pendiente temporal ID {temp_id}")
            return False

    def borrar_pendiente_temp_by_ids(self, producto_id: int, ticket_id: int = None) -> bool:
        """Borra productos del temporal por producto_id y ticket_id (compatibilidad).
        
        ADVERTENCIA: Borra TODOS los que coincidan. Usar preferiblemente borrar_pendiente_temp(temp_id).
        """
        try:
            pendientes = self.cargar_pendientes_temp()
            filtrados = [p for p in pendientes 
                         if not (p.get('producto_id') == producto_id 
                                 and (ticket_id is None or p.get('ticket_id') == ticket_id))]
            
            if len(pendientes) == len(filtrados):
                return False
            
            if not filtrados:
                return self.borrar_pendientes_temp()
            
            with open(TEMP_FILE, 'w', encoding='utf-8') as f:
                json.dump(filtrados, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.exception(f"Error borrando pendiente temporal producto {producto_id}")
            return False
    
    def eliminar_coincidencia(self, tipo_id: int, variante_id: Optional[int],
                              diseno_codigo: str) -> bool:
        """Elimina la primera línea del JSON que coincida por tipo, variante y diseño.

        No compara talla ni color: al reponer puede cambiarse esos atributos.

        Returns:
            True si se borró una línea, False si no había coincidencia.
        """
        try:
            lineas = self.cargar()
            for i, linea in enumerate(lineas):
                if (linea.get('tipo_id') == tipo_id and
                    linea.get('variante_id') == variante_id and
                    linea.get('diseno_codigo') == diseno_codigo):
                    del lineas[i]
                    return self.guardar(lineas)
            return False
        except Exception:
            logger.exception("Error eliminando coincidencia de reposición")
            return False

    def borrar_pendientes_temp(self) -> bool:
        """Borra el archivo temporal de pendientes por completo.
        
        Returns:
            True si se borró o no existía, False si hubo error
        """
        try:
            if os.path.exists(TEMP_FILE):
                os.remove(TEMP_FILE)
            return True
        except Exception as e:
            logger.exception(f"Error borrando archivo temporal {TEMP_FILE}")
            return False
