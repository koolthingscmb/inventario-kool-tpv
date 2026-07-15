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
        """Guarda productos pendientes de anotar en el archivo temporal.
        
        Args:
            ticket_id: ID del ticket
            productos: Lista de productos pendientes [{producto_id, nombre, cantidad}]
            
        Returns:
            True si se guardó correctamente, False si hubo error
        """
        try:
            data = {
                'ticket_id': ticket_id,
                'productos': productos,
                'fecha': datetime.now().isoformat()
            }
            
            with open(TEMP_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.exception(f"Error guardando pendientes temporales en {TEMP_FILE}")
            return False
    
    def cargar_pendientes_temp(self) -> Optional[Dict[str, Any]]:
        """Carga los productos pendientes del archivo temporal.
        
        Returns:
            Dict con ticket_id y productos, o None si no hay archivo o error
        """
        try:
            if not os.path.exists(TEMP_FILE):
                return None
            
            with open(TEMP_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Error cargando pendientes temporales desde {TEMP_FILE}")
            return None
    
    def borrar_pendientes_temp(self) -> bool:
        """Borra el archivo temporal de pendientes.
        
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
