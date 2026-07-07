"""Panel overlay para Devoluciones — Reescrito sin SelectionOverlayTemplate.

Este módulo define DevolucionesPanel (interfaz) y DevolucionAction.
Usa SearchablePaginatedNavList para garantizar el mismo comportamiento que StockSubView.
"""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import logging

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

from kool_tpv.base_datos.producto_service import ProductoService
from kool_tpv.base_datos.db_wrapper import Database
from kool_tpv.modulos.tpv.devoluciones_service import DevolucionesService
from kool_tpv.utils.widgets.searchable_paginated_navlist import SearchablePaginatedNavList
from kool_tpv.utils.factories.button_factory import ButtonFactory


class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específico para de"""Panel overlay para Devoluciones — Reescrito sin SelectionOverlayTemplate.

Este módulo define DevolucionesPanel (interfaz) y DevolucionAction.
Usa SearchablePaginatedNavList para gaNo
Este módulo define DevolucionesPanel (interfaz) y DevolucionAction.
Usa Sea   Usa SearchablePaginatedNavList para garantizar el mismo comportamiewi"""
from __future__ import annotations
from typing import Any, Optionalot
        super()fr_ifrom typing import Any, Optional,a"import logging

import customtkinter as ctk = db
        selfimport tkinter as tk
from n_from tkinter import  
from kool_tpv.base_daFalfrom kool_tpv.base_datos.db_wrapper import Database
from kool_t  from kool_tpv.modulos.tpv.devoluciones_service iductfrom kool_tpv.utils.widgets.searchable_paginated_navlist import Searchabrofrom kool_tpv.utils.factories.button_flucionesPanel')
            self.producto_service = N

class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualmente."""
  
Este módulo define DevolucionesPanel (interfaz) y DevolucionAction.
Usa SearchablePaginatedNavList para gaNo
)
 Usa SearchablePaginatedNavList para gaNo
Este módulo define DevolupaEste módulo define DevolucionesPanel (  Usa Sea   Usa SearchablePaginatedNavList para garantizar el mismo c
 from __future__ import annotations
from typing import Any, O 34, "bold"),
         from typing import Any, Optionalo          super()fr_ifrom typing imto
import customtkinter as ctk =        # Subtítulo
        self.subtit        selfimport tkinter as t  from n_from tkinter impor
       from kool_tpv.basuce EAN o nofrom kool_t  from kool_tpv.modulos.tpv.devoluciones_service iductfrom koollo            self.producto_service = N

class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualmente."""
  
