"""Tests del scraper La Razón con fixture HTML."""
from pathlib import Path
import pytest
from tendencia.scrapers.larazon import parse_larazon
from tendencia.schema import Titular

FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'larazon_portada.html'
FECHA   = '2026-06-02'


@pytest.fixture(scope='module')
def filas() -> list[Titular]:
    return parse_larazon(FIXTURE.read_text(encoding='utf-8'), FECHA)


def test_excluye_fecha_anterior(filas):
    assert all(f['fecha'] == FECHA for f in filas)


def test_tres_items_en_fecha(filas):
    # 3 posts del 2026-06-02; 1 del 2026-06-01 excluido
    # Post 5 (opinión) también entra → 4 total
    assert len(filas) == 4


def test_todos_tienen_titular(filas):
    for f in filas:
        assert f['titular']


def test_fecha_extraida_del_time(filas):
    assert all(f['fecha'] == FECHA for f in filas)


def test_tiene_foto_detectada(filas):
    con_foto = [f for f in filas if f['tiene_foto']]
    assert len(con_foto) >= 2


def test_candidato_default_ninguno(filas):
    assert all(f['candidato'] == 'ninguno' for f in filas)


def test_diario_correcto(filas):
    assert all(f['diario'] == 'La Razón' for f in filas)


def test_bajada_cuando_existe(filas):
    con_bajada = [f for f in filas if f['bajada']]
    assert len(con_bajada) >= 2


def test_posicion_incremental(filas):
    assert [f['posicion'] for f in filas] == list(range(1, len(filas) + 1))
