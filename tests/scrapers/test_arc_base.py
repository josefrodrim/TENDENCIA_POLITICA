"""
Tests del parser Arc con fixture de El Comercio.
Cubre también Gestión, Correo y Ojo (mismo base).
Sin peticiones en vivo.
"""
from pathlib import Path

import pytest

from tendencia.scrapers.arc_base import _fecha_peru, parse_arc_rss
from tendencia.schema import Titular

FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'arc_rss.xml'
FECHA   = '2026-06-02'
DIARIO  = 'El Comercio'


@pytest.fixture(scope='module')
def filas() -> list[Titular]:
    xml = FIXTURE.read_text(encoding='utf-8')
    return parse_arc_rss(xml, DIARIO, FECHA)


# ── Conversión UTC → hora Perú ──────────────────────────────────────────────

def test_pubdate_mismo_dia_utc():
    """14:00 UTC del 02 Jun = 09:00 Perú del 02 Jun → 2026-06-02."""
    assert _fecha_peru('Tue, 02 Jun 2026 14:00:00 +0000') == '2026-06-02'


def test_pubdate_borde_tarde_utc_es_peru_mismo_dia():
    """03 Jun 01:00 UTC = 02 Jun 20:00 Perú → sigue siendo 2026-06-02."""
    assert _fecha_peru('Wed, 03 Jun 2026 01:00:00 +0000') == '2026-06-02'


def test_pubdate_borde_medianoche_peru_siguiente_dia():
    """03 Jun 05:01 UTC = 03 Jun 00:01 Perú → ya es 2026-06-03."""
    assert _fecha_peru('Wed, 03 Jun 2026 05:01:00 +0000') == '2026-06-03'


def test_pubdate_invalido_devuelve_vacio():
    assert _fecha_peru('no-es-una-fecha') == ''


# ── Filtrado por fecha ──────────────────────────────────────────────────────

def test_excluye_fecha_siguiente(filas):
    """El item de 2026-06-03 en hora Perú no debe aparecer."""
    assert all(f['fecha'] == FECHA for f in filas)


def test_cinco_items_en_fecha(filas):
    """5 items caen en 2026-06-02 hora Perú; 1 item (05:01 UTC) queda fuera."""
    assert len(filas) == 5


# ── Campos obligatorios ─────────────────────────────────────────────────────

def test_todos_tienen_titular(filas):
    for f in filas:
        assert f['titular'], f"Titular vacío: {f['url']}"


def test_todos_tienen_bajada(filas):
    for f in filas:
        assert f['bajada'], f"Bajada vacía: {f['url']}"


def test_diario_correcto(filas):
    assert all(f['diario'] == DIARIO for f in filas)


# ── Sección y opinión ───────────────────────────────────────────────────────

def test_opinion_detectada(filas):
    opinion = [f for f in filas if f['seccion'] == 'opinion']
    assert len(opinion) == 1
    assert opinion[0]['es_opinion'] is True


def test_politica_no_es_opinion(filas):
    pol = [f for f in filas if f['seccion'] == 'politica']
    assert len(pol) >= 2
    assert all(not f['es_opinion'] for f in pol)


# ── Foto ────────────────────────────────────────────────────────────────────

def test_media_content_marca_foto(filas):
    keiko = next(f for f in filas if 'keiko' in f['url'])
    assert keiko['tiene_foto'] is True


def test_sin_media_tiene_foto_false(filas):
    opinion = next(f for f in filas if f['seccion'] == 'opinion')
    assert opinion['tiene_foto'] is False


# ── Posición ────────────────────────────────────────────────────────────────

def test_posicion_incremental(filas):
    assert [f['posicion'] for f in filas] == list(range(1, len(filas) + 1))


# ── Candidato default ───────────────────────────────────────────────────────

def test_candidato_default_ninguno(filas):
    assert all(f['candidato'] == 'ninguno' for f in filas)