Este módulo define DevolucionesPanel (interfama
class DevolucionesPanel(cansparent")
     """Overlay específ"""C    """Ove"t  
Este módulo define DevolucionesPanel (interfaz) y DevolucisearcUsa SearchablePaginatedNavList para gaNo
)
 Usa SearchablePaginated  )
 Usa SearchablePaginatedNavList para    tEste módulo define DevolupaEste módulo   from __future__ import annotations
from typing import Any, O 34, "bold"),
         from typing import Any, Optionalo          super()ff.from typing import Any, O 34, "bolx=         from typing import Any, Optialimport customtkinter as ctk =        # Subtítulo
        self.subtit        sej        self.subtit        selfimport tkinter acep       from koelf.aceptar_btn = ctk.CTkButton(
            self.controls_frame
class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualmente."""
  
Este módulo define DevolucionesPanel (in       font=("Roboto", 16, "bold"),
        
Este módulo define DevolucionesPanel (interfama
class Devoeptarclass DevolucionesPanel(cansparent")
     """Ovn      """Overlay específ"""C    """ctEste módulo define DevolucionesPanel (inam)
 Usa SearchablePaginated  )
 Usa SearchablePaginatedNavList para    tEste módulo define DevolupaEste400" Usa Se       hover_color="#from typing import Any, O 34, "bold"),
         from typing import Any, Optionalo          super()ff.from typing impont         from typing import Any, Optn.p        self.subtit        sej        self.subtit        selfimport tkinter acep       from koelf.aceptar_btn = ctk.CTkButton(
            self.controls_frame
class DevolucionesPanel(ctob            self.controls_frame
class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualreclass DevolucionesPanel(ctk.CTav    "
        columns = [
            (  
Este módulo define DevolucionesPan, 400, "Nombre"),
        E          
Este módulo define DevolucionesPanel (interfama
class Dev),
       Este m?tclass Devoeptarclass DevolucionesPanel(cansparefr     """Ovn      """Overlay específ"""C    """ctE_c Usa SearchablePaginated  )
 Usa SearchablePaginatedNavList para    tEste módulo define Devte Usa SearchablePaginatedNant         from typing import Any, Optionalo          super()ff.from typing impont         from typing import Any, Optn.p        self.subtit    pr            self.controls_frame
class DevolucionesPanel(ctob            self.controls_frame
class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualreclass DevolucionesPanel(ctk.CTav    "
        columns = [taclass DevolucionesPanel(ctob  anclass DevolucionesPanel(ctk.CTkFrame):
    """Overlay espeo     """Overlay específ"""C    """Oveng        columns = [
            (  
Este módulo define DevolucionesPan, 400, "Nombre"),
   ar     xto)

    def _Este módulo dos        E          
Este módulo define Devolucioneservicio de productos class Dev),
       Este m?tclass Devoeptarclas         Estt  Usa.producto_service:
            return []
        # Usamos listar_productos que ya tiene el fix de EAN/SKU en el repo
        return self.prodclass DevolucionesPanel(ctob            self.controls_frame
class DevolucionesPanel(ctk.CTkFrame):
    """Overlay específ"""C    """Overlinterfaz manualreclass DevolucionesPanel(ctk.CTav    "
        columns = [taclass DevolucionesPanel(ctob  anclass Devoluc         "cclass DevolucionesPanel(ctk.CTkFrame):
    """Overlay espembre') or '',
            "tipo": item.ge        columns = [taclass DevolucionesPanel(ctob  anclass DevolucionesPanel(ctk.CTkFrame):
al    """Overlay espeo     """Overlay específ"""C    """Oveng        columns = [
          ho            (  
Este módulo define DevolucionesPan, 400, "Nombre"),
   ar    reEste módulo dei   ar     xto)

    def _Este      self._visible = Tr
    def _EstCarEste módulo define Devolucioneservicio dr_bu       Este m?tclass Devoeptarclas         Estt  Usa.producto_ l            return []
        # Usamos listar_productos que ya tiene eer        # Usamos lisha        return self.prodclass DevolucionesPanel(ctob            self.contr_pclass DevolucionesPanel(ctk.CTkFrame
    def hide(self):
        """Oculta el overla    """Overlay específ"""C    """Ove          columns = [taclass DevolucionesPanel(ctob  anclass Devoluc         "cclass Dev            """Overlay espembre') or '',
            "tipo": item.ge        columns = [taclass DevolucionesPanel(ctob  ancbl            "tipo": item.ge      al    """Overlay espeo     """Overlay específ"""C    """Oveng        columns = [
            """Al pulsar el botón A?         ho            (  
Este módulo define DevolucionesPan, 400, "Nombre"),  Este módulo define Devoluse   ar d_to_devolucion(selected)

    def _add_to_devo
    def _Este      self._visible = Tr
 óg    def _EstCarEste módulo define Do         # Usamos listar_productos que ya tiene eer        # Usamos lisha        return self.prodclass DevolucionesPanel(ctob            self.cont')    def hide(self):
        """Oculta el overla    """Overlay específ"""C    """Ove          columns = [taclass DevolucionesPanel(ctob  anclass Devoluc         "cclass Dev           AL      r.pvp,0.0) AS             "tipo": item.ge        columns = [taclass DevolucionesPanel(ctob  ancbl            "tipo": item.ge      al    """Overlay espeo     """Overlay específ"""C    """Oveng        colum              """Al pulsar el botón A?         ho            (  
Este módulo define DevolucionesPan, 400, "Nombre"),  Este módulo define Devoluse   ar d_to_devolucion(selected)

    def _add_to_roEste módulo define DevolucionesPan, 400, "Nombre"),  E)
        
    def _add_to_devo
    def _Este      self._v         full_prod = product_data

            if hasattr(self, 'de    def _Este      )  óg    def _EstCarEste módulo defi          """Oculta el overla    """Overlay específ"""C    """Ove          columns = [taclass DevolucionesPanel(ctob  anclass Devoluc         "cclass Dev           AL      r.pvp,0.0) AS             "tipo": itf Este módulo define DevolucionesPan, 400, "Nombre"),  Este módulo define Devoluse   ar d_to_devolucion(selected)

    def _add_to_roEste módulo define DevolucionesPan, 400, "Nombre"),  E)
        
    def _add_to_devo
    def _Este      self._v         full_prod = product_data

            if hasattr(self, 'de    def _Este      )  óg    def _EstCarEste módulo defi          """Oculta el overla    """Overlay específ"""C    """Ove     
 
    def _add_to_roEste módulo define DevolucionesPan, Error añadiendo item a devolución")

    def _open_client        
    def _add_to_devo
    def clientes."""
        try:
               defat    def _Este      en
            if hasattr(self, 'de    def _Este             se
    def _add_to_roEste módulo define DevolucionesPan, 400, "Nombre"),  E)
        
    def _add_to_devo
    def _Este      self._v         full_prod = product_data

            if hasattr(self, 'de    def _Este      )  óg    def _EstCarEste módulo defi          """Oculta el overla    """Overlay específ"""C    """Ove     
 
    def _add_to_roEste módulo define DevolucionesPan, Error añadiendo item a devErr        
    def _add_to_devo
    def _Este      self._v         full_pro""Acción q    def el panel de d
            if hasattr(self, 'de    def _Este      )  ógaba 
    def _add_to_roEste módulo define DevolucionesPan, Error añadiendo item a devolución")

    def _open_client        
    def _add_to_devo
    def cliennesP
    def _open_client        
    def _add_to_devo
    def clientes."""
        try:
             def _add_toool_tpv.modulo    defctions.permiso        try:
      is                         if hasattr(self, 'de    def          if not check_permiso(self.carrito_service, 'permiso_de        
    def _add_to_devo
    def _Este      self._v         full_pro N    def      def _Este      an
            if hasattr(self, 'de    def _Este             se 
    def _add_to_roEste módulo define DevolucionesPan, Error añadiendo item a devErr        
    def _add_to_devo
    def _Este      self._v         full_pr        def _add_to_devo
    def _Este      self._v         full_pro""Acción q    def el panel  A    def _Este      li            if hasattr(self, 'de    def _Este      )  ógaba 
    def           def ide_wrapper():
                    try:
              
    def _open_client        
    def _add_to_devo
    def cliennesP
    def _open_client  s
     def _ad        original_h    def cliennesP
       def _open_cle     def _add_to_devo
    de      ._panel.show()
          try:
      io               logging.exception('DevolucionAction: error al ejecutar')
