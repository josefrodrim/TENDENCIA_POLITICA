"""
Tests del módulo Wayback — mock de peticiones HTTP para no depender de la red.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tendencia.wayback import _parsear, _timestamp_objetivo, buscar_snapshot

FECHA = '2026-05-20'


# ── Timestamp ────────────────────────────────────────────────────────────────

def test_timestamp_objetivo_formato():
    ts = _timestamp_objetivo('2026-05-20')
    assert ts == '20260520120000'


def test_timestamp_objetivo_otro_mes():
    assert _timestamp_objetivo('2026-06-01') == '20260601120000'


# ── buscar_snapshot (mock CDX) ───────────────────────────────────────────────

def test_buscar_snapshot_devuelve_url(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        ['timestamp', 'statuscode'],
        ['20260520121500', '200'],
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch('tendencia.wayback._SESS') as mock_sess:
        mock_sess.get.return_value = mock_resp
        url = buscar_snapshot('https://larepublica.pe/rss/home.xml', FECHA)

    assert url is not None
    assert 'web.archive.org' in url
    assert '20260520121500' in url


def test_buscar_snapshot_sin_resultados(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.json.return_value = []   # sin snapshots
    mock_resp.raise_for_status = MagicMock()

    with patch('tendencia.wayback._SESS') as mock_sess:
        mock_sess.get.return_value = mock_resp
        url = buscar_snapshot('https://larepublica.pe/rss/home.xml', FECHA)

    assert url is None


def test_buscar_snapshot_error_red(monkeypatch):
    with patch('tendencia.wayback._SESS') as mock_sess:
        mock_sess.get.side_effect = Exception('timeout')
        url = buscar_snapshot('https://larepublica.pe/rss/home.xml', FECHA)
    assert url is None


# ── _parsear: reutiliza los parsers existentes ───────────────────────────────

def test_parsear_glr_usa_fixture():
    fixture = Path('tests/fixtures/larepublica_rss.xml').read_text(encoding='utf-8')
    filas = _parsear(fixture, 'La República', 'glr', '2026-06-02')
    assert len(filas) == 5
    assert all(f['diario'] == 'La República' for f in filas)


def test_parsear_arc_usa_fixture():
    fixture = Path('tests/fixtures/arc_rss.xml').read_text(encoding='utf-8')
    filas = _parsear(fixture, 'El Comercio', 'arc', '2026-06-02')
    assert len(filas) == 5


def test_parsear_larazon_usa_fixture():
    fixture = Path('tests/fixtures/larazon_portada.html').read_text(encoding='utf-8')
    filas = _parsear(fixture, 'La Razón', 'larazon', '2026-06-02')
    assert len(filas) == 4


def test_parsear_tipo_desconocido_devuelve_vacio():
    filas = _parsear('<xml/>', 'Test', 'desconocido', '2026-06-02')
    assert filas == []
