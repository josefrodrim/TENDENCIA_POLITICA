"""
Tests del scraper El Popular — mismo parser GLR que La República,
distinto dominio y nombre de diario.
"""
from pathlib import Path

import pytest

from tendencia.scrapers.glr_base import parse_glr_rss
from tendencia.schema import Titular

# Reutiliza el fixture de La República — mismo formato XML
FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'larepublica_rss.xml'
FECHA   = '2026-06-02'
DIARIO  = 'El Popular'


@pytest.fixture(scope='module')
def filas() -> list[Titular]:
    xml = FIXTURE.read_text(encoding='utf-8')
    # Reemplazar dominio en el XML para simular feed de El Popular
    xml_popular = xml.replace('larepublica.pe', 'elpopular.pe')
    return parse_glr_rss(xml_popular, DIARIO, FECHA)


def test_cinco_items(filas):
    assert len(filas) == 5


def test_diario_es_elpopular(filas):
    assert all(f['diario'] == DIARIO for f in filas)


def test_fecha_correcta(filas):
    assert all(f['fecha'] == FECHA for f in filas)


def test_candidato_ninguno(filas):
    assert all(f['candidato'] == 'ninguno' for f in filas)


def test_opinion_detectada(filas):
    col = [f for f in filas if f['es_opinion']]
    assert len(col) >= 1
