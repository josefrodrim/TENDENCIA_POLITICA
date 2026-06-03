"""
Tests del parser GLR con fixture de La República.
Sin peticiones en vivo — usa larepublica_rss.xml como fuente.
"""
from pathlib import Path

import pytest

from tendencia.scrapers.glr_base import parse_glr_rss
from tendencia.schema import Titular

FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'larepublica_rss.xml'
FECHA   = '2026-06-02'
DIARIO  = 'La República'


@pytest.fixture(scope='module')
def filas() -> list[Titular]:
    xml = FIXTURE.read_text(encoding='utf-8')
    return parse_glr_rss(xml, DIARIO, FECHA)


# ── Filtrado por fecha ──────────────────────────────────────────────────────

def test_excluye_fecha_distinta(filas):
    """El item del 2026-06-01 no debe aparecer."""
    fechas = {f['fecha'] for f in filas}
    assert fechas == {FECHA}


def test_cinco_items_en_fecha(filas):
    """Fixture tiene 5 items en 2026-06-02 y 1 en 2026-06-01."""
    assert len(filas) == 5


# ── Campos obligatorios ─────────────────────────────────────────────────────

def test_todos_tienen_titular(filas):
    for f in filas:
        assert f['titular'], f"Titular vacío: {f['url']}"


def test_todos_tienen_bajada(filas):
    for f in filas:
        assert f['bajada'], f"Bajada vacía: {f['url']}"


def test_todos_tienen_url(filas):
    for f in filas:
        assert f['url'].startswith('https://larepublica.pe/')


def test_diario_correcto(filas):
    assert all(f['diario'] == DIARIO for f in filas)


def test_fecha_correcta(filas):
    assert all(f['fecha'] == FECHA for f in filas)


# ── Sección y opinión ───────────────────────────────────────────────────────

def test_opinion_detectada_en_columnistas(filas):
    col = [f for f in filas if f['seccion'] == 'columnistas']
    assert len(col) == 1
    assert col[0]['es_opinion'] is True


def test_politica_no_es_opinion(filas):
    pol = [f for f in filas if f['seccion'] == 'politica']
    assert len(pol) >= 2
    assert all(not f['es_opinion'] for f in pol)


def test_seccion_extraida_correctamente(filas):
    secciones = {f['seccion'] for f in filas}
    assert 'politica' in secciones
    assert 'columnistas' in secciones
    assert 'economia' in secciones


# ── Foto ────────────────────────────────────────────────────────────────────

def test_media_content_marca_foto(filas):
    """Item 1 tiene media:content → tiene_foto=True."""
    item1 = next(f for f in filas if 'hnews-100001' in f['url'])
    assert item1['tiene_foto'] is True


def test_image_image_marca_foto(filas):
    """Item del debate tiene image:image → tiene_foto=True."""
    debate = next(f for f in filas if 'hnews-100005' in f['url'])
    assert debate['tiene_foto'] is True


def test_sin_imagen_tiene_foto_false(filas):
    """Item 2 (Roberto Sánchez) no tiene imagen."""
    item2 = next(f for f in filas if 'hnews-100002' in f['url'])
    assert item2['tiene_foto'] is False


# ── Posición ────────────────────────────────────────────────────────────────

def test_posicion_incremental(filas):
    posiciones = [f['posicion'] for f in filas]
    assert posiciones == list(range(1, len(filas) + 1))


# ── Candidato default ───────────────────────────────────────────────────────

def test_candidato_default_ninguno(filas):
    """El scraper NO hace detección — eso es tarea del pipeline."""
    assert all(f['candidato'] == 'ninguno' for f in filas)


# ── Campos de codificación vacíos ───────────────────────────────────────────

def test_valencia_sugerida_nula(filas):
    assert all(f['valencia_sugerida'] is None for f in filas)


def test_valencia_humana_nula(filas):
    assert all(f['valencia_humana'] is None for f in filas)
