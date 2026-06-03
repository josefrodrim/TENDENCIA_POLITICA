"""
Parser base para la plataforma GLR (Grupo La República).
Cubre: La República, El Popular, y otros sitios del grupo.

RSS estructura: /<seccion>/YYYY/MM/DD/<slug>
Campos: title (titular), description (bajada), link (URL+fecha),
        media:content / image:image (tiene_foto), category (sección).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from tendencia.scrapers.base import ScraperError, get_html
from tendencia.schema import Titular, fila_vacia

_NS = {
    'image': 'http://www.google.com/schemas/sitemap-image/1.1',
    'media': 'http://search.yahoo.com/mrss/',
    'dc':    'http://purl.org/dc/elements/1.1/',
}

_OPINION = frozenset({'columnistas', 'opinion', 'editorial', 'carlincatura'})

_RE_FECHA   = re.compile(r'/(\d{4})/(\d{2})/(\d{2})/')
_RE_SECCION = re.compile(r'https?://[^/]+/([^/?#]+)')


def _fecha_desde_url(url: str) -> str:
    m = _RE_FECHA.search(url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ''


def _seccion_desde_url(url: str) -> str:
    m = _RE_SECCION.search(url)
    return m.group(1) if m else ''


def parse_glr_rss(xml_text: str, diario: str, fecha: str) -> list[Titular]:
    """
    Parsea el XML RSS de un diario GLR y devuelve las filas
    correspondientes a 'fecha' (YYYY-MM-DD en hora Perú, ya embebida en la URL).
    candidato='ninguno' en todas las filas — la detección la hace el pipeline.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ScraperError(f"[{diario}] XML inválido: {e}") from e

    filas: list[Titular] = []
    posicion = 0

    for item in root.iter('item'):
        url = (item.findtext('link') or item.findtext('guid') or '').strip()
        if not url or _fecha_desde_url(url) != fecha:
            continue

        posicion += 1
        seccion = _seccion_desde_url(url)
        tiene_foto = (
            item.find('image:image', _NS) is not None
            or item.find('media:content', _NS) is not None
        )

        fila = fila_vacia(diario, fecha, url=url)
        fila.update({
            'titular':    (item.findtext('title')       or '').strip(),
            'bajada':     (item.findtext('description') or '').strip(),
            'seccion':    seccion,
            'es_opinion': seccion in _OPINION,
            'posicion':   posicion,
            'tiene_foto': tiene_foto,
        })
        filas.append(fila)

    return filas


def fetch_glr(diario: str, rss_urls: list[str], fecha: str) -> list[Titular]:
    """
    Descarga uno o varios feeds RSS GLR, parsea y deduplica por URL.
    Lanza ScraperError si todos los feeds fallan.
    """
    errores: list[str] = []
    vistas:  set[str]  = set()
    todas:   list[Titular] = []

    for rss_url in rss_urls:
        try:
            xml_text = get_html(rss_url)
        except Exception as e:
            errores.append(str(e))
            continue

        for fila in parse_glr_rss(xml_text, diario, fecha):
            if fila['url'] not in vistas:
                vistas.add(fila['url'])
                todas.append(fila)

    if not todas and errores:
        raise ScraperError(f"[{diario}] Todos los feeds fallaron: {'; '.join(errores)}")

    return todas
