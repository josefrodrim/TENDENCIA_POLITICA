"""Scraper Gestión — plataforma Arc/GEC."""
from __future__ import annotations

from tendencia.scrapers.arc_base import fetch_arc
from tendencia.schema import Titular

_DIARIO  = 'Gestión'
_RSS_URL = 'https://gestion.pe/arc/outboundfeeds/rss/?outputType=xml'


def fetch(fecha: str) -> list[Titular]:
    return fetch_arc(_DIARIO, _RSS_URL, fecha)
