"""Tests del scraper Expreso con fixture HTML."""
from pathlib import Path
import pytest
from tendencia.scrapers.expreso import parse_expreso
from tendencia.schema import Titular

FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'expreso_portada.html'
FECHA   = '2026-06-02'


@pytest.fixture(scope='module')
def filas() -> list[Titular]:
    return parse_expreso(FIXTURE.read_text(encoding='utf-8'), FECHA)


def test_al_menos_tres_articulos(filas):
    assert len(filas) >= 3


def test_todos_tienen_titular(filas):
    for f in filas:
        assert f['titular']


def test_todos_tienen_url(filas):
    for f in filas:
        assert 'expreso.com.pe' in f['url']


def test_fecha_asignada(filas):
    assert all(f['fecha'] == FECHA for f in filas)


def test_no_duplicados(filas):
    urls = [f['url'] for f in filas]
    assert len(urls) == len(set(urls))


def test_seccion_extraida(filas):
    secciones = {f['seccion'] for f in filas if f['seccion']}
    assert 'politica' in secciones


def test_opinion_detectada(filas):
    opinion = [f for f in filas if f['es_opinion']]
    assert len(opinion) >= 1


def test_tiene_foto_en_tarjeta(filas):
    con_foto = [f for f in filas if f['tiene_foto']]
    assert len(con_foto) >= 1


def test_candidato_default_ninguno(filas):
    assert all(f['candidato'] == 'ninguno' for f in filas)


def test_posicion_incremental(filas):
    assert [f['posicion'] for f in filas] == list(range(1, len(filas) + 1))


def test_diario_correcto(filas):
    assert all(f['diario'] == 'Expreso' for f in filas)
