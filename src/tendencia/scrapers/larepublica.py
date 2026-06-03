"""
Scraper La República — plataforma GLR.

Feeds RSS:
  /rss/home.xml     200 items, portada general
  /rss/politica.xml  66 items, sección política (superset parcial)
Ambos se fusionan y deduplan por URL.
"""
from __future__ import annotations

from tendencia.scrapers.glr_base import fetch_glr
from tendencia.schema import Titular

_DIARIO = 'La República'
_RSS = [
    'https://larepublica.pe/rss/home.xml',
    'https://larepublica.pe/rss/politica.xml',
]


def fetch(fecha: str) -> list[Titular]:
    """
    Devuelve titulares de La República para la fecha dada (YYYY-MM-DD).
    candidato='ninguno' — la detección la hace el pipeline.
    """
    return fetch_glr(_DIARIO, _RSS, fecha)
