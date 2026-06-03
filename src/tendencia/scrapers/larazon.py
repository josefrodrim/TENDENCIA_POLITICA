"""
Scraper La Razón — HTML scraping (WordPress / Astra theme).
No expone RSS. Fecha disponible via <time datetime="YYYY-MM-DDTHH:MM:SS-05:00">.

Selectores:
  Artículos: .wp-block-post (query loop de WordPress)
  Título:    .wp-block-post-title a
  Fecha:     time[datetime]  → datetime[:10] ya en hora Perú
  Foto:      img dentro del contenedor del post
  Bajada:    .wp-block-post-excerpt__excerpt  (si existe)
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from tendencia.scrapers.base import ScraperError, get_html
from tendencia.schema import Titular, fila_vacia

_DIARIO  = 'La Razón'
_URL     = 'https://larazon.pe/'
_OPINION = frozenset({'opinion', 'editorial', 'columna', 'columnistas', 'analisis'})


def _seccion_desde_url(url: str) -> str:
    """larazon.pe/<slug>/ — sin sección en URL; se infiere del nav o se deja vacío."""
    return ''


def parse_larazon(html: str, fecha: str) -> list[Titular]:
    soup = BeautifulSoup(html, 'lxml')
    filas: list[Titular] = []
    posicion = 0

    for post in soup.select('.wp-block-post'):
        time_tag = post.select_one('time[datetime]')
        if not time_tag:
            continue
        fecha_art = (time_tag.get('datetime') or '')[:10]
        if fecha_art != fecha:
            continue

        title_a = post.select_one('.wp-block-post-title a')
        if not title_a:
            continue

        posicion += 1
        url     = title_a.get('href', '').strip()
        titular = title_a.get_text(strip=True)
        bajada_tag = post.select_one('.wp-block-post-excerpt__excerpt, .entry-summary, p.excerpt')
        bajada  = bajada_tag.get_text(strip=True) if bajada_tag else ''
        tiene_foto = bool(post.select_one('img'))

        # Categoría: si el post tiene class tipo "category-opinion" en el <li>
        cls_str = ' '.join(post.get('class', []))
        sec = next((s for s in _OPINION if s in cls_str.lower()), '')

        fila = fila_vacia(_DIARIO, fecha, url=url)
        fila.update({
            'titular':    titular,
            'bajada':     bajada,
            'seccion':    sec,
            'es_opinion': bool(sec),
            'posicion':   posicion,
            'tiene_foto': tiene_foto,
        })
        filas.append(fila)

    return filas


def fetch(fecha: str) -> list[Titular]:
    try:
        html = get_html(_URL)
    except Exception as e:
        raise ScraperError(f"[{_DIARIO}] Error al descargar: {e}") from e
    return parse_larazon(html, fecha)
