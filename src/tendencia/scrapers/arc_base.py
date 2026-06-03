"""
Parser base para la plataforma Arc Publishing (Grupo El Comercio / GEC).
Cubre: El Comercio, Gestión, Correo, Ojo.

RSS: <base>/arc/outboundfeeds/rss/?outputType=xml  (100 items)

Diferencia clave vs GLR: la URL Arc NO contiene la fecha.
La fecha se extrae de pubDate (UTC) y se convierte a hora Perú (UTC-5).
Ejemplo:
  pubDate "Wed, 03 Jun 2026 01:00:00 +0000"  →  20:00 del 02 Jun en Perú
  → fecha_peru = "2026-06-02"  ✓
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime

from tendencia.scrapers.base import ScraperError, get_html
from tendencia.schema import Titular, fila_vacia

_PERU_TZ  = timezone(timedelta(hours=-5))
_NS       = {
    'media': 'http://search.yahoo.com/mrss/',
    'dc':    'http://purl.org/dc/elements/1.1/',
}
_OPINION      = frozenset({'opinion', 'columnistas', 'editorial', 'columna'})
_RE_SECCION   = re.compile(r'https?://[^/]+/([^/?#]+)')


def _fecha_peru(pubdate: str) -> str:
    """RFC-2822 UTC → fecha en hora Perú (UTC-5)."""
    try:
        return parsedate_to_datetime(pubdate).astimezone(_PERU_TZ).strftime('%Y-%m-%d')
    except Exception:
        return ''


def _seccion(url: str) -> str:
    m = _RE_SECCION.search(url)
    return m.group(1) if m else ''


def parse_arc_rss(xml_text: str, diario: str, fecha: str) -> list[Titular]:
    """
    Parsea RSS Arc y devuelve filas para la fecha indicada (hora Perú).
    candidato='ninguno' — la detección la hace el pipeline.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ScraperError(f"[{diario}] XML inválido: {e}") from e

    filas: list[Titular] = []
    posicion = 0

    for item in root.iter('item'):
        pubdate = (item.findtext('pubDate') or '').strip()
        if _fecha_peru(pubdate) != fecha:
            continue

        url      = (item.findtext('link') or item.findtext('guid') or '').strip()
        sec      = _seccion(url)
        tiene_foto = (
            item.find('media:content',   _NS) is not None
            or item.find('media:thumbnail', _NS) is not None
        )

        posicion += 1
        fila = fila_vacia(diario, fecha, url=url)
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


def fetch_arc(diario: str, rss_url: str, fecha: str) -> list[Titular]:
    """Descarga y parsea un feed Arc para la fecha dada."""
    try:
        xml_text = get_html(rss_url)
    except Exception as e:
        raise ScraperError(f"[{diario}] Error al descargar RSS: {e}") from e
    return parse_arc_rss(xml_text, diario, fecha)
