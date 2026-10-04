"""Componente IMÁGENES de la SUBIDA a Shopify.

Gestiona dos listas:
  - locales: archivos elegidos desde el ordenador ({path, alt}).
  - web: imágenes que ya están en Shopify al editar un producto ({url, alt}).

Ambas muestran miniatura. Las de Shopify se descargan en segundo plano con una
versión reducida de la CDN para no bloquear la pantalla.
"""
import io
import logging
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import customtkinter as ctk
import requests

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

TAM_MINIATURA = 56
ANCHO_DESCARGA = 100


def _url_miniatura(url: str) -> str:
    """Devuelve la misma URL de la CDN de Shopify pidiendo una versión pequeña."""
    p = urlsplit(url)
    q = dict(parse_qsl(p.query))
    q["width"] = str(ANCHO_DESCARGA)
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))


class SelectorImagenes:
    """Sección IMÁGENES: botón de selección y lista con miniaturas."""

    def __init__(self, parent, bg: str, bg_medium: str, secondary: str):
        self._bg = bg
        self._bg_medium = bg_medium
        self._secondary = secondary

        self._locales: List[Dict[str, Any]] = []   # {path, alt}
        self._web: List[Dict[str, Any]] = []        # {url, alt}
        self._thumb_refs = []                       # miniaturas locales (evita GC)
        self._cache: Dict[str, Any] = {}            # url -> PhotoImage ya descargada
        self._descargando = set()
        self._fallidas = set()
        self._labels_web: Dict[str, List[tk.Label]] = {}

        self.frame = tk.Frame(parent, bg=bg)

        top = tk.Frame(self.frame, bg=bg)
        top.pack(fill="x", padx=10)
        ctk.CTkButton(top, text="SELECCIONAR ARCHIVOS", width=200, height=34,
                      fg_color=secondary, command=self._add_images).pack(side="left")
        self._lista = tk.Frame(self.frame, bg=bg)
        self._lista.pack(fill="x", padx=10, pady=5)

        # Hueco transparente que reserva el tamaño de la miniatura mientras se descarga
        self._vacia = tk.PhotoImage(master=parent, width=TAM_MINIATURA, height=TAM_MINIATURA)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def obtener_locales(self) -> List[Dict[str, Any]]:
        return [dict(i) for i in self._locales]

    def obtener_web(self) -> List[Dict[str, Any]]:
        return [dict(i) for i in self._web]

    def set_web(self, imagenes: List[Dict[str, Any]]):
        """Sustituye las imágenes ya existentes en Shopify (no toca las locales)."""
        self._web = list(imagenes)
        self._fallidas.clear()
        self._render()

    def limpiar(self):
        self._locales.clear()
        self._web.clear()
        self._render()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _add_images(self):
        paths = filedialog.askopenfilenames(
            title="Selecciona imágenes",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")]
        )
        for p in paths:
            self._locales.append({"path": p, "alt": ""})
        self._render()

    def _del_image(self, idx):
        self._locales.pop(idx)
        self._render()

    def _del_web_image(self, idx):
        self._web.pop(idx)
        self._render()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def _render(self):
        for child in self._lista.winfo_children():
            child.destroy()
        self._thumb_refs.clear()
        self._labels_web = {}

        for idx, img in enumerate(self._locales):
            row_f = tk.Frame(self._lista, bg=self._bg_medium)
            row_f.pack(fill="x", pady=3)
            if PIL_OK:
                try:
                    pil = Image.open(img["path"]); pil.thumbnail((TAM_MINIATURA, TAM_MINIATURA))
                    thumb = ImageTk.PhotoImage(pil)
                    self._thumb_refs.append(thumb)
                    tk.Label(row_f, image=thumb, bg=self._bg_medium).pack(side="left", padx=8)
                except (OSError, ValueError):
                    logger.warning(f"No se pudo generar la miniatura de {img['path']}")
            name = img["path"].split("/")[-1]
            tk.Label(row_f, text=name, fg="#FFF", bg=self._bg_medium,
                     font=("Helvetica", 10), width=30, anchor="w").pack(side="left", padx=5)
            alt = ctk.CTkEntry(row_f, placeholder_text="alt text", width=220, height=28)
            alt.insert(0, img["alt"])
            alt.bind("<FocusOut>", lambda e, i=idx, w=alt: self._locales[i].update(alt=w.get()))
            alt.pack(side="left", padx=8)
            ctk.CTkButton(row_f, text="✕", width=30, height=28, fg_color="#8b1a1a",
                          command=lambda i=idx: self._del_image(i)).pack(side="right", padx=8)

        for idx, img in enumerate(self._web):
            row_f = tk.Frame(self._lista, bg=self._bg_medium)
            row_f.pack(fill="x", pady=3)
            if PIL_OK:
                url = img["url"]
                lbl = tk.Label(row_f, image=self._cache.get(url, self._vacia), bg=self._bg_medium)
                lbl.pack(side="left", padx=8)
                if url not in self._cache:
                    self._labels_web.setdefault(url, []).append(lbl)
            tk.Label(row_f, text=f"☁ {img['url'].split('/')[-1][:40]}", fg="#8cf",
                     bg=self._bg_medium, font=("Helvetica", 10), anchor="w").pack(side="left", padx=8)
            tk.Label(row_f, text="(ya en Shopify)", fg="#666", bg=self._bg_medium,
                     font=("Helvetica", 9, "italic")).pack(side="left", padx=5)
            ctk.CTkButton(row_f, text="✕", width=30, height=28, fg_color="#8b1a1a",
                          command=lambda i=idx: self._del_web_image(i)).pack(side="right", padx=8)

        self._lanzar_descargas()

    # ------------------------------------------------------------------
    # Miniaturas de Shopify (segundo plano)
    # ------------------------------------------------------------------

    def _lanzar_descargas(self):
        if not PIL_OK:
            return
        pendientes = []
        for img in self._web:
            url = img["url"]
            if url in self._cache or url in self._descargando or url in self._fallidas or url in pendientes:
                continue
            pendientes.append(url)
        if not pendientes:
            return
        self._descargando.update(pendientes)
        threading.Thread(target=self._descargar, args=(pendientes,), daemon=True).start()

    def _descargar(self, urls: List[str]):
        for url in urls:
            pil = None
            try:
                r = requests.get(_url_miniatura(url), timeout=15)
                r.raise_for_status()
                pil = Image.open(io.BytesIO(r.content))
                pil.load()
                pil.thumbnail((TAM_MINIATURA, TAM_MINIATURA))
            except (requests.RequestException, OSError, ValueError) as e:
                logger.error(f"No se pudo descargar la miniatura {url}: {e}")
            try:
                self.frame.after(0, lambda u=url, p=pil: self._miniatura_lista(u, p))
            except (tk.TclError, RuntimeError) as e:
                logger.debug(f"Miniatura descartada, la ventana ya no está activa: {e}")
                return

    def _miniatura_lista(self, url: str, pil):
        """Se ejecuta en el hilo de Tk: crea la PhotoImage y actualiza las filas."""
        self._descargando.discard(url)
        if pil is None:
            self._fallidas.add(url)
            return
        if not self.frame.winfo_exists():
            return
        foto = ImageTk.PhotoImage(pil)
        self._cache[url] = foto
        for lbl in self._labels_web.pop(url, []):
            if lbl.winfo_exists():
                lbl.configure(image=foto)
