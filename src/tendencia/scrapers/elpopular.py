"""
Scraper El Popular — plataforma GLR (mismo base que La República).
RSS: /rss/home.xml  250 items.
"""
from __future__ import annotations

from tendencia.scrapers.glr_base import fetch_glr
from tendencia.schema import Titular

_DIARIO = 'El Popular'
_RSS = ['https://www.elpopular.pe/rss/home.xml']


def fetch(fecha: str) -> list[Titular]:
    return fetch_glr(_DIARIO, _RSS, fecha)
