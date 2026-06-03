"""
Scraper Diario Uno — WordPress RSS estándar.
RSS: /feed/  (~10 items)
URL estructura: diariouno.pe/YYYY/MM/DD/slug  → fecha extraída del path.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from tendencia.scrapers.base import ScraperError, get_html
from tendencia.schema import Titular, fila_vacia

_DIARIO    = 'Diario Uno'
_RSS_URL   = 'https://diariouno.pe/feed/'
_OPINION   = frozenset({'opinion', 'editorial', 'columna', 'columnistas'})
_RE_FECHA  = re.compile(r'/(\d{4})/(\d{2})/(\d{2})/')
_RE_SECCION = re.compile(r'https?://[^/]+/(?:\d{4}/\d{2}/\d{2}/)?([^/?#]+)')


def _fecha(url: str) -> str:
    m = _RE_FECHA.search(url)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ''


def _seccion(url: str) -> str:
    # WordPress: diariouno.pe/YYYY/MM/DD/slug → extraer categoría del feed <category>
    # Como fallback usamos el primer segmento no-fecha
    m = _RE_FECHA.search(url)
    if m:
        # URL tiene fecha; sección viene del tag <category> en el RSS
        return ''
    seg = _RE_SECCION.search(url)
    return seg.group(1) if seg else ''


def fetch(fecha: str) -> list[Titular]:
    try:
        xml_text = get_html(_RSS_URL)
    except Exception as e:
        raise ScraperError(f"[{_DIARIO}] Error RSS: {e}") from e

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ScraperError(f"[{_DIARIO}] XML inválido: {e}") from e

    filas: list[Titular] = []
    posicion = 0

    for item in root.iter('item'):
        url = (item.findtext('link') or item.findtext('guid') or '').strip()
        if _fecha(url) != fecha:
            continue

        posicion += 1
        # En WordPress el RSS incluye <category> con la sección
        categorias = [c.text or '' for c in item.findall('category')]
        sec = (categorias[0].lower().strip() if categorias else '')
        tiene_foto = '<img' in (item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or '')

        fila = fila_vacia(_DIARIO, fecha, url=url)
        fila.update({
            'titular':    (item.findtext('title')       or '').strip(),
            'bajada':     (item.findtext('description') or '').strip(),
            'seccion':    sec,
            'es_opinion': sec in _OPINION,
            'posicion':   posicion,
            'tiene_foto': tiene_foto,
        })
        filas.append(fila)

    return filas
