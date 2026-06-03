"""
Scraper Expreso — HTML scraping (UIkit framework).
El RSS Arc devuelve 0 items. La fecha no está en URL ni en <time> completo
(solo muestra hora). Se usa la fecha recibida como parámetro (captura a las 07:00).

Selectores:
  Lista "Últimas noticias": dl.uk-description-expreso-list > dd > a > h4
  Tarjetas de sección:      a.uk-link-reset[href] > h3.uk-card-title
  Foto:                     figure img dentro del ancestro de la tarjeta
  Sección:                  primer segmento del path de la URL
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from tendencia.scrapers.base import ScraperError, get_html
from tendencia.schema import Titular, fila_vacia

_DIARIO  = 'Expreso'
_URL     = 'https://www.expreso.com.pe/'
_OPINION = frozenset({'opinion', 'columnistas', 'editorial'})

import re
_RE_SECCION = re.compile(r'https?://[^/]+/([^/?#]+)')


def _seccion(url: str) -> str:
    m = _RE_SECCION.search(url)
    s = m.group(1) if m else ''
    # excluir segmentos que no son secciones
    return s if s not in ('tag', 'search', '') else ''


def parse_expreso(html: str, fecha: str) -> list[Titular]:
    soup = BeautifulSoup(html, 'lxml')
    seen: set[str] = set()
    filas: list[Titular] = []
    posicion = 0

    def _agregar(url: str, titular: str, bajada: str, tiene_foto: bool) -> None:
        nonlocal posicion
        if not url or not titular or url in seen:
            return
        seen.add(url)
        posicion += 1
        sec = _seccion(url)
        fila = fila_vacia(_DIARIO, fecha, url=url)
        fila.update({
            'titular':    titular,
            'bajada':     bajada,
            'seccion':    sec,
            'es_opinion': sec in _OPINION,
            'posicion':   posicion,
            'tiene_foto': tiene_foto,
        })
        filas.append(fila)

    # 1) Lista "Últimas noticias" (dl.uk-description-expreso-list)
    for dl in soup.select('dl.uk-description-expreso-list'):
        for dd in dl.select('dd'):
            a = dd.select_one('a[href]')
            if not a:
                continue
            h = a.select_one('h4, h3, h2')
            _agregar(
                url=a.get('href', ''),
                titular=h.get_text(strip=True) if h else a.get_text(strip=True),
                bajada='',
                tiene_foto=bool(dd.select_one('img')),
            )

    # 2) Tarjetas (a.uk-link-reset con h3.uk-card-title)
    for a in soup.select('a.uk-link-reset[href]'):
        h = a.select_one('h3.uk-card-title, h2.uk-card-title')
        if not h:
            continue
        parent = a.parent
        bajada_tag = parent.select_one('p') if parent else None
        _agregar(
            url=a.get('href', ''),
            titular=h.get_text(strip=True),
            bajada=bajada_tag.get_text(strip=True) if bajada_tag else '',
            tiene_foto=bool(a.select_one('img') or (parent and parent.select_one('img'))),
        )

    return filas


def fetch(fecha: str) -> list[Titular]:
    from datetime import date
    if fecha != date.today().isoformat():
        # El HTML de portada no tiene fecha en URL ni en <time> — no sirve para histórico.
        # Para fechas pasadas usar: python -m tendencia.cli recuperar --fecha <fecha>
        raise ScraperError(
            f"[{_DIARIO}] Solo captura el día actual. "
            f"Para histórico usar: tendencia.cli recuperar --fecha {fecha}"
        )
    try:
        html = get_html(_URL)
    except Exception as e:
        raise ScraperError(f"[{_DIARIO}] Error al descargar: {e}") from e
    return parse_expreso(html, fecha)
